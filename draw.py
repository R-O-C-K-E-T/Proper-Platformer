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

        self.target_tick = 0

    def load(self, world, obj_map): # obj_map is between world to self.world
        tick = self.world.tick
        self.toremove = set(self.world)

        self.world.tick = world.tick

        for obj_a, obj_b in obj_map.items():
            if obj_b not in self.toremove:
                self.world.add_object(obj_b)
                if 'add_object' in self.world.script:
                    try:
                        self.world.script['add_object'](obj_b)
                    except:
                        print_exc()
            else:
                self.toremove.remove(obj_b)

            obj_b.pos = obj_a.pos
            obj_b.vel = obj_a.vel
            obj_b.rot = obj_a.rot
            obj_b.rot_vel = obj_a.rot_vel

        for obj in self.toremove:
            if 'remove_object' in self.world.script:
                try:
                    self.world.script['remove_object'](obj)
                except:
                    print_exc()
            self.world.remove_object(obj)
            obj.cleanup()

        dt = max(tick - world.tick, 0)
        self.world.update(dt)

    def update(self):
        self.target_tick += 1

        dt = (self.target_tick - self.world.tick) / 15 + 14 / 15
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
