import struct, socket, json, math,  time
import numpy as np

import physics.physics as physics
import shared, wrapper, packets, networking
from draw import Drawer

class Client:
    def __init__(self, fancy, screen, world, players, connection):
        self.world = world

        copiedWorld = world.copy()
        copiedWorld.script = {} # No scripts should ever be run on drawer

        copiedWorld.steps = 2
        self.objectMap = dict(zip(world, copiedWorld))

        self.drawer = Drawer(fancy, [self.objectMap[player] for player in players], screen, copiedWorld)
        self.players = players

        self.ids = None
        self.playerIDs = {}
        self.timeMap = {}

        self.lastLoad = 0 # When the drawer world was last updated
        self.sentTick = 0 # Tick last player action that's been sent

        self.actions = {}

        self.data = [] # Random debugging data stuff

        self.connection = connection

    def update(self):
        received = []
        for packet in self.connection.poll():
            if hasattr(packet, 'tick'):
                if packet.tick < self.world.tick:
                    if packet.type != networking.NORMAL:
                        packet.handleClient(self)
                else:
                    dt = packet.tick - self.world.tick
                    while len(received) < dt + 1:
                        received.append([])
                    received[dt].append(packet)
            else:
                packet.handleClient(self)

        #print(self.world.spawn, self.drawer.world.spawn, self.drawer.cameras[0].player.world.spawn)
        #print(id(self.world), id(self.drawer.world), id(self.drawer.cameras[0].player.world))

        for i, packet_group in enumerate(received):
            if i != 0:
                self.tick()
            for packet in packet_group:
                packet.handleClient(self)

        if self.connection.last_received + 3 < time.time():
            self.connection.send(packets.DisconnectPacket('Timed Out'))
            raise RuntimeError('Server connection timed out')

        if self.world.tick - self.lastLoad > 0:
            self.drawer.load(self.world, self.objectMap)
            self.lastLoad = self.world.tick

        actions = []
        for player in self.drawer.players:
            player.action = player.getAction()
            actions.append(player.action)

        targetTick = round(self.drawer.world.tick)
        #print(self.actions)
        for i in range(max(-float('inf'), self.sentTick+1, *self.actions), targetTick+1):
            self.actions[i] = actions

        if self.ids is not None:
            while self.sentTick < targetTick:
                self.sentTick += 1
                self.timeMap[self.sentTick] = time.time()
                self.connection.send(packets.UpdateClientPacketServer(self.sentTick, self.actions[self.sentTick]))

        self.drawer.update()
        #self.data.append([time.time(), self.world.tick, self.lastLoad, self.sentTick, self.drawer.world.tick, self.drawer.targetTick])

    def render(self):
        self.drawer.render()

    def cleanup(self):
        self.drawer.cleanup()

        self.connection.socket.close()

        with open('data.json', 'w') as f:
            json.dump(self.data, f)

    def tick(self): # Called when a packet is received for a tick that hasn't happened yet
        actions = self.actions.pop(self.world.tick, None)
        if actions is not None:
            for player, action in zip(self.players, actions):
                player.action = action
        self.world.update()
