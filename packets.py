import struct, json, time
import numpy as np
from queue import Queue
from traceback import print_exc

import shared, objects, wrapper, util, safe, networking
import physics.physics as physics

class InitConnectionPacketServer:
    def __init__(self, *args):
        if len(args) == 0:
            return

        self.players = []
        for player in args[0]:
            self.players.append((player.name, player.colour))

    def read(self, buf):
        self.players = []
        n = buf[0]
        for nameB, r, g, b in struct.iter_unpack('50p3B', buf[1:1+n*struct.calcsize('50p3B')]):
            self.players.append((nameB.decode('utf-8'), (r,g,b)))

    def write(self):
        buf = bytes([len(self.players)])
        for player in self.players:
            buf += struct.pack('50p3B', bytes(player[0],'utf-8'), *player[1])
        return buf

    def handleServer(self, server, connection):
        assert connection not in server.connections
        if len(self.players) == 0:
            server.disconnect(connection)

        connection.base_id = server.curID
        ids = list(range(server.curID, server.curID+len(self.players)))
        server.curID += len(self.players)

        connection.send(InitConnectionPacketClient(server.world.tick, ids))
        if server.clientScript is not None:
            connection.send(ScriptPacketClient(server.clientScript))
        connection.send(LevelPropsPacketClient(server.world.gravity, server.world.spawn))

        #for ID, obj in server.world.objects.items():
        #   connection.send(NewObjectPacketClient(server.world.tick, ID, obj))
        for objSync in server.objectSyncs:
            for packet in objSync.getCreationPackets():
                connection.send(packet)

        for idA, objA in server.world.objects.items():
            for objB, constraint in objA.constraints:
                idB = util.findKey(server.world.objects, objB)

                localA = constraint.localA.tolist() if type(constraint.localA) == np.ndarray else constraint.localA
                localB = constraint.localB.tolist() if type(constraint.localB) == np.ndarray else constraint.localB

                if type(constraint) == physics.PivotConstraint:
                    data = {'type': 'pivot', 'localA': localA, 'localB': localB}
                elif type(constraint) == physics.FixedConstraint:
                    data = {'type': 'fixed', 'localA': localA, 'localB': localB}
                elif type(constraint) == physics.SliderConstraint:
                    normal = constraint.normal.tolist() if type(normal) == np.ndarray else constraint.normal
                    data = {'type': 'slider', 'localA': localA, 'localB': localB, 'normal': normal}

                connection.send(NewConstraintPacketClient(server.world.tick, idA, idB, data))

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
    type = networking.RELIABLE

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

    def handleClient(self, client):
        client.world.tick = self.tick
        client.drawer.targetTick = self.tick + 5
        client.drawer.world.tick = self.tick
        client.sentTick = self.tick
        client.ids = self.ids

        for ID, player in zip(self.ids, client.players):
            client.playerIDs[ID] = player

class NewPlayerPacketClient:
    type = networking.RELIABLE

    def __init__(self, *args):
        if len(args) == 0:
            return
        self.tick, self.id, player = args
        self.name, self.colour = player.name, player.colour

    def read(self, buf):
        self.tick, self.id, nameB, r,g,b = struct.unpack('<II50p3B', buf)
        self.name = nameB.decode('utf-8')
        self.colour = [r,g,b]

    def write(self):
        return struct.pack('<II50p3B', self.tick, self.id, bytes(self.name,'utf-8'), *self.colour)

    def handleClient(self, client):
        while self.tick > client.world.tick:
            client.tick()

        client.playerIDs[self.id] = player = objects.OtherPlayer(client.world, self.colour, self.name)
        client.world.add_object(player)

        client.objectMap[player] = objects.OtherPlayer(client.drawer.world, self.colour, self.name)

class DeletePlayerPacketClient:
    type = networking.RELIABLE

    def __init__(self, *args):
        if len(args) == 0:
            return
        self.tick, self.id = args

    def read(self, buf):
        self.tick, self.id = struct.unpack('<II', buf)

    def write(self):
        return struct.pack('<II', self.tick, self.id)

    def handleClient(self, client):
        while self.tick > client.world.tick:
            client.tick()
        player = client.playerIDs.pop(self.id)
        client.world.removeObject(player)

        del client.objectMap[player]

