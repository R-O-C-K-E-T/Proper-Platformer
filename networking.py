import socket, struct, operator, time, zlib, random, math, threading
import numpy as np

DEBUG = False

NORMAL = 0
RELIABLE = 1
BIG = 2

MTU = 1200

def apply_crc(protocol_id, data):
    return struct.pack('!I', zlib.crc32(protocol_id + data)) + data
def check_crc(protocol_id, data):
    return data[:4] == struct.pack('!I', zlib.crc32(protocol_id + data[4:]))

class SequenceNumber:
    def __init__(self, size, initial=0):
        assert type(size) == int and size > 0

        self.size = size
        self.maximum = 1 << size

        if type(initial) == bytes:
            if size > 32:
                raise NotImplementedError
            elif size > 16:
                self.value, = struct.unpack('!I', initial) % self.maximum
            elif size > 8:
                self.value = struct.unpack('!H', initial) % self.maximum
            else:
                self.value = struct.unpack('!B', initial) % self.maximum
        elif type(initial) == int:
            self.value = initial % self.maximum
        else:
            raise TypeError('Invalid initial type')

    def increment(self, amount=1):
        return SequenceNumber(self.size, self.value + amount)

    def write(self):
        if self.size > 32:
            raise NotImplementedError
        elif self.size > 16:
            return struct.pack('!I', self.value)
        elif self.size > 8:
            return struct.pack('!H', self.value)
        else:
            return struct.pack('!B', self.value)

    def __repr__(self):
        return 'SequenceNum({}, {})'.format(self.size, self.value)
    def __str__(self):
        return str(self.value)

    def __hash__(self):
        return hash(self.value)

    def _richcmp(op):
        def cmp(self, other):
            if not isinstance(other, SequenceNumber):
                return NotImplemented
            if self.size != other.size:
                return NotImplemented

            a = self.value
            b = other.value

            if a == b:
                val = 0
            else:
                val = 1 if ((a > b) and ((a - b) % self.maximum <= (self.maximum >> 1))) or ((a < b) and ((b - a) % self.maximum > (self.maximum >> 1))) else -1
            return op(val, 0)
        return cmp

    __lt__ = _richcmp(operator.lt)
    __gt__ = _richcmp(operator.gt)
    __le__ = _richcmp(operator.le)
    __ge__ = _richcmp(operator.ge)
    __eq__ = _richcmp(operator.eq)
    __ne__ = _richcmp(operator.ne)


def make_client_connection(host, port, protocol, timeout=3, payload=None, threaded=False):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    sock.connect((host, port))

    protocol_id, sending_types = protocol[:2]

    salt = random.randrange(1<<32)
    init_packet = b'CONN' + struct.pack('!I', salt)
    init_packet += bytes([0])*(MTU - len(init_packet) - 4)

    if DEBUG:
        print('Initialising Connection: salt={}'.format(salt))

    t = time.time()
    sock.send(apply_crc(protocol_id, init_packet))
    data = sock.recv(20)
    rtt = time.time() - t

    if DEBUG:
        print('Got Response {} in {:.2f}ms'.format(data, rtt*1000))

    if not check_crc(protocol_id, data):
        raise RuntimeError('Invalid Response: CRC Incorrect')
    if data[4:8] != b'CHAL':
        raise RuntimeError('Invalid Response: Incorrect Packet Type')

    challenge = data[8:12]
    client_salt, server_salt = struct.unpack('!II', data[12:20])

    if salt != client_salt:
        raise RuntimeError('Invalid Response: Wrong Salt')

    salt = struct.pack('!I', client_salt ^ server_salt)

    if DEBUG:
        print('Using final salt {}'.format(client_salt ^ server_salt))

    response = b'CHAL' + challenge + salt

    if payload is None:
        response += bytes([0])
    else:
        response += bytes([sending_types.index(type(payload)) + 1]) + payload.write()

    response += bytes([0])*(MTU - len(response) - 4)
    sock.send(apply_crc(protocol_id, response))

    time.sleep(rtt*0.5)

    if threaded:
        return ThreadedConnection(protocol, salt, sock)
    else:
        return Connection(protocol, salt, sock)

