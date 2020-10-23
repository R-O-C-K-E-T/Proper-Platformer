import math, time
import numpy as np

import physics.physics as physics

import objects, packets, networking, util

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
            self.prev_vel = np.array(self.obj.vel, dtype=float)
            self.prev_pos = np.array(self.obj.pos, dtype=float)
            self.new = False

            obj_packets += self.get_creation_packets()
        else:
            self.priority += 0.02 if self.obj.mass < 0 and self.obj.moment < 0 else 0.1
            self.dt += 1

            pos = np.array(self.obj.pos, dtype=float)
            vel = np.array(self.obj.vel, dtype=float)

            if sum(vel**2) < 0.2**2 and sum(np.array(self.prev_vel)**2): # if stationary
                pos_prediction = self.prev_pos + self.prev_vel*self.dt
                vel_prediction = self.prev_vel
            else:
                pos_prediction = self.prev_pos + self.prev_vel*self.dt + np.multiply(self.server.world.gravity, self.dt**2/2)
                vel_prediction = self.prev_vel + np.multiply(self.server.world.gravity, self.dt)

            self.priority += min(math.sqrt(sum((pos_prediction - pos)**2)) / 15, 0.3)
            self.priority += min(math.sqrt(sum((vel_prediction - vel)**2)) / 15, 0.3)

            if self.obj.dirty_state:
                self.priority += 1
                self.obj.dirty_state = False

        if self.obj.dirty_props:
            obj_packets.append(self.get_properties_packet())
            self.obj.dirty_props = False
            self.ever_dirty = True

        return obj_packets

    def get_creation_packets(self):
        obj_packets = []
        if not self.new:
            obj_packets.append(packets.NewObjectPacketClient(self.server.world.tick, self.id, self.obj))
            if self.ever_dirty:
                obj_packets.append(self.get_properties_packet())
        return obj_packets


    def reset(self):
        self.prev_pos = np.array(self.obj.pos, dtype=float)
        self.prev_vel = np.array(self.obj.vel, dtype=float)
        self.dt = 0
        self.priority = 0

    def get_properties_packet(self):
        return packets.ObjectPropsPacketClient(self.server.world.tick, self.id, self.obj)

class Server:
    def __init__(self, world, client_script, port):
        self.port = port
        self.client_script = client_script

        self.load_world(world)

        self.actions = {}

        self.playerIDs = {}
        self.connections = {}

        self.pending_constraints = []

        self.curID = 0

        self.connection_handler = networking.ThreadedServerConnectionHandler('', port, packets.PROTOCOL)
        self.connection_handler.new_connection = self.new_connection
        self.connection_handler.start(self.handle_packet)

        self.paused = False

    def load_world(self, world):
        self.world = world
        self.object_syncs = [ObjectSync(self, ID, obj) for ID, obj in self.world.objects.items()]

        _add_object = self.world.add_object
        def add_object(obj):
            ID = self.world.current_object_id
            #print('Adding Object', ID, obj.colour)
            _add_object(obj)
            if isinstance(obj, objects.Object):
                self.object_syncs.append(ObjectSync(self, ID, obj))
                #self.sendall(packets.NewObjectPacketClient(self.world.tick, ID, obj))
        self.world.add_object = self.world.script['add_object'] = add_object

        _remove_object = self.world.remove_object
        def remove_object(obj):
            if isinstance(obj, objects.Object):
                for ID, other in self.world.objects.items():
                    if other is obj:
                        break
                else:
                    raise ValueError
                _remove_object(obj)

                for i, sync in enumerate(self.object_syncs):
                    if sync.id == ID:
                        break
                else:
                    raise ValueError
                self.object_syncs.pop(i)

                self.sendall(packets.DeleteObjectPacketClient(self.world.tick, ID))
            else:
                _remove_object(obj)
        self.world.remove_object = self.world.script['remove_object'] = remove_object

        _copy_objects = self.world.copy_objects
        def copy_objects(objects, ID):
            new_objects = _copy_objects(objects, ID)

            for obj in new_objects:
                obj_ID = util.find_key(self.world.objects, obj)
                for other, constraint in obj.constraints:
                    other_ID = util.find_key(self.world.objects, other)

                    local_a = constraint.local_a.tolist() if type(constraint.local_a) == np.ndarray else constraint.local_a
                    local_b = constraint.local_b.tolist() if type(constraint.local_b) == np.ndarray else constraint.local_b

                    if type(constraint) == physics.PivotConstraint:
                        data = {'type': 'pivot', 'local_a': local_a, 'local_b': local_b}
                    elif type(constraint) == physics.FixedConstraint:
                        data = {'type': 'fixed', 'local_a': local_a, 'local_b': local_b}
                    elif type(constraint) == physics.SliderConstraint:
                        normal = constraint.normal.tolist() if type(normal) == np.ndarray else constraint.normal
                        data = {'type': 'slider', 'local_a': local_a, 'local_b': local_b, 'normal': normal}

                    self.pending_constraints.append(packets.NewConstraintPacketClient(self.world.tick, obj_ID, other_ID, data))
            return new_objects
        self.world.copy_objects = copy_objects

    def handle_packet(self, connection, packet):
        packet.handle_server(self, connection)

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
        for obj_sync in self.object_syncs:
            for packet in obj_sync.update():
                self.sendall(packet)

            if obj_sync.priority >= 1:
                obj_sync.reset()
                updating_objects.append((obj_sync.id, obj_sync.obj))

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
            self.world.remove_object(player)

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
        payload.handle_server(self, connection)

    def stop(self, reason):
        self.connection_handler.sendall(packets.DisconnectPacket(reason))
        self.connection_handler.stop()

    def set_world(self, world, client_script):
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

        self.load_world(world)

        self.sendall(packets.LevelPropsPacketClient(world.gravity, world.spawn))

        for obj_sync in self.object_syncs:
            for packet in obj_sync.update():
                self.sendall(packet)

        if client_script is None:
            if self.client_script is not None:
                self.sendall(packets.ScriptPacketClient(''))
        else:
            self.sendall(packets.ScriptPacketClient(client_script))
        self.client_script = client_script

        for id_a, obj_a in world.objects.items():
            for obj_b, constraint in obj_a.constraints:
                id_b = util.find_key(self.world.objects, obj_b)

                local_a = constraint.local_a.tolist() if type(constraint.local_a) == np.ndarray else constraint.local_a
                local_b = constraint.local_b.tolist() if type(constraint.local_b) == np.ndarray else constraint.local_b

                if type(constraint) == physics.PivotConstraint:
                    data = {'type': 'pivot', 'local_a': local_a, 'local_b': local_b}
                elif type(constraint) == physics.FixedConstraint:
                    data = {'type': 'fixed', 'local_a': local_a, 'local_b': local_b}
                elif type(constraint) == physics.SliderConstraint:
                    normal = constraint.normal.tolist() if type(normal) == np.ndarray else constraint.normal
                    data = {'type': 'slider', 'local_a': local_a, 'local_b': local_b, 'normal': normal}

                self.sendall(packets.NewConstraintPacketClient(world.tick, id_a, id_b, data))
