import math
import numpy as np

from OpenGL import GL as gl
from OpenGL import GLU as glu

import util

def gen_circle(size):
    sides = max(math.ceil(size*2), 3)
    return np.array([[math.cos(a)*size, math.sin(a)*size] for a in (i*math.pi*2/sides for i in range(sides))])

class Camera:
    def __init__(self, offset, size):
        self.pos = np.zeros(2)
        self.size = size
        self.offset = offset

    def load(self):
        gl.glViewport(self.offset[0], self.offset[1], self.size[0], self.size[1])
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        x, y = self.size[0]/2, self.size[1]/2
        glu.gluOrtho2D(-x, x, y, -y)
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()

        gl.glColor3ub(255,255,255)
        gl.glBegin(gl.GL_TRIANGLE_FAN)
        d = 1.0
        gl.glVertex3f(-x, -y, d)
        gl.glVertex3f( x, -y, d)
        gl.glVertex3f( x,  y, d)
        gl.glVertex3f(-x,  y, d)
        gl.glEnd()

        gl.glTranslatef(*(-self.pos), 0)

    def is_visible(self, lower, upper):
        return  upper[0] >= self.pos[0] - self.size[0]*0.5 and \
                upper[1] >= self.pos[1] - self.size[1]*0.5 and \
                lower[0] <= self.pos[0] + self.size[0]*0.5 and \
                lower[1] <= self.pos[1] + self.size[1]*0.5



class PlayerCamera(Camera):
    def __init__(self, fancy, player, *args):
        super().__init__(*args)
        self.fancy = fancy
        self.player = player

        self.vel = np.array(player.vel, dtype=float)
        self.pos = np.array(player.pos, dtype=float)

    def update_position(self):
        self.vel += (self.player.vel - self.vel) / 40
        self.pos += self.vel + (self.player.pos - self.pos) / 20

        if util.length2(self.pos - self.player.pos) > 1000**2:
            self.pos[:] = self.player.pos
            self.vel[:] = self.player.vel

    def update(self):
        self.load()
        self.update_position()
        
        if self.fancy:
            for obj in self.player.world:
                obj.render_fancy(self)
        else:
            for obj in self.player.world:
                obj.render(self)
