import struct, json, time
import numpy as np
from traceback import print_exc

import objects, util, safe, networking
import physics.physics as physics

class InitConnectionPacketServer:
    type=networking.PacketType.INITIAL

    def __init__(self, *args):
        if len(args) == 0:
            return

        self.players = []
        for player in args[0]:
            self.players.append((player.name, player.colour))

    def read(self, buf):
        self.players = []
        n = buf[0]
        for name_bytes, r, g, b in struct.iter_unpack('50p3B', buf[1:1+n*struct.calcsize('50p3B')]):
            self.players.append((name_bytes.decode('utf-8'), (r,g,b)))

    def write(self):
        buf = bytes([len(self.players)])
        for player in self.players:
            buf += struct.pack('50p3B', bytes(player[0],'utf-8'), *player[1])
        return buf

    def handle_server(self, server, connection):
        assert connection not in server.connections
        if len(self.players) == 0:
            server.disconnect(connection)

        connection.base_id = server.curID
        ids = list(range(server.curID, server.curID+len(self.players)))
        server.curID += len(self.players)

        connection.send(InitConnectionPacketClient(server.world.tick, ids))
        if server.client_script is not None:
            connection.send(ScriptPacketClient(server.client_script))
        connection.send(LevelPropsPacketClient(server.world.gravity, server.world.spawn))

        #for ID, obj in server.world.objects.items():
        #   connection.send(NewObjectPacketClient(server.world.tick, ID, obj))
        for obj_sync in server.object_syncs:
            for packet in obj_sync.get_creation_packets():
                connection.send(packet)

        for id_a, obj_a in server.world.objects.items():
            for obj_b, constraint in obj_a.constraints:
                id_b = util.find_key(server.world.objects, obj_b)

                local_a = constraint.local_a.tolist() if type(constraint.local_a) == np.ndarray else constraint.local_a
                local_b = constraint.local_b.tolist() if type(constraint.local_b) == np.ndarray else constraint.local_b

                if type(constraint) == physics.PivotConstraint:
                    data = {'type': 'pivot', 'local_a': local_a, 'local_b': local_b}
                elif type(constraint) == physics.FixedConstraint:
                    data = {'type': 'fixed', 'local_a': local_a, 'local_b': local_b}
                elif type(constraint) == physics.SliderConstraint:
                    normal = constraint.normal.tolist() if type(normal) == np.ndarray else constraint.normal
                    data = {'type': 'slider', 'local_a': local_a, 'local_b': local_b, 'normal': normal}

                connection.send(NewConstraintPacketClient(server.world.tick, id_a, id_b, data))

        for ID, player in server.playerIDs.items():
            connection.send(NewPlayerPacketClient(server.world.tick, ID, player))

        players = []
        for ID, (name, colour) in zip(ids, self.players):
            player = objects.BasePlayer(server.world, colour, name)

            #server.sendall(NewPlayerPacketClient(server.world.tick, ID, player))
            for other_conn in server.connections:
                other_conn.send(NewPlayerPacketClient(server.world.tick, ID, player))

            players.append(player)

            server.playerIDs[ID] = player
            server.world.add_object(player)

        server.connections[connection] = players
        print(', '.join(name for name, _ in self.players) + ' joined.')

class InitConnectionPacketClient:
    type = networking.PacketType.RELIABLE

    def __init__(self, *args):
        if len(args) == 0:
            return
        self.tick, self.ids = args

    def read(self, buf):
        self.tick, *self.ids = [v for v, in struct.iter_unpack('<I', buf)]

    def write(self):
        buf = struct.pack('<I', self.tick)
        for id in self.ids:
            buf += struct.pack('<I', id)
        return buf

    def handle_client(self, client):
        client.world.tick = self.tick
        client.drawer.target_tick = self.tick + 5
        client.drawer.world.tick = self.tick
        client.sent_tick = self.tick
        client.ids = self.ids

        for ID, player in zip(self.ids, client.players):
            client.playerIDs[ID] = player