class BaseServerConnectionHandler:
    def __init__(self, host, port, protocol):
        assert len(protocol) in (2,3)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((host, port))

        self.socket = sock
        self.protocol = protocol

        self.pending = []
        self.connections = {}

    def handle_connection_packet(self, addr, data):
        protocol_id = self.protocol[0]
        receiving_types = self.protocol[-1]

        if len(data) < MTU:
            if DEBUG:
                print('Received connection packet below MTU {}<{}'.format(len(data), MTU))
            return

        if not check_crc(protocol_id, data):
            if DEBUG:
                print('Received connection packet with invalid crc')
            return

        type = data[4:8]

        if type == b'CONN':
            client_salt = data[8:12]
            server_salt = random.randrange(1<<32)

            challenge = struct.pack('!I', random.randrange(1<<32))

            response = b'CHAL' + challenge + client_salt + struct.pack('!I', server_salt)

            if DEBUG:
                print('Received connection request from {} using salt={}'.format(addr, *struct.unpack('!I', client_salt)))

            self.socket.sendto(apply_crc(protocol_id, response), addr)

            salt = struct.pack('!I', server_salt ^ struct.unpack('!I', client_salt)[0])
            self.pending.append((addr, salt, challenge))

            if len(self.pending) > 16:
                self.pending.pop(0)
        elif type == b'CHAL':
            challenge, salt = data[8:12], data[12:16]
            try:
                self.pending.remove((addr, salt, challenge))
            except ValueError:
                if DEBUG:
                    print('Invalid challenge attempt from {}'.format(addr))
                return

            if DEBUG:
                print('Connection with {} established with salt={}'.format(addr, *struct.unpack('!I', salt)))

            packet_id = data[16]
            if packet_id == 0:
                payload = None
            else:
                payload = receiving_types[packet_id-1]()
                payload.read(data[17:])

            connection = BaseConnection(self.protocol, salt, self.socket, addr)

            self.connections[addr] = connection
            self.new_connection(connection, payload)

    def sendall(self, packet):
        if packet.type == NORMAL:
            sending_types = self.protocol[1]
            type_id = sending_types.index(type(packet)) + 1
            data = bytes([type_id]) + packet.write()

            if len(data) + 8 > MTU:
                raise ValueError('Packet too large: {}>{}'.format(len(data)+8, MTU))

            for addr, conn in self.connections.items():
                if conn.trace is not None:
                    conn.trace.append((time.time(), packet))
                self.socket.sendto(apply_crc(self.protocol[0], conn.salt + data), addr)
        else:
            for connection in self.connections.values():
                connection.send(packet)

    def disconnect(self, addr):
        del self.connections[addr]

    def new_connection(self, connection, payload):
        pass

class ServerConnectionHandler(BaseServerConnectionHandler):
    def __init__(self, *args):
        super().__init__(*args)
        self.socket.setblocking(False)

    def poll(self):
        packets = {}
        while True:
            try:
                data, addr = self.socket.recvfrom(MTU)
            except BlockingIOError:
                break

            if addr in self.connections:
                connection = self.connections[addr]
                packet = connection.receive(data)
                if packet is not None:
                    packets.setdefault(connection, []).append(packet)
            else:
                self.handle_connection_packet(addr, data)

        for connection in self.connections.values():
            packets.setdefault(connection, [])
            packets[connection] += connection.update()
        return packets

class ThreadedServerConnectionHandler(BaseServerConnectionHandler):
    def __init__(self, *args):
        super().__init__(*args)

        self.lock = threading.RLock()
        
        self._is_stopped = False
        self.thread = threading.Thread(name='Server Network Thread', target=self._run_thread)
        self.socket.setblocking(True)

    def _run_thread(self):
        while True:
            data, addr = self.socket.recvfrom(MTU)
            if self._is_stopped:
                break

            with self.lock:
                if addr in self.connections:
                    connection = self.connections[addr]
                    packets = connection.receive(data)
                    for packet in packets:
                        self._packet_handler(connection, packet)
                else:
                    self.handle_connection_packet(addr, data)

    def start(self, packet_handler):
        self._packet_handler = packet_handler
        self.thread.start()

    def stop(self):
        self._is_stopped = True
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.sendto(b'', ('localhost', self.socket.getsockname()[1]))
        self.thread.join()

        self.socket.close()

    def sendall(self, packet):
        with self.lock:
            super().sendall(packet)

    def update(self):
        with self.lock:
            for connection in self.connections.values():
                connection.update()

