import math
import numpy as np

from OpenGL import GL as gl
from OpenGL import GLU as glu

import util

def gen_circle(size):
    sides = max(math.ceil(size*2), 3)
    return np.array([[math.cos(a)*size, math.sin(a)*size] for a in (i*math.pi*2/sides for i in range(sides))])

class Renderer:
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
        gl.glVertex2f(-x,-y)
        gl.glVertex2f(x,-y)
        gl.glVertex2f(x,y)
        gl.glVertex2f(-x,y)
        gl.glEnd()

        gl.glTranslatef(*(-self.pos), 0)


def draw_circle(pos, size, colour, outline=(1.5, (0,0,0))):
    # TODO make fast
    draw_convex_polygon(gen_circle(size) + pos, colour, outline)

def draw_polygon(points, colour, outline=(1.5, (0,0,0))):
    draw_concave_polygon(points, colour, outline)

def draw_concave_polygon(points, colour, outline=(1.5, (0,0,0))):
    if colour is not None:
        gl.glColor3ubv(colour)
        try:
            gl.glBegin(gl.GL_TRIANGLES)
            for tri in util.triangulate(points): # Crashes for shapes with overlapping points
                for point in tri:
                    gl.glVertex2fv(point)
            gl.glEnd()
        except:
            pass

    if outline is not None:
        gl.glLineWidth(outline[0])
        gl.glColor3ubv(outline[1])

        gl.glBegin(gl.GL_LINE_LOOP)
        for point in points:
            gl.glVertex2fv(point)
        gl.glEnd()


def draw_convex_polygon(points, colour, outline=(1.5, (0,0,0))):
    if colour is not None:
        gl.glColor3ubv(colour)
        gl.glBegin(gl.GL_TRIANGLE_FAN)
        for point in points:
            gl.glVertex2fv(point)
        gl.glEnd()

    if outline is not None:
        gl.glLineWidth(outline[0])
        gl.glColor3ubv(outline[1])
        gl.glBegin(gl.GL_LINE_LOOP)
        for point in points:
            gl.glVertex2f(*point)
        gl.glEnd()

def draw_line(a, b, colour=(0,0,0), width=1.5):
    gl.glLineWidth(width)
    gl.glColor3ub(*colour)

    gl.glBegin(gl.GL_LINES)
    gl.glVertex2f(*a)
    gl.glVertex2f(*b)
    gl.glEnd()


def draw_loop(points, width):
    width /= 2

    gl.glBegin(gl.GL_TRIANGLE_STRIP)

    for a,b,c in zip(np.array(points), np.roll(points,1,0), np.roll(points,2,0)):
        n1 = util.get_normal(a,b)
        n2 = util.get_normal(b,c)

        gl.glVertex2fv(b - n2*width)
        gl.glVertex2fv(b + n1*width)
        gl.glVertex2fv(b - n1*width)
        gl.glVertex2fv(a + n1*width)
        gl.glVertex2fv(a - n1*width)

    gl.glEnd()


def draw_shaded(loops, base_colour, rim_colour, distance):
    gl.glClear(gl.GL_DEPTH_BUFFER_BIT)
    gl.glDepthFunc(gl.GL_ALWAYS)
    gl.glColor3fv(base_colour)
    gl.glBegin(gl.GL_TRIANGLES)
    for tri in util.triangulate(loops):
        for point in tri:
            gl.glVertex3f(*point, -1)
    gl.glEnd()

    gl.glDepthFunc(gl.GL_LEQUAL)
    gl.glBegin(gl.GL_TRIANGLES)
    for loop in loops:
        for a, b, c in zip(np.roll(loop, -1, 0), loop, np.roll(loop, 1, 0)):
            normal = np.array([b[1]-a[1],a[0]-b[0]])
            l = util.length(normal)
            if l == 0:
                continue
            normal /= l

            inset_a = a - normal*distance
            inset_b = b - normal*distance

            gl.glColor3fv(rim_colour)
            gl.glVertex3f(*a, 0)
            gl.glVertex3f(*b, 0)
            gl.glColor3fv(base_colour)
            gl.glVertex3f(*inset_a, -1)

            gl.glVertex3f(*inset_a, -1)
            gl.glVertex3f(*inset_b, -1)
            gl.glColor3fv(rim_colour)
            gl.glVertex3f(*b, 0)
    gl.glEnd()

    for loop in loops:
        for a, b, c in zip(np.roll(loop, -1, 0), loop, np.roll(loop, 1, 0)):
            if util.is_convex(a, b, c):
                continue
            normals = [
                np.array([b[1]-a[1],a[0]-b[0]]),
                np.array([c[1]-b[1],b[0]-c[0]]),
            ]
            normals = [norm / util.length(norm) for norm in normals]

            for _ in range(2):
                new_normals = []
                for normA, normB in zip(normals, normals[1:]):
                    new = normA + normB
                    new /= util.length(new)
                    new_normals.append(new)

                for i, norm in enumerate(new_normals):
                    normals.insert(1+2*i, norm)

            gl.glBegin(gl.GL_TRIANGLE_FAN)
            gl.glColor3fv(rim_colour)
            gl.glVertex3f(*b, 0)

            gl.glColor3fv(base_colour)

            for norm in normals:
                point = b - norm * distance
                gl.glVertex3f(*point, -1)

            gl.glEnd()

    gl.glColor3f(0,0,0)
    for loop in loops:
        gl.glBegin(gl.GL_LINE_LOOP)
        for point in loop:
            gl.glVertex3f(*point, 1)
        gl.glEnd()