class NewPlayerPacketClient:
    type = networking.PacketType.RELIABLE

    def __init__(self, *args):
        if len(args) == 0:
            return
        self.tick, self.id, player = args
        self.name, self.colour = player.name, player.colour

    def read(self, buf):
        self.tick, self.id, name_bytes, r, g, b = struct.unpack('<II50p3B', buf)
        self.name = name_bytes.decode('utf-8')
        self.colour = [r,g,b]

    def write(self):
        return struct.pack('<II50p3B', self.tick, self.id, bytes(self.name,'utf-8'), *self.colour)

    def handle_client(self, client):
        while self.tick > client.world.tick:
            client.tick()

        client.playerIDs[self.id] = player = objects.OtherPlayer(client.world, self.colour, self.name)
        client.world.add_object(player)

        client.object_map[player] = objects.OtherPlayer(client.drawer.world, self.colour, self.name)

class DeletePlayerPacketClient:
    type = networking.PacketType.RELIABLE

    def __init__(self, *args):
        if len(args) == 0:
            return
        self.tick, self.id = args

    def read(self, buf):
        self.tick, self.id = struct.unpack('<II', buf)

    def write(self):
        return struct.pack('<II', self.tick, self.id)

    def handle_client(self, client):
        while self.tick > client.world.tick:
            client.tick()
        player = client.playerIDs.pop(self.id)
        client.world.remove_object(player)

        del client.object_map[player]

class PlayerStatePacketClient:
    type = networking.PacketType.NORMAL

    def __init__(self, *args):
        if len(args) == 0:
            return
        self.tick, self.id, player = args
        self.pos = player.pos
        self.vel = player.vel
        self.rot = player.rot
        self.rot_vel = player.rot_vel
        self.action = player.action

    def read(self, buf):
        res = struct.unpack('<II6d2f', buf)
        self.tick, self.id = res[:2]
        self.pos = res[2:4]
        self.vel = res[4:6]
        self.rot, self.rot_vel = res[6:8]
        self.action = res[8:10]

    def write(self):
        return struct.pack('<II6d2f', self.tick, self.id, *self.pos, *self.vel, self.rot, self.rot_vel, *self.action)

    def handle_client(self, client):
        while self.tick > client.world.tick:
            client.tick()
        if self.tick < client.world.tick:
            return
        player = client.playerIDs.get(self.id)
        if player is None:
            return
        player.pos = self.pos
        player.vel = self.vel
        player.rot = self.rot
        player.rot_vel = self.rot_vel
        player.action = self.action

class UpdateClientPacketServer:
    type = networking.PacketType.NORMAL

    def __init__(self, *args):
        if len(args) == 0:
            return
        #self.tick, self.id, self.action = args
        self.tick, self.actions = args
        self.valid = True

    def read(self, buf):
        self.tick, = struct.unpack('<I', buf[:4])
        self.actions = list(struct.iter_unpack('2f', buf[4:]))
        self.valid = all(abs(x) <= 1 and abs(y) <= 1 for x, y in self.actions)

    def write(self):
        return struct.pack('<I', self.tick) + b''.join(struct.pack('ff', *action) for action in self.actions)

    def handle_server(self, server, connection):
        try:
            players = server.connections[connection]
        except KeyError:
            print('Received Client update from disconnected client')
            return
        if not self.valid:
            print('Warning: {} tried to perform an invalid action'.format(connection.addr))
            return

        if len(self.actions) != len(players):
            print('Client sent action update packet with incorrect number of actions: {}!={}'.format(len(self.actions, len(players))))
            return

        for ID, action in zip(range(connection.base_id, connection.base_id+len(players)), self.actions):
            actions = server.actions.get(self.tick, None)
            if actions is None:
                server.actions[self.tick] = actions = {}
            actions[ID] = action
        #print(self.tick, server.world.tick)
        connection.send(UpdateClientResponsePacketClient(self.tick, server.world.tick))

class UpdateClientResponsePacketClient:
    type = networking.PacketType.NORMAL

    def __init__(self, *args):
        if len(args) == 0:
            return
        self.client_tick, self.server_tick = args

    def read(self, buf):
        self.client_tick, self.server_tick = struct.unpack('<II', buf)

    def write(self):
        return struct.pack('<II', self.client_tick, self.server_tick)

    def handle_client(self, client):
        rtt = time.time() - client.time_map.pop(self.client_tick)

        client.connection.update_rtt(rtt)

        tick_delay = rtt * 60
        client.drawer.target_tick = (tick_delay + self.server_tick + 1) * 1/4 + client.drawer.target_tick * 3/4