class ChunkSender:
    def __init__(self, chunk_id, packet, conn):
        self.conn = conn

        self.packet_timeout = MTU / (256*1024)
        self.timeout = None

        type_id = conn.sending_types.index(type(packet)) + 1
        self.chunk_id = chunk_id

        payload = packet.write()

        self.done = False

        #             crc salt type chunk_id size slice_id
        header_size = 4 + 4 +  1  + 1 +      1 +  1
        slice_size = MTU - header_size

        self.num_chunks = math.ceil(len(payload) / slice_size)

        if self.num_chunks > 256:
            max_size = slice_size * 256
            raise ValueError('Payload too large: {}>{}'.format(payload, max_size))

        self.send_queue = []
        self.slices = []
        for i in range(256):
            slice_data = payload[i*slice_size:(i+1)*slice_size]
            if len(slice_data) == 0:
                break
            self.slices.append(bytes([type_id, chunk_id, self.num_chunks, i]) + slice_data)
            self.send_queue.append(i)

    def initial_burst(self):
        for i in self.send_queue[:128]:
            self.conn.send_raw(self.slices[i])
        self.send_queue = self.send_queue[128:] + self.send_queue[:128]
        self.timeout = time.time() + self.packet_timeout * 5

    def handle_ack(self, ack):
        bitfield = np.unpackbits(np.array(list(ack), np.uint8)).tolist()
        for i, value in enumerate(bitfield):
            if value:
                try:
                    self.send_queue.remove(i)
                except ValueError:
                    pass
        if len(self.send_queue) == 0:
            self.done = True

    def update(self):
        t = time.time()
        i = 0
        while self.timeout < t and i < len(self.send_queue):
            slice_id = self.send_queue.pop(0)
            self.send_queue.append(slice_id)

            self.conn.send_raw(self.slices[slice_id])

            self.timeout += self.packet_timeout
            i += 1


class ChunkReceiver:
    def __init__(self, packet_type, conn):
        self.conn = conn
        self.packet_type = packet_type

        self.done = False

        self.chunk_id = None
        self.slices = None
        self.remaining = None

    def receive(self, packet_type, data):
        chunk_id, size, slice_id = data[:3]
        if self.chunk_id is None:
            self.chunk_id = chunk_id
            self.slices = [None] * size
            self.remaining = size
        else:
            if chunk_id != self.chunk_id:
                return

        if packet_type != self.packet_type:
            print('Received slice packet with invalid packet type')
            return
        if size != len(self.slices):
            print('Received slice packet with wrong size field')
            return

        packet = None
        if self.slices[slice_id] is None:
            self.remaining -= 1
            self.slices[slice_id] = data[3:]
            if self.remaining == 0:
                self.done = True
                packet = self.packet_type()
                packet.read(b''.join(self.slices))
        self.send_ack()
        return packet

    def send_ack(self):
        data = [False] * 256
        for i, val in enumerate(self.slices):
            if val is not None:
                data[i] = True
        bitfield = bytes(np.packbits(data))
        self.conn.send_raw(bytes([0, self.chunk_id]) + bitfield)


class PacketCache:
    def __init__(self, size):
        self.size = size
        self.entries = [(None,None)] * size

    def __getitem__(self, sequence_num):
        stored_num, packet_data = self.entries[sequence_num.value % self.size]
        if stored_num == sequence_num:
            return packet_data
        else:
            return None

    def __setitem__(self, sequence_num, packet_data):
        assert packet_data is not None
        self.entries[sequence_num.value % self.size] = sequence_num, packet_data

    def __delitem__(self, sequence_num):
        if sequence_num in self:
            self.entries[sequence_num.value % self.size] = None, None

    def __contains__(self, sequence_num):
        assert isinstance(sequence_num, SequenceNumber)
        return self.entries[sequence_num.value % self.size][0] == sequence_num

    def __iter__(self):
        for item in self.entries:
            if item[0] is not None:
                yield item