class PlayerStatePacketClient:
    type = networking.NORMAL

    def __init__(self, *args):
        if len(args) == 0:
            return
        self.tick, self.id, player = args
        self.pos = player.pos
        self.vel = player.vel
        self.rot = player.rot
        self.rotV = player.rotV
        self.action = player.action

    def read(self, buf):
        res = struct.unpack('<II6d2f', buf)
        self.tick, self.id = res[:2]
        self.pos = res[2:4]
        self.vel = res[4:6]
        self.rot, self.rotV = res[6:8]
        self.action = res[8:10]

    def write(self):
        return struct.pack('<II6d2f', self.tick, self.id, *self.pos, *self.vel, self.rot, self.rotV, *self.action)

    def handleClient(self, client):
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
        player.rotV = self.rotV
        player.action = self.action

class UpdateClientPacketServer:
    type = networking.NORMAL

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

    def handleServer(self, server, connection):
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
    type = networking.NORMAL

    def __init__(self, *args):
        if len(args) == 0:
            return
        self.clientTick, self.serverTick = args

    def read(self, buf):
        self.clientTick, self.serverTick = struct.unpack('<II', buf)

    def write(self):
        return struct.pack('<II', self.clientTick, self.serverTick)

    def handleClient(self, client):
        rtt = time.time() - client.timeMap.pop(self.clientTick)

        client.connection.update_rtt(rtt)

        tick_delay = rtt * 60
        client.drawer.targetTick = (tick_delay + self.serverTick + 1) * 1/4 + client.drawer.targetTick * 3/4


class ScriptPacketClient:
    type = networking.BIG

    def __init__(self, *args):
        if len(args) == 0:
            return
        self.script, = args

    def read(self, buf):
        self.script = buf.decode('utf-8')

    def write(self):
        return bytes(self.script, 'utf-8')

    def handleClient(self, client):
        res = safe.validate(self.script)
        if res is not None:
            print('Warning: This level has a potentially dangerous script', res)
        client.world.loadScript(self.script)
        client.drawer.world.loadScript(self.script)

        if 'add_object' in client.world.script:
            try:
                for obj in client.world:
                    client.world.script['add_object'](obj)
            except:
                print_exc()

class LevelPropsPacketClient:
    type = networking.RELIABLE

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

    def handleClient(self, client):
        for world in (client.world, client.drawer.world):
            world.gravity = self.gravity
            world.spawn = self.spawn

class UpdateObjectsPacketClient:
    type = networking.NORMAL

    def __init__(self, *args):
        if len(args) == 0:
            return
        self.tick, objects = args
        self.objects = [(ID, obj.pos, obj.vel, obj.rot, obj.rotV) for (ID, obj) in objects]

    def write(self):
        return struct.pack('<I', self.tick) + b''.join(struct.pack('<I6f', ID, *pos, *vel, rot, rotV) for ID, pos, vel, rot, rotV in self.objects)

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

    def handleClient(self, client):
        while self.tick > client.world.tick:
            client.tick()
        if self.tick < client.world.tick:
            return

        for ID, pos, vel, rot, rotV in self.objects:
            obj = client.world.objects.get(ID)
            if obj is None:
                return
            obj.pos = pos
            obj.vel = vel
            obj.rot = rot
            obj.rotV = rotV