class ScriptPacketClient:
    type = networking.PacketType.BIG

    def __init__(self, *args):
        if len(args) == 0:
            return
        self.script, = args

    def read(self, buf):
        self.script = buf.decode('utf-8')

    def write(self):
        return bytes(self.script, 'utf-8')

    def handle_client(self, client):
        res = safe.validate(self.script)
        if res is not None:
            print('Warning: This level has a potentially dangerous script', res)
        client.world.load_script(self.script)
        client.drawer.world.load_script(self.script)

        if 'add_object' in client.world.script:
            try:
                for obj in client.world:
                    client.world.script['add_object'](obj)
            except:
                print_exc()

class LevelPropsPacketClient:
    type = networking.PacketType.RELIABLE

    def __init__(self, *args):
        if len(args) == 0:
            return
        self.gravity, self.spawn = args

    def read(self, buf):
        res = struct.unpack('dddd', buf)
        self.gravity = res[:2]
        self.spawn = res[2:]

    def write(self):
        return struct.pack('dddd', *self.gravity, *self.spawn)

    def handle_client(self, client):
        for world in (client.world, client.drawer.world):
            world.gravity = self.gravity
            world.spawn = self.spawn

class UpdateObjectsPacketClient:
    type = networking.PacketType.NORMAL

    def __init__(self, *args):
        if len(args) == 0:
            return
        self.tick, objects = args
        self.objects = [(ID, obj.pos, obj.vel, obj.rot, obj.rot_vel) for (ID, obj) in objects]

    def write(self):
        return struct.pack('<I', self.tick) + b''.join(struct.pack('<I6f', ID, *pos, *vel, rot, rot_vel) for ID, pos, vel, rot, rot_vel in self.objects)

    def read(self, buf):
        self.tick, = struct.unpack('<I', buf[:4])

        self.objects = []
        for data in struct.iter_unpack('<I6f', buf[4:]):
            self.objects.append([
               data[0],
               np.array(data[1:3]),
               np.array(data[3:5]),
               data[5],
               data[6]
            ])

    def handle_client(self, client):
        while self.tick > client.world.tick:
            client.tick()
        if self.tick < client.world.tick:
            return

        for ID, pos, vel, rot, rot_vel in self.objects:
            obj = client.world.objects.get(ID)
            if obj is None:
                return
            obj.pos = pos
            obj.vel = vel
            obj.rot = rot
            obj.rot_vel = rot_vel

class NewObjectPacketClient:
    type = networking.PacketType.RELIABLE

    def __init__(self, *args):
        if len(args) == 0:
            return
        self.tick, self.id, obj = args
        self.data = obj.data
        self.pos = obj.pos
        self.vel = obj.vel
        self.rot = obj.rot
        self.rot_vel = obj.rot_vel

    def write(self):
        return struct.pack('<II6d',self.tick,self.id,*self.pos,*self.vel,self.rot,self.rot_vel) + bytes(json.dumps(self.data), 'utf-8')

    def read(self, buf):
        size = struct.calcsize('<II6d')
        res = struct.unpack('<II6d', buf[:size])

        self.tick, self.id = res[:2]
        self.pos = np.array(res[2:4])
        self.vel = np.array(res[4:6])
        self.rot, self.rot_vel = res[6:]

        self.data = json.loads(buf[size:].decode('utf-8'))

    def handle_client(self, client):
        while self.tick > client.world.tick:
            client.tick()
        obj_a = objects.Object(client.world, self.data)
        obj_b = objects.Object(client.drawer.world, self.data)

        for obj in (obj_a, obj_b):
            obj.pos = self.pos
            obj.vel = self.vel
            obj.rot = self.rot
            obj.rot_vel = self.rot_vel

        client.world.objects[self.id] = obj_a
        client.world.append(obj_a)
        if 'add_object' in client.world.script:
            try:
                client.world.script['add_object'](obj_a)
            except:
                print_exc()

        client.object_map[obj_a] = obj_b

class DeleteObjectPacketClient:
    type = networking.PacketType.RELIABLE

    def __init__(self, *args):
        if len(args) == 0:
            return
        self.tick, self.id = args

    def write(self):
        return struct.pack('<II', self.tick, self.id)

    def read(self, buf):
        self.tick, self.id = struct.unpack('<II', buf)

    def handle_client(self, client):
        while self.tick > client.world.tick:
            client.tick()
        obj = client.world.objects.pop(self.id)
        if 'remove_object' in client.world.script:
            try:
                client.world.script['remove_object'](obj)
            except:
                print_exc()

        client.world.remove(obj)
        del client.object_map[obj]

