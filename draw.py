import math, pygame, copy
import numpy as np
from traceback import print_exc

import shared, wrapper, camera, util, objects

from OpenGL.GL import *
from OpenGL.GLU import *

class Drawer:
    def __init__(self, fancy, players, screen, world):
        self.fancy = fancy
        self.screen = screen

        self.world = world
        self.players = players.copy()
        self.cameras = []

        self.targetTick = 0

    def load(self, world, objMap): # objMap is between world to self.world
        tick = self.world.tick
        self.toremove = set(self.world)

        self.world.tick = world.tick

        for objA, objB in objMap.items():
            if objB not in self.toremove:
                self.world.add_object(objB)
                if 'add_object' in self.world.script:
                    try:
                        self.world.script['add_object'](objB)
                    except:
                        print_exc()
            else:
                self.toremove.remove(objB)

            objB.pos = objA.pos
            objB.vel = objA.vel
            objB.rot = objA.rot
            objB.rotV = objA.rotV

        for obj in self.toremove:
            if 'removeObject' in self.world.script:
                try:
                    self.world.script['removeObject'](obj)
                except:
                    print_exc()
            self.world.removeObject(obj)
            obj.cleanup()

        dt = max(tick - world.tick, 0)
        self.world.update(dt)

    def update(self):
        self.targetTick += 1

        dt = (self.targetTick - self.world.tick) / 15 + 14 / 15
        dt = max(dt, 0)

        self.world.update(dt)

    def resize(self, size=None):
        n = len(self.players)
        columns = math.ceil(math.sqrt(n))
        rows = math.ceil(n / columns)

        self.cameras.clear()
        if size is None:
            if pygame.version.vernum.major >= 2:
                size = pygame.display.get_window_size()
            else:
                size = self.screen.get_size() # Seems to return (1,1) for pygame 2.0+

        cellSize = (size[0]-columns+1) // columns, (size[1]-rows+1) // rows
        for i, player in enumerate(self.players):
            column = i % columns
            row = i // columns

            pos = column * (cellSize[0]+1), row * (cellSize[1]+1)
            self.cameras.append(camera.PlayerCamera(self.fancy, player, pos, cellSize))

    def render(self):
        for camera in self.cameras:
            camera.update()

    def cleanup(self):
        for obj in self.world:
            obj.cleanup()
