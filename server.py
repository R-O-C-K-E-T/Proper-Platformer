import struct, math, time, pickle, threading
import numpy as np

import physics.physics as physics

import shared, client, wrapper, objects, packets, networking, util

class ObjectSync:
    def __init__(self, server, ID, obj):
        self.server = server
        self.id = ID
        self.obj = obj
        self.priority = 0

        self.dt = 0

        self.new = True
        self.ever_dirty = False

    def update(self):
        obj_packets = []
        if self.new:
            self.prevVel = np.array(self.obj.vel, dtype=float)
            self.prevPos = np.array(self.obj.pos, dtype=float)
            self.new = False

            obj_packets += self.getCreationPackets()
        else:
            self.priority += 0.02 if self.obj.mass < 0 and self.obj.moment < 0 else 0.1
            self.dt += 1

            pos = np.array(self.obj.pos, dtype=float)
            vel = np.array(self.obj.vel, dtype=float)

            if sum(vel**2) < 0.2**2 and sum(np.array(self.prevVel)**2): # if stationary
                posPrediction = self.prevPos + self.prevVel*self.dt
                velPrediction = self.prevVel
            else:
                posPrediction = self.prevPos + self.prevVel*self.dt + np.multiply(self.server.world.gravity, self.dt**2/2)
                velPrediction = self.prevVel + np.multiply(self.server.world.gravity, self.dt)

            self.priority += min(math.sqrt(sum((posPrediction - pos)**2)) / 15, 0.3)
            self.priority += min(math.sqrt(sum((velPrediction - vel)**2)) / 15, 0.3)

            if self.obj.dirtyState:
                self.priority += 1
                self.obj.dirtyState = False

        if self.obj.dirtyProps:
            obj_packets.append(self.getPropertiesPacket())
            self.obj.dirtyProps = False
            self.ever_dirty = True

        return obj_packets

    def getCreationPackets(self):
        obj_packets = []
        if not self.new:
            obj_packets.append(packets.NewObjectPacketClient(self.server.world.tick, self.id, self.obj))
            if self.ever_dirty:
                obj_packets.append(self.getPropertiesPacket())
        return obj_packets


    def reset(self):
        self.prevPos = np.array(self.obj.pos, dtype=float)
        self.prevVel = np.array(self.obj.vel, dtype=float)
        self.dt = 0
        self.priority = 0

    def getPropertiesPacket(self):
        return packets.ObjectPropsPacketClient(self.server.world.tick, self.id, self.obj)