class ObjectPropsPacketClient:
    type = networking.PacketType.RELIABLE

    def __init__(self, *args):
        if len(args) == 0:
            return
        self.tick, self.id, obj = args
        self.data = {
           'colour': obj.colour,
           'mass': obj.mass,
           'moment': obj.moment,
           'animated': obj.animated,
           'lethal': obj.lethal,
           'checkpoint': obj.checkpoint,
           'groups': obj.groups,
           'trigger': obj.trigger,
        }

    def write(self):
        return struct.pack('<II', self.tick, self.id) + bytes(json.dumps(self.data), 'utf-8')

    def read(self, buf):
        size = struct.calcsize('<II')
        self.tick, self.id = struct.unpack('<II', buf[:size])
        self.data = json.loads(buf[size:].decode('utf-8'))

    def handle_client(self, client):
        while self.tick > client.world.tick:
            client.tick()

        obj_a = client.world.objects.get(self.id)

        if obj_a is None:
            print('Properties received for non-existent object')
            return
        obj_b = client.object_map[obj_a]
        for obj in (obj_a, obj_b):
            obj.colour = self.data['colour']
            obj.set_mass(self.data['mass'])
            obj.set_moment(self.data['moment'])
            obj.animated = self.data['animated']
            obj.lethal = self.data['lethal']
            obj.checkpoint = self.data['checkpoint']
            obj.groups = self.data['groups']
            obj.trigger = self.data['trigger']

class NewConstraintPacketClient:
    type = networking.PacketType.RELIABLE

    def __init__(self, *args):
        if len(args) == 0:
            return
        self.tick, self.id_a, self.id_b, self.data = args

    def write(self):
        return struct.pack('<III', self.tick, self.id_a, self.id_b) + bytes(json.dumps(self.data), 'utf-8')

    def read(self, buf):
        size = struct.calcsize('<III')
        self.tick, self.id_a, self.id_b = struct.unpack('<III', buf[:size])
        self.data = json.loads(buf[size:].decode('utf-8'))

    def handle_client(self, client):
        while self.tick > client.world.tick:
            client.tick()

        obj_a = client.world.objects.get(self.id_a)
        obj_b = client.world.objects.get(self.id_b)

        if obj_a is None or obj_b is None:
            print('Tried to add constraint between non-existent objects')
            return

        #print("adding constraint", self.data, obj_a, obj_b)
        if self.data['type'] == 'pivot':
            constraint = physics.PivotConstraint(self.data['local_a'], self.data['local_b'])
        elif self.data['type'] == 'fixed':
            constraint = physics.FixedConstraint(self.data['local_a'], self.data['local_b'])
        elif self.data['type'] == 'slider':
            constraint = physics.SliderConstraint(self.data['local_a'], self.data['local_b'], self.data['normal'])
        else:
            assert False
        obj_a.constraints.append((obj_b, constraint))

        mirrored_a = client.object_map[obj_a]
        mirrored_b = client.object_map[obj_b]
        mirrored_a.constraints.append((mirrored_b, constraint))

class DisconnectPacket:
    type = networking.PacketType.NORMAL

    def __init__(self, *args):
        if len(args) == 0:
            return
        self.reason, = args

    def write(self):
        return self.reason.encode('utf-8')

    def read(self, buf):
        self.reason = buf.decode('utf-8')

    def handle_client(self, client):
        client.disconnect_message = self.reason

    def handle_server(self, server, connection):
        if connection not in server.connections:
            return
        print('Player disconnected: {}'.format(self.reason))
        server.disconnect(connection)

# Server packets are handled by server and vice versa
# Unspecified packets are handled by both

packet_types = [
   InitConnectionPacketClient,
   InitConnectionPacketServer,
   ScriptPacketClient,
   LevelPropsPacketClient,
   UpdateClientPacketServer,
   PlayerStatePacketClient,
   UpdateClientResponsePacketClient,
   NewObjectPacketClient,
   DeleteObjectPacketClient,
   ObjectPropsPacketClient,
   UpdateObjectsPacketClient,
   NewConstraintPacketClient,
   NewPlayerPacketClient,
   DeletePlayerPacketClient,
   DisconnectPacket,
]
PROTOCOL = bytes([171, 85, 215, 1]), packet_types