class BaseConnection:
    def __init__(self, protocol, salt, sock, addr=None):
        self.protocol_id = protocol[0]
        if len(protocol) == 2:
            self.sending_types = self.receiving_types = protocol[1]
        elif len(protocol) == 3:
            self.sending_types,  self.receiving_types = protocol[1:]
        else:
            assert False
        assert len(self.sending_types) <= 255 and len(self.receiving_types) <= 255
        assert isinstance(self.protocol_id, bytes)

        self.salt = salt
        self.socket = sock
        self.addr = addr

        self.trace = None

        self.earliest_sending = SequenceNumber(16)
        self.latest_sending = SequenceNumber(16)


        self.earliest_unreceived = SequenceNumber(16)
        self.latest_received = None

        self.last_received = time.time()

        self.chunk_queue = []
        self.chunk_id = 0
        self.sending_chunk = None

        self.chunk_receiver = None

        self.sending_packets = PacketCache(256)
        self.received_packets = PacketCache(256)

        self.rtt = 0
        self.rtt_dev = 3

        self.packet_loss = 0

    def send(self, packet):
        type_id = self.sending_types.index(type(packet)) + 1

        if self.trace is not None:
            self.trace.append((time.time(), packet))

        if packet.type == BIG:
            self.chunk_queue.append(ChunkSender(self.chunk_id, packet, self))
            self.chunk_id = (self.chunk_id + 1) % 256
        elif packet.type == RELIABLE:
            data = struct.pack('!BH', type_id, self.latest_sending.value) + packet.write()
            self.sending_packets[self.latest_sending] = data, None
            self.latest_sending = self.latest_sending.increment()
        elif packet.type == NORMAL:
            data = struct.pack('!B', type_id) + packet.write()
            self.send_raw(data)
        else:
            raise ValueError('Invalid Packet Type')

    def send_raw(self, data): # Adds 8 bytes
        data = apply_crc(self.protocol_id, self.salt + data)

        if len(data) > MTU:
            raise ValueError('Packet too large: {}>{}'.format(len(data), MTU))

        if self.addr is None:
            self.socket.send(data)
        else:
            self.socket.sendto(data, self.addr)

    @property
    def timeout_interval(self):
        # RFC 2988
        k = 4
        g = 0.01 # Good enough

        return self.rtt + max(g, k*self.rtt_dev)

    def packet_lost(self):
        f = 0.05
        self.packet_loss = self.packet_loss*(1-f) + 1*f

    def packet_received(self):
        f = 0.05
        self.packet_loss = self.packet_loss*(1-f) + 0*f

    def update_rtt(self, rtt):
        # RFC 2988
        a = 1/8
        b = 1/4

        self.rtt_dev = self.rtt_dev*(1-b) + abs(rtt - self.rtt)*b
        self.rtt = self.rtt*(1-a) + rtt*a

    def _handle_ack_packet(self, packet):
        size = len(packet)
        if size == 32 + 1: # Big ACK
            if self.sending_chunk is None:
                if DEBUG:
                    print('Received Big ACK when not sending')
                return
            chunk_id = packet[0]
            if self.sending_chunk.chunk_id != chunk_id:
                if DEBUG:
                    print('Received Big ACK for wrong chunk id {}!={}'.format(self.sending_chunk.chunk_id, chunk_id))
                return
            if DEBUG:
                print('Received Big ACK', chunk_id, packet[1:])
            self.sending_chunk.handle_ack(packet[1:])
        elif size == 2 + 4: # Reliable ACK
            initial, = struct.unpack('!H', packet[:2])
            bitfield = np.unpackbits(np.array(list(packet[2:6]), np.uint8)).tolist()

            self.packet_received()

            if DEBUG:
                print('Received Reliable ACK packet', initial, bitfield)

            t = time.time()
            for i, value in enumerate([1] + bitfield):
                if value:
                    sequence_num = SequenceNumber(16, initial - i)
                    res = self.sending_packets[sequence_num]
                    if res is not None:
                        dt = t - res[1]

                        self.update_rtt(dt)
                    del self.sending_packets[sequence_num]
                    while self.earliest_sending not in self.sending_packets and self.earliest_sending < self.latest_sending:
                        self.earliest_sending = self.earliest_sending.increment(1)
        else:
            if DEBUG:
                print('Received ACK with invalid size')

    def receive(self, data):
        if not check_crc(self.protocol_id, data):
            if DEBUG:
                print('Received packet with invalid crc')
            return None

        recv_salt = data[4:8]
        if recv_salt != self.salt:
            if DEBUG:
                print('Received packet with invalid salt {}!={}'.format(recv_salt, self.salt))
            return None

        self.last_received = time.time()

        packet_type_id = data[8] - 1
        payload = data[9:]
        if packet_type_id == -1: # ACK Packet
            self._handle_ack_packet(payload)
            return []
        else:
            packet_type = self.receiving_types[packet_type_id]

            if DEBUG:
                print('Received packet of type', packet_type)

            if packet_type.type == NORMAL:
                packet = packet_type()
                packet.read(payload)
                return [packet]

            if packet_type.type == RELIABLE:
                sequence_number = SequenceNumber(16, struct.unpack('!H', payload[:2])[0])
                if sequence_number not in self.received_packets:
                    reliable = packet_type()
                    reliable.read(payload[2:])
                    if self.latest_received is None:
                        self.latest_received = sequence_number
                    else:
                        self.latest_received = max(self.latest_received, sequence_number)

                    self.received_packets[sequence_number] = reliable

                self.send_ack()

                packets = []

                if self.earliest_unreceived == sequence_number:
                    seq = self.earliest_unreceived
                    while seq <= self.latest_received:
                        packet = self.received_packets[seq]
                        if packet is None:
                            break
                        packets.append(packet)
                        seq = seq.increment(1)
                    self.earliest_unreceived = seq

                return packets
            
            if packet_type.type == BIG:
                if self.chunk_receiver is None:
                    self.chunk_receiver = ChunkReceiver(packet_type, self)
                elif (self.chunk_receiver.chunk_id + 1) % 256 == payload[0]:
                    if not self.chunk_receiver.done:
                        print('Big packet dropped: New chunk started when old chunk not finished')
                    self.chunk_receiver = ChunkReceiver(packet_type, self)

                packet = self.chunk_receiver.receive(packet_type, payload)

                if packet is None:
                    return []
                else:
                    return [packet]
    
    def send_ack(self):
        latest = self.latest_received
        if DEBUG:
            print('Sending ACK:', latest)
        
        bitfield = np.packbits([latest.increment(-(i+1)) in self.received_packets for i in range(32)])
        self.send_raw(bytes([0]) + struct.pack('!H4B', latest.value, *bitfield))

    def update(self):
        t = time.time()

        for i in range(32):
            sequence_num = self.earliest_sending.increment(i)

            res = self.sending_packets[sequence_num]
            if res is not None:
                packet_data, send_time = res
                if send_time is None or send_time + self.timeout_interval < t:
                    if send_time is not None:
                        self.packet_lost()
                        if DEBUG:
                            print('Resending Packet', sequence_num.value)
                    self.send_raw(packet_data)
                    self.sending_packets[sequence_num] = packet_data, t

        if self.sending_chunk is None:
            if len(self.chunk_queue) != 0:
                self.sending_chunk = self.chunk_queue.pop(0)
                self.sending_chunk.initial_burst()
        else:
            if self.sending_chunk.done:
                if len(self.chunk_queue) != 0:
                    prev = self.sending_chunk
                    self.sending_chunk = self.chunk_queue.pop(0)
                    self.sending_chunk.timeout = prev.timeout
                else:
                    self.sending_chunk = None
            if self.sending_chunk is not None:
                self.sending_chunk.update()

class Connection(BaseConnection):
    def __init__(self, *args):
        super().__init__(*args)

        self.socket.setblocking(False)

    def poll(self):
        packets = []
        while True:
            try:
                data = self.socket.recv(MTU)
            except BlockingIOError:
                break
            
            packets += self.receive(data)
        return packets

class ThreadedConnection(BaseConnection):
    def __init__(self, *args):
        super().__init__(*args)

        self.lock = threading.RLock()

        self._is_stopped = False
        self.thread = threading.Thread(name='Network Thread', target=self._run_thread)
        self.socket.setblocking(True)

    def update(self):
        with self.lock:
            super().update()    

    def _run_thread(self):
        while True:
            data = self.socket.recv(MTU)
            if self._is_stopped:
                break
            
            with self.lock:
                for packet in self.receive(data):
                    self._packet_handler(packet)

    def start(self, packet_handler):
        self._packet_handler = packet_handler
        self.thread.start()

    def stop(self):
        self._is_stopped = True
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.sendto(b'', ('localhost', self.socket.getsockname()[1]))
        self.thread.join()
        self.socket.close()