class NewObjectPacketClient:
    type = networking.RELIABLE

    def __init__(self, *args):
        if len(args) == 0:
            return
        self.tick, self.id, obj = args
        self.data = obj.data
        self.pos = obj.pos
        self.vel = obj.vel
        self.rot = obj.rot
        self.rotV = obj.rotV

    def write(self):
        return struct.pack('<II6d',self.tick,self.id,*self.pos,*self.vel,self.rot,self.rotV) + bytes(json.dumps(self.data), 'utf-8')

    def read(self, buf):
        size = struct.calcsize('<II6d')
        res = struct.unpack('<II6d', buf[:size])

        self.tick, self.id = res[:2]
        self.pos = np.array(res[2:4])
        self.vel = np.array(res[4:6])
        self.rot, self.rotV = res[6:]

        self.data = json.loads(buf[size:].decode('utf-8'))

    def handleClient(self, client):
        while self.tick > client.world.tick:
            client.tick()
        objA = objects.Object(client.world, self.data)
        objB = objects.Object(client.drawer.world, self.data)

        for obj in (objA, objB):
            obj.pos = self.pos
            obj.vel = self.vel
            obj.rot = self.rot
            obj.rotV = self.rotV

        client.world.objects[self.id] = objA
        client.world.append(objA)
        if 'add_object' in client.world.script:
            try:
                client.world.script['add_object'](objA)
            except:
                print_exc()

        client.objectMap[objA] = objB

class DeleteObjectPacketClient:
    type = networking.RELIABLE

    def __init__(self, *args):
        if len(args) == 0:
            return
        self.tick, self.id = args

    def write(self):
        return struct.pack('<II', self.tick, self.id)

    def read(self, buf):
        self.tick, self.id = struct.unpack('<II', buf)

    def handleClient(self, client):
        while self.tick > client.world.tick:
            client.tick()
        obj = client.world.objects.pop(self.id)
        if 'removeObject' in client.world.script:
            try:
                client.world.script['removeObject'](obj)
            except:
                print_exc()

        client.world.remove(obj)
        del client.objectMap[obj]

class ObjectPropsPacketClient:
    type = networking.RELIABLE

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

    def handleClient(self, client):
        while self.tick > client.world.tick:
            client.tick()

        objA = client.world.objects.get(self.id)

        if objA is None:
            print('Properties received for non-existent object')
            return
        objB = client.objectMap[objA]
        for obj in (objA, objB):
            obj.colour = self.data['colour']
            obj.setMass(self.data['mass'])
            obj.setMoment(self.data['moment'])
            obj.animated = self.data['animated']
            obj.lethal = self.data['lethal']
            obj.checkpoint = self.data['checkpoint']
            obj.groups = self.data['groups']
            obj.trigger = self.data['trigger']

class NewConstraintPacketClient:
    type = networking.RELIABLE

    def __init__(self, *args):
        if len(args) == 0:
            return
        self.tick, self.idA, self.idB, self.data = args

    def write(self):
        return struct.pack('<III', self.tick, self.idA, self.idB) + bytes(json.dumps(self.data), 'utf-8')

    def read(self, buf):
        size = struct.calcsize('<III')
        self.tick, self.idA, self.idB = struct.unpack('<III', buf[:size])
        self.data = json.loads(buf[size:].decode('utf-8'))

    def handleClient(self, client):
        while self.tick > client.world.tick:
            client.tick()

        objA = client.world.objects.get(self.idA)
        objB = client.world.objects.get(self.idB)

        if objA is None or objB is None:
            print('Tried to add constraint between non-existent objects')
            return

        #print("adding constraint", self.data, objA, objB)
        if self.data['type'] == 'pivot':
            constraint = physics.PivotConstraint(self.data['localA'], self.data['localB'])
        elif self.data['type'] == 'fixed':
            constraint = physics.FixedConstraint(self.data['localA'], self.data['localB'])
        elif self.data['type'] == 'slider':
            constraint = physics.SliderConstraint(self.data['localA'], self.data['localB'], self.data['normal'])
        objA.constraints.append((objB, constraint))

        objC = client.objectMap[objA]
        objD = client.objectMap[objB]
        objC.constraints.append((objD, constraint))

class DisconnectPacket:
    type = networking.NORMAL

    def __init__(self, *args):
        if len(args) == 0:
            return
        self.reason, = args

    def write(self):
        return self.reason.encode('utf-8')

    def read(self, buf):
        self.reason = buf.decode('utf-8')

    def handleClient(self, client):
        client.disconnect_message = self.reason

    def handleServer(self, server, connection):
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
