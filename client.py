import json, time, queue

import packets, networking
from draw import Drawer

class Client:
    def __init__(self, fancy, screen, world, players, connection):
        self.world = world

        copied_world = world.copy()
        copied_world.script = {} # No scripts should ever be run on drawer

        copied_world.steps = 2
        self.object_map = dict(zip(world, copied_world))

        self.drawer = Drawer(fancy, [self.object_map[player] for player in players], screen, copied_world)
        self.players = players

        self.ids = None
        self.playerIDs = {}
        self.time_map = {}

        self.last_load = 0 # When the drawer world was last updated
        self.sent_tick = 0 # Tick last player action that's been sent

        self.actions = {}

        self.data = [] # Random debugging data stuff

        self.packet_queue = queue.Queue()
        self.disconnect_message = None

        self.connection = connection
        self.connection.start(self.handle_packet)

    def update(self):
        self.connection.update()

        if self.disconnect_message is not None:
            raise RuntimeError('Disconnected from server "{}"'.format(self.disconnect_message))

        received = []
        while True:
            try:
                packet = self.packet_queue.get_nowait()
            except:
                break
            
            if hasattr(packet, 'tick'):
                if packet.tick < self.world.tick:
                    if packet.type != networking.PacketType.NORMAL:
                        packet.handle_client(self)
                else:
                    dt = packet.tick - self.world.tick
                    while len(received) < dt + 1:
                        received.append([])
                    received[dt].append(packet)
            else:
                packet.handle_client(self)

        #print(self.world.spawn, self.drawer.world.spawn, self.drawer.cameras[0].player.world.spawn)
        #print(id(self.world), id(self.drawer.world), id(self.drawer.cameras[0].player.world))

        for i, packet_group in enumerate(received):
            if i != 0:
                self.tick()
            for packet in packet_group:
                packet.handle_client(self)

        if self.connection.last_received + 3 < time.time():
            self.connection.send(packets.DisconnectPacket('Timed Out'))
            raise RuntimeError('Server connection timed out')

        if self.world.tick - self.last_load > 0:
            self.drawer.load(self.world, self.object_map)
            self.last_load = self.world.tick

        actions = []
        for player in self.drawer.players:
            player.action = player.get_action()
            actions.append(player.action)

        target_tick = round(self.drawer.world.tick)
        #print(self.actions)
        for i in range(max(-float('inf'), self.sent_tick+1, *self.actions), target_tick+1):
            self.actions[i] = actions

        if self.ids is not None:
            while self.sent_tick < target_tick:
                self.sent_tick += 1
                self.time_map[self.sent_tick] = time.time()
                self.connection.send(packets.UpdateClientPacketServer(self.sent_tick, self.actions[self.sent_tick]))

        self.drawer.update()
        #self.data.append([time.time(), self.world.tick, self.last_load, self.sent_tick, self.drawer.world.tick, self.drawer.target_tick])

    def handle_packet(self, packet):
        self.packet_queue.put(packet)

    def render(self):
        self.drawer.render()

    def cleanup(self):
        self.drawer.cleanup()

        self.connection.stop()

        with open('data.json', 'w') as f:
            json.dump(self.data, f)

    def tick(self): # Called when a packet is received for a tick that hasn't happened yet
        actions = self.actions.pop(self.world.tick, None)
        if actions is not None:
            for player, action in zip(self.players, actions):
                player.action = action
        self.world.update()