class Server:
    def __init__(self, world, clientScript, port):
        self.port = port
        self.clientScript = clientScript

        self.loadWorld(world)

        self.actions = {}

        self.playerIDs = {}
        self.connections = {}

        self.pending_constraints = []

        self.curID = 0

        self.connection_handler = networking.ThreadedServerConnectionHandler('', port, packets.PROTOCOL)
        self.connection_handler.new_connection = self.new_connection
        self.connection_handler.start(self.handle_packet)

        self.paused = False

    def loadWorld(self, world):
        self.world = world
        self.objectSyncs = [ObjectSync(self, ID, obj) for ID, obj in self.world.objects.items()]

        _add_object = self.world.add_object
        def add_object(obj):
            ID = self.world.curObjID
            #print('Adding Object', ID, obj.colour)
            _add_object(obj)
            if isinstance(obj, objects.Object):
                self.objectSyncs.append(ObjectSync(self, ID, obj))
                #self.sendall(packets.NewObjectPacketClient(self.world.tick, ID, obj))
        self.world.add_object = self.world.script['add_object'] = add_object

        _removeObject = self.world.removeObject
        def removeObject(obj):
            if isinstance(obj, objects.Object):
                for ID, other in self.world.objects.items():
                    if other is obj:
                        break
                else:
                    raise ValueError
                _removeObject(obj)

                for i, sync in enumerate(self.objectSyncs):
                    if sync.id == ID:
                        break
                else:
                    raise ValueError
                self.objectSyncs.pop(i)

                self.sendall(packets.DeleteObjectPacketClient(self.world.tick, ID))
            else:
                _removeObject(obj)
        self.world.removeObject = self.world.script['removeObject'] = removeObject

        _copyObjects = self.world.copyObjects
        def copyObjects(objects, ID):
            newObjects = _copyObjects(objects, ID)

            for obj in newObjects:
                obj_ID = util.findKey(self.world.objects, obj)
                for other, constraint in obj.constraints:
                    other_ID = util.findKey(self.world.objects, other)

                    localA = constraint.localA.tolist() if type(constraint.localA) == np.ndarray else constraint.localA
                    localB = constraint.localB.tolist() if type(constraint.localB) == np.ndarray else constraint.localB

                    if type(constraint) == physics.PivotConstraint:
                        data = {'type': 'pivot', 'localA': localA, 'localB': localB}
                    elif type(constraint) == physics.FixedConstraint:
                        data = {'type': 'fixed', 'localA': localA, 'localB': localB}
                    elif type(constraint) == physics.SliderConstraint:
                        normal = constraint.normal.tolist() if type(normal) == np.ndarray else constraint.normal
                        data = {'type': 'slider', 'localA': localA, 'localB': localB, 'normal': normal}

                    self.pending_constraints.append(packets.NewConstraintPacketClient(self.world.tick, obj_ID, other_ID, data))
            return newObjects
        self.world.copyObjects = copyObjects

    def handle_packet(self, connection, packet):
        packet.handleServer(self, connection)

    def update(self):
        self.connection_handler.update()

        with self.connection_handler.lock:
            t = time.time()
            for connection in list(self.connections):
                if connection.last_received + 3 < t:
                    self.kick(connection, 'Timed out')

            actions = self.actions.pop(self.world.tick, {})
            actions = dict((ID, action) for ID, action in actions.items() if ID in self.playerIDs)

            for ID, action in actions.items():
                self.playerIDs[ID].action = action

        if not self.paused:
            self.world.update()

        updating_objects = []
        for objSync in self.objectSyncs:
            for packet in objSync.update():
                self.sendall(packet)

            if objSync.priority >= 1:
                objSync.reset()
                updating_objects.append((objSync.id, objSync.obj))

        for packet in self.pending_constraints: # TODO handle case where play joins same tick as this
            self.sendall(packet)
        self.pending_constraints.clear()

        for i in range(0, len(updating_objects), 20):
            self.sendall(packets.UpdateObjectsPacketClient(self.world.tick, updating_objects[i:i+20]))

        for ID, action in actions.items():
            try:
                player = self.playerIDs[ID]
            except KeyError:
                continue
            for connection, _ in self.connections.items():
                connection.send(packets.PlayerStatePacketClient(self.world.tick, ID, player))

    '''def get_connection(self, player):
       for connection, other in self.connections.items():
          if other is player:
             break
       else:
          raise ValueError
       return connection'''

    def sendall(self, packet):
        self.connection_handler.sendall(packet)

    def kick(self, connection, reason):
        connection.send(packets.DisconnectPacket(reason))
        print('Kicking', reason)
        self.disconnect(connection)

    def disconnect(self, connection):
        players = self.connections.pop(connection)
        for player in players:
            for ID, other in self.playerIDs.items():
                if other in players:
                    break
            else:
                assert False
            del self.playerIDs[ID]
            self.world.removeObject(player)

            self.sendall(packets.DeletePlayerPacketClient(self.world.tick, ID))

        print(', '.join(player.name for player in players) + ' left.')

        '''print('Writing trace')
        with open('serverTrace.pickle', 'wb') as f:
           pickle.dump(connection.trace, f)'''

    def new_connection(self, connection, payload):
        print('New connection from: {}:{}'.format(*connection.addr))
        if not isinstance(payload, packets.InitConnectionPacketServer):
            self.connection_handler.disconnect(connection.addr)
            return
        #connection.trace = []
        payload.handleServer(self, connection)

    def stop(self, reason):
        self.connection_handler.sendall(packets.DisconnectPacket(reason))
        self.connection_handler.stop()

    def setWorld(self, world, clientScript):
        for ID in self.world.objects:
            self.sendall(packets.DeleteObjectPacketClient(self.world.tick, ID))

        self.playerIDs = {}

        world.tick = self.world.tick

        new_connections = {}
        for connection, old_players in self.connections.items():
            new_players = []
            for ID, old_player in zip(range(connection.base_id, connection.base_id + len(old_players)), old_players):
                new_player = objects.BasePlayer(world, old_player.colour, old_player.name)
                new_players.append(new_player)

                self.playerIDs[ID] = new_player
                world.add_object(new_player)
            new_connections[connection] = new_players
        self.connections = new_connections

        self.loadWorld(world)

        self.sendall(packets.LevelPropsPacketClient(world.gravity, world.spawn))

        for obj_sync in self.objectSyncs:
            for packet in obj_sync.update():
                self.sendall(packet)

        if clientScript is None:
            if self.clientScript is not None:
                self.sendall(packets.ScriptPacketClient(''))
        else:
            self.sendall(packets.ScriptPacketClient(clientScript))
        self.clientScript = clientScript

        for idA, objA in world.objects.items():
            for objB, constraint in objA.constraints:
                idB = util.findKey(self.world.objects, objB)

                localA = constraint.localA.tolist() if type(constraint.localA) == np.ndarray else constraint.localA
                localB = constraint.localB.tolist() if type(constraint.localB) == np.ndarray else constraint.localB

                if type(constraint) == physics.PivotConstraint:
                    data = {'type': 'pivot', 'localA': localA, 'localB': localB}
                elif type(constraint) == physics.FixedConstraint:
                    data = {'type': 'fixed', 'localA': localA, 'localB': localB}
                elif type(constraint) == physics.SliderConstraint:
                    normal = constraint.normal.tolist() if type(normal) == np.ndarray else constraint.normal
                    data = {'type': 'slider', 'localA': localA, 'localB': localB, 'normal': normal}

                self.sendall(packets.NewConstraintPacketClient(world.tick, idA, idB, data))
