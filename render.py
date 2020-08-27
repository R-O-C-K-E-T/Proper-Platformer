import math
import numpy as np

from OpenGL.GL import *
from OpenGL.GLU import *

import util

def genCircle(size):
    sides = max(math.ceil(size*2), 3)
    return np.array([[math.cos(a)*size, math.sin(a)*size] for a in (i*math.pi*2/sides for i in range(sides))])

class Renderer:
    def __init__(self, offset, size):
        self.pos = np.zeros(2)
        self.size = size
        self.offset = offset

    def load(self):
        glViewport(self.offset[0], self.offset[1], self.size[0], self.size[1])
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        x, y = self.size[0]/2, self.size[1]/2
        gluOrtho2D(-x, x, y, -y)
        glMatrixMode(GL_MODELVIEW)

        glLoadIdentity()
        glColor3ub(255,255,255)
        glBegin(GL_TRIANGLE_FAN)
        glVertex2f(-x,-y)
        glVertex2f(x,-y)
        glVertex2f(x,y)
        glVertex2f(-x,y)
        glEnd()

        glTranslatef(*(-self.pos), 0)


def drawCircle(pos, size, colour, outline=(1.5, (0,0,0))):
    # TODO make fast
    drawConvexPolygon(genCircle(size) + pos, colour, outline)

def drawPolygon(points, colour, outline=(1.5, (0,0,0))):
    drawConcavePolygon(points, colour, outline)

def drawConcavePolygon(points, colour, outline=(1.5, (0,0,0))):
    if colour is not None:
        glColor3ub(*colour)
        try:
            glBegin(GL_TRIANGLES)
            for tri in util.triangulate(points): # Crashes for shapes with overlapping points
                for point in tri:
                    glVertex2fv(point)
            glEnd()
        except:
            pass

    if outline is not None:
        glLineWidth(outline[0])
        glColor3ub(*outline[1])

        glBegin(GL_LINE_LOOP)
        for point in points:
            glVertex2fv(point)
        glEnd()


def drawConvexPolygon(points, colour, outline=(1.5, (0,0,0))):
    if colour is not None:
        glColor3ub(*colour)
        glBegin(GL_TRIANGLE_FAN)
        for point in points:
            glVertex2fv(point)
        glEnd()

    if outline is not None:
        glLineWidth(outline[0])
        glColor3ub(*outline[1])
        glBegin(GL_LINE_LOOP)
        for point in points:
            glVertex2f(*point)
        glEnd()

def drawLine(a, b, colour=(0,0,0), width=1.5):
    glLineWidth(width)
    glColor3ub(*colour)

    glBegin(GL_LINES)
    glVertex2f(*a)
    glVertex2f(*b)
    glEnd()


def drawLoop(points, width):
    width /= 2

    glBegin(GL_TRIANGLE_STRIP)

    for a,b,c in zip(np.array(points), np.roll(points,1,0), np.roll(points,2,0)):
        n1 = util.getNormal(a,b)
        n2 = util.getNormal(b,c)

        glVertex2f(*(b - n2*width))
        glVertex2f(*(b + n1*width))
        glVertex2f(*(b - n1*width))
        glVertex2f(*(a + n1*width))
        glVertex2f(*(a - n1*width))

    glEnd()


def draw_shaded(loops, base_colour, rim_colour, distance):
    glClear(GL_DEPTH_BUFFER_BIT)
    glDepthFunc(GL_ALWAYS)
    glColor3fv(base_colour)
    glBegin(GL_TRIANGLES)
    for tri in util.triangulate(loops):
        for point in tri:
            glVertex3f(*point, -1)
    glEnd()

    glDepthFunc(GL_LEQUAL)
    glBegin(GL_TRIANGLES)
    for loop in loops:
        for a, b, c in zip(np.roll(loop, -1, 0), loop, np.roll(loop, 1, 0)):
            normal = np.array([b[1]-a[1],a[0]-b[0]])
            l = util.length(normal)
            if l == 0:
                continue
            normal /= l

            inset_a = a - normal*distance
            inset_b = b - normal*distance

            glColor3fv(rim_colour)
            glVertex3f(*a, 0)
            glVertex3f(*b, 0)
            glColor3fv(base_colour)
            glVertex3f(*inset_a, -1)

            glVertex3f(*inset_a, -1)
            glVertex3f(*inset_b, -1)
            glColor3fv(rim_colour)
            glVertex3f(*b, 0)
    glEnd()

    for loop in loops:
        for a, b, c in zip(np.roll(loop, -1, 0), loop, np.roll(loop, 1, 0)):
            if util.isConvex(a, b, c):
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

            glBegin(GL_TRIANGLE_FAN)
            glColor3fv(rim_colour)
            glVertex3f(*b, 0)

            glColor3fv(base_colour)

            for norm in normals:
                point = b - norm * distance
                glVertex3f(*point, -1)

            glEnd()

    glColor3f(0,0,0)
    for loop in loops:
        glBegin(GL_LINE_LOOP)
        for point in loop:
            glVertex3f(*point, 1)
        glEnd()
