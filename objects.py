import numpy as np
import math, random, pygame

from OpenGL.GL import *
from OpenGL.GLU import *

import physics.physics as physics

import util, camera, font, decomposition, render, actions

OFFSET = 5
SCALE = 0.3

def calculateProps(polygon, density):
    area = sum(util.cross2d(a, b) for a, b in zip(polygon, np.roll(polygon, 1, 0))) / 2

    pos = np.array([sum((a[i]+b[i])*util.cross2d(a, b) for a, b in zip(polygon, np.roll(polygon, 1, 0))) for i in range(2)]) / (6*area)

    if density is None:
        mass = -1
        moment = -1
    else:
        mass = area * density

        polygon = np.array(polygon) - pos
        moment = sum(util.cross2d(a, b)*(sum(a**2)+np.dot(a, b)+sum(b**2)) for a, b in zip(polygon, np.roll(polygon, 1, 0))) * mass / (6*area)

    return mass, moment, pos

def genPolygon(points, density):
    points = np.array(points, dtype=float)
    if not util.checkWinding(points):
        points = points[::-1]

    mass, moment, com = calculateProps(points, density)
    points -= com

    colliders = [physics.PolyCollider(decomposition.convertFrom(polygon)) for polygon in decomposition.decompose(decomposition.convertInto(points[::-1]))]

    return com, points, colliders, mass, moment

def circleMassMoment(radius, density):
    mass = math.pi * radius**2 * density
    moment = mass * radius**2 / 2
    return mass, moment


def genCircle(radius, density):
    massMoment = (-1, -1) if density is None else circleMassMoment(radius, density)
    return ([physics.CircleCollider(radius)], *massMoment)


class Object(physics.Object):
    def __init__(self, world, data):
        self.world = world
        self.data = data
        density = data['physics']['density'] if 'physics' in data else None
        self.type = data['type']
        if self.type == 'polygon':
            pos, self.points, colliders, mass, moment = genPolygon(data['points'], density)
        elif self.type == 'circle':
            self.radius = data['radius']
            colliders, mass, moment = genCircle(data['radius'], density)
            pos = data['pos']
        elif self.type == 'text':
            self.drawn_character = font.createCharacter(data['char'], data['size'])

            if density is None:
                mass = -1
                moment = -1
            else:
                mass = self.drawn_character.area * density
                moment = self.drawn_character.area_moment * mass

            pos = self.drawn_character.offset + data['pos']
            colliders = [physics.PolyCollider(convex) for convex in self.drawn_character.convex_polygons]

        self.trigger = data.get('trigger', None)
        if 'trigger' in data:
            def handler(other, normal, localA, localB):
                if self.trigger in self.world.script:
                    return self.world.script[self.trigger](self, other, normal, localA, localB)
                return False
            self.collide = handler

        super().__init__(mass, moment, data['restitution'], data['friction'])
        self.pos = pos
        for collider in colliders:
            self.colliders.append(collider)

        self.animated = data.get('animated', None)
        self.colour = data['colour']
        self.lethal = data['lethal']
        self.checkpoint = data.get('checkpoint', None)
        self.groups = data['groups']

        self.dirtyState = False
        self.dirtyProps = False

        self.displaylist = None
        self.fancy_displaylist = None

        self.initialState = {'colour': list(self.colour), 'pos': self.pos, 'vel': self.vel, 'rot': self.rot, 'rotV': self.rotV}

    def __setstate__(self, state):
        super().__setstate__(state)
        if self.trigger is not None:
            def handler(other, normal, localA, localB):
                if self.trigger in self.world.script:
                    return self.world.script[self.trigger](self, other, normal, localA, localB)
                return False
            self.collide = handler
        elif hasattr(self, 'collide'):
            delattr(self, 'collide')

    def reset(self):
        self.colour = self.initialState['colour']
        self.pos = self.initialState['pos']
        self.vel = self.initialState['vel']
        self.rot = self.initialState['rot']
        self.rotV = self.initialState['rotV']
        self.dirtyState = True

    def update(self, dt):
        if self.animated is not None:
            period = self.animated['period']
            maxOffset = self.animated['xOffset'], self.animated['yOffset']
            timeOffset = self.animated['tOffset']

            t = 2*((self.world.tick+timeOffset) % period) / period  # time 0-2
            if t > 1:
                t = 2 - t

            tn = 2*((self.world.tick+1+timeOffset) % period) / period
            if tn > 1:
                tn = 2-tn
            dt = tn-t

            self.pos = np.array(maxOffset, dtype=float) * t + self.initialState['pos']
            self.vel = np.array(maxOffset, dtype=float) * dt

    def create_displaylist(self):
        if self.displaylist is None:
            self.displaylist = glGenLists(1)
        glNewList(self.displaylist, GL_COMPILE)
        if self.type == 'polygon':
            glBegin(GL_TRIANGLES)
            try:
                for tri in util.triangulateSingle(self.points):
                    for point in tri:
                        glVertex2fv(point)
            except Exception as e:
                print(self, self.points.tolist())
                raise e
            glEnd()
            glColor3ub(0,0,0)

            #render.drawLoop(self.points, 1.5)

            #glLineWidth(1.5)
            glBegin(GL_LINE_LOOP)
            for point in self.points:
                glVertex2fv(point)
            glEnd()
        elif self.type == 'text':
            glBegin(GL_TRIANGLES)
            for tri in self.drawn_character.triangles:
                for point in tri:
                    glVertex2fv(point)
            glEnd()

            glColor3ub(0,0,0)

            #glLineWidth(1.5)
            for loop in self.drawn_character.loops:
                #render.drawLoop(loop, 1.5)
                glBegin(GL_LINE_LOOP)
                for point in loop:
                    glVertex2fv(point)
                glEnd()

        elif self.type == 'circle':
            circle = render.genCircle(self.radius)
            glBegin(GL_TRIANGLE_FAN)
            for point in circle:
                glVertex2fv(point)
            glEnd()
            glColor3ub(0,0,0)
            #render.drawLoop(circle, 1.5)

            #glLineWidth(1.5)
            glBegin(GL_LINE_LOOP)
            for point in circle:
                glVertex2fv(point)
            glEnd()
            if self.mass >= 0:
                glBegin(GL_LINES)
                glVertex2f(0,0)
                glVertex2f(self.radius,0)
                glEnd()
        glEndList()

    def render(self, camera):
        if not camera.is_visible(*self.bounds):
            return

        if self.displaylist is None:
            self.create_displaylist()
        colour = self.checkpoint['colour'] if hasattr(camera, 'player') and self is camera.player.checkpoint else self.colour

        glPushMatrix()

        glTranslatef(*self.pos, 0)
        glRotatef(math.degrees(self.rot), 0, 0, 1)

        glColor3ub(*colour)
        glCallList(self.displaylist)

        glPopMatrix()

    def create_fancy_displaylist(self, colour):
        if self.fancy_displaylist is None:
            displaylist = glGenLists(1)
        else:
            displaylist, _ = self.fancy_displaylist

        glNewList(displaylist, GL_COMPILE)
        if self.type == 'polygon':
            loops = [self.points]
        elif self.type == 'text':
            loops = [loop[::-1] for loop in self.drawn_character.loops]
        elif self.type == 'circle':
            loops = [render.genCircle(self.radius)[::-1]]

        float_colour = np.array(util.convertToLinear(np.divide(colour, 255)))

        render.draw_shaded(loops, float_colour, float_colour*SCALE, OFFSET)

        if self.type == 'circle' and self.mass >= 0:
            glBegin(GL_LINES)
            glVertex2f(0,0)
            glVertex2f(self.radius,0)
            glEnd()
        glEndList()

        self.fancy_displaylist = displaylist, colour

    def render_fancy(self, camera):
        if not camera.is_visible(*self.bounds):
            return
        colour = list(self.checkpoint['colour'] if hasattr(camera, 'player') and self is camera.player.checkpoint else self.colour)

        if self.fancy_displaylist is None:
            self.create_fancy_displaylist(colour)
        else:
            _, prev_colour = self.fancy_displaylist
            if prev_colour != colour:
                self.create_fancy_displaylist(colour)

        glPushMatrix()

        glTranslatef(*self.pos, 0)
        glRotatef(math.degrees(self.rot), 0, 0, 1)
        glCallList(self.fancy_displaylist[0])

        glPopMatrix()


    def cleanup(self):
        if self.displaylist is not None:
            glDeleteLists(self.displaylist, 1)
            self.displaylist = None
        if self.fancy_displaylist is not None:
            glDeleteLists(self.fancy_displaylist[0], 1)
            self.fancy_displaylist = None

def applyImpulse(objA, objB, pos, impulse):
    objA.vel = np.array(objA.vel) + objA.invMass * impulse
    objB.vel = np.array(objB.vel) - objB.invMass * impulse

    rA = util.cross2d(impulse, objA.pos - pos)
    rB = util.cross2d(impulse, objB.pos - pos)

    objB.rotV = objB.rotV - (objB.invMoment*impulse)*rA
    objB.rotV = objB.rotV - (objB.invMoment*impulse)*rB


class JumpConstraint(physics.CustomConstraint):
    def __init__(self, normal, localA, localB, strength):
        self.normal = np.array(normal, float)
        self.localA = localA
        self.localB = localB

        player_mass = BasePlayer.density * math.pi * BasePlayer.size**2

        self.target_velocity = 8 * strength
        #self.target_energy = player_mass*self.target_velocity**2/2
        self.max_impulse = player_mass * self.target_velocity * 2

        self.impulse = 0

    def apply(self, objA, objB):
        V = np.array([*objA.vel, 0, *objB.vel, objB.rotV]) # [ms-1, ms-1, s-1, ms-1, ms-1, s-1]
        M = np.array([objA.invMass, objA.invMass, objA.invMoment,
                      objB.invMass, objB.invMass, objB.invMoment]) # kg-1, kg-1, kg-1m-2, kg-1, kg-1, kg-1m-2

        #M[3:] *= 0.5

        offsetA = objA.localToGlobalVec(self.localA)
        offsetB = objB.localToGlobalVec(self.localB)
        J = np.array([-self.normal[0], -self.normal[1], util.cross2d(self.normal, offsetA),
                            self.normal[0], self.normal[1], -util.cross2d(self.normal, offsetB)]) # 1, 1, m, 1, 1, m

        bias = self.target_velocity # ms-1
        impulse = -(np.dot(V, J) + bias) / np.dot(J*J, M) # np.dot(V,J) = ms-1, np.dot(J*J, M) = kg-1, impulse = kgms-1

        new_impulse = self.impulse + impulse
        impulse = new_impulse - self.impulse
        self.impulse = new_impulse

        if impulse == 0:
            return

        dV = (J * M) * impulse

        objA.vel = np.array(objA.vel) + dV[0:2]
        objA.rotV = objA.rotV + dV[2]
        objB.vel = np.array(objB.vel) + dV[3:5]
        objB.rotV = objB.rotV + dV[5]

class BasePlayer(physics.Object):
    size = 15
    density = 0.5

    def __init__(self, world, colour, name):
        super().__init__(*circleMassMoment(BasePlayer.size, BasePlayer.density), 0.2, 0.8)
        self.world = world
        self.colliders.append(physics.CircleCollider(BasePlayer.size))
        self.pos = world.spawn + (np.random.random(2)-0.5) * 2
        self.vel = 0, 0
        self.colour = colour
        self.name = name
        self.dead = -1

        self.jump = False

        self.checkpoint = None
        self.action = 0,0

        self.displaylist = None
        self.fancy_displaylist = None

    def create_displaylist(self):
        if self.displaylist is None:
            self.displaylist = glGenLists(1)

        circle = render.genCircle(BasePlayer.size)
        glNewList(self.displaylist, GL_COMPILE)
        glBegin(GL_TRIANGLE_FAN)
        for point in circle:
            glVertex2fv(point)
        glEnd()
        glColor3ub(0,0,0)

        #render.drawLoop(circle, 1.5)
        #glLineWidth(1.5)

        glBegin(GL_LINE_LOOP)
        for point in circle:
            glVertex2fv(point)
        glEnd()

        glBegin(GL_LINES)
        glVertex2f(0,0)
        glVertex2f(BasePlayer.size, 0)
        glEnd()
        glEndList()

    def create_fancy_displaylist(self):
        if self.fancy_displaylist is None:
            self.fancy_displaylist = glGenLists(1)
        circle = render.genCircle(BasePlayer.size)
        glNewList(self.fancy_displaylist, GL_COMPILE)
        glBegin(GL_TRIANGLE_FAN)
        for point in circle:
            glVertex2fv(point)
        glEnd()
        glColor3ub(0,0,0)

        #render.drawLoop(circle, 1.5)
        #glLineWidth(1.5)
        colour = np.array(util.convertToLinear(np.divide(self.colour, 255)))
        render.draw_shaded([circle[::-1]], colour, colour*SCALE, OFFSET)

        glBegin(GL_LINES)
        glVertex2f(0,0)
        glVertex2f(BasePlayer.size, 0)
        glEnd()
        glEndList()

    def getAction(self):
        raise NotImplementedError

    def update(self, dt):
        if self.dead == -1:
            root = self.world.AABBTree.root
            if root is not None:
                gravity = self.world.gravity
                lower, upper = root.bounds
                pos = max((lower, (lower[0], upper[1]), (upper[0], lower[1]), upper), key=lambda corner: np.dot(corner, self.world.gravity))
                if np.dot(pos, gravity) - (np.dot(self.pos, gravity) + np.dot(self.vel, gravity)*0.5) < 0:
                    self.die()
                    return
            
            delta = 0.01
            if self.action[1] > 0:
                stopping = self.rotV
                roll = -1 if self.rotV > 0 else 1
            else:
                stopping = None
                roll = self.action[0]
            
            roll *= delta
            energy = abs(self.rotV)*self.rotV + roll
            self.rotV = math.sqrt(abs(energy))*util.sign(energy)

            if stopping is not None and util.sign(self.rotV) != util.sign(stopping):
                self.rotV = 0

            if not isinstance(self.jump, bool):
                for i, (_, constraint) in enumerate(self.constraints):
                    if constraint is self.jump:
                        break
                else:
                    raise ValueError
                del self.constraints[i]
            self.jump = self.action[1] < -0.1

            if abs(self.rotV + roll) < max(0.7, abs(self.rotV)):
                self.rotV += roll
        elif self.dead >= 3:
            self.die()
        else:
            self.dead += 1

    def render(self, camera):
        if self.displaylist is None:
            self.create_displaylist()

        glPushMatrix()

        glTranslatef(*self.pos, 0)
        glRotatef(math.degrees(self.rot), 0, 0, 1)
        glColor3ubv(self.colour)

        #render.drawCircle((0,0), BasePlayer.size, self.colour)
        glCallList(self.displaylist)

        glPopMatrix()

    def render_fancy(self, camera):
        if self.fancy_displaylist is None:
            self.create_fancy_displaylist()

        glPushMatrix()

        glTranslatef(*self.pos, 0)
        glRotatef(math.degrees(self.rot), 0, 0, 1)

        #render.drawCircle((0,0), BasePlayer.size, self.colour)

        glColor3ub(*self.colour)
        glCallList(self.fancy_displaylist)

        glPopMatrix()


    def collide(self, other, normal, localA, localB):
        if hasattr(other, 'lethal') and other.lethal:
            self.dead = max(self.dead, 0)

        if hasattr(other, 'checkpoint') and type(other.checkpoint) == dict: # make sure it's not another player
            self.checkpoint = other

        gravity = util.normalise(np.array(self.world.gravity, dtype=float))
        if np.dot(normal, gravity) < -0.7 and self.jump is True:
            self.jump = JumpConstraint(normal, localA, localB, -self.action[1])
            self.constraints.append((other, self.jump))
            return True # Ensure no contact constraint interferes
        return False

    def die(self):
        self.dead = -1
        if self.checkpoint is None:
            spawn = self.world.spawn
        elif self.checkpoint not in self.world:
            self.checkpoint = None
            spawn = self.world.spawn
        else:
            obj = self.checkpoint
            spawn = np.add(obj.pos, (obj.checkpoint['xOffset'], obj.checkpoint['yOffset']))
        self.pos = np.array(spawn, float) + (np.random.random(2)-0.5)*2
        self.vel = 0, 0

        if not isinstance(self.jump, bool):
            for i, (_, constraint) in enumerate(self.constraints):
                if constraint is self.jump:
                    break
            else:
                raise ValueError
            del self.constraints[i]
        self.jump = False
        if 'onDeath' in self.world.script:
            self.world.script['onDeath'](self)

    def cleanup(self):
        if self.displaylist is not None:
            glDeleteLists(self.displaylist, 1)
            self.displaylist = None

class OtherPlayer(BasePlayer):
    font = None
    def __init__(self, world, colour, name):
        super().__init__(world, colour, name)
        self.texture = None

    def initialise_texture(self):
        if OtherPlayer.font is None:
            OtherPlayer.font = pygame.font.SysFont(None, 25)
        surface = OtherPlayer.font.render(self.name, True, (255,0,0), (0,0,0))

        if self.texture is None:
            self.texture = int(glGenTextures(1)) # sometimes retures np.uintc
        self.texture_size = surface.get_size()

        arr = np.zeros((*self.texture_size[::-1],4), np.ubyte) + 0xff
        arr[:,:,3] = [[surface.get_at((x,y))[0] for x in range(self.texture_size[0])] for y in range(self.texture_size[1])]
        #arr = (np.random.random((*self.texture_size[::-1], 4)) * 256).astype(np.ubyte)

        glBindTexture(GL_TEXTURE_2D, self.texture)

        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)

        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, *self.texture_size, 0, GL_RGBA, GL_UNSIGNED_BYTE, arr)

    def create_fancy_displaylist(self):
        super().create_fancy_displaylist()
        self.initialise_texture()

    def create_displaylist(self):
        super().create_displaylist()
        self.initialise_texture()

    def cleanup(self):
        super().cleanup()
        if self.texture is not None:
            glDeleteTextures(self.texture)
            self.texture = None

    def getAction(self):
        return self.action

    def render_texture(self, fancy):
        glPushMatrix()

        if fancy:
            glDepthFunc(GL_ALWAYS)

        glTranslatef(self.pos[0]-self.texture_size[0]/2, self.pos[1]-self.texture_size[1]/2 - 25,0)
        glScale(*self.texture_size, 0)

        glBindTexture(GL_TEXTURE_2D, self.texture)

        glEnable(GL_TEXTURE_2D)

        glEnable(GL_BLEND) # Dunno why initial call in main.py doesn't work
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        colour = [0.3] * 3
        if fancy:
            colour = util.convertToLinear(colour)
        glColor3fv(colour)

        glBegin(GL_TRIANGLE_FAN)
        glTexCoord2f(0, 0)
        glVertex2f(0,0)
        glTexCoord2f(1, 0)
        glVertex2f(1,0)
        glTexCoord2f(1, 1)
        glVertex2f(1,1)
        glTexCoord2f(0, 1)
        glVertex2f(0,1)
        glEnd()

        glDisable(GL_TEXTURE_2D)

        if fancy:
            glDepthFunc(GL_LEQUAL) # Restore

        glPopMatrix()

    def render(self, camera):
        super().render(camera)
        self.render_texture(False)

    def render_fancy(self, camera):
        super().render_fancy(camera)
        self.render_texture(True)
        

class Player(BasePlayer):
    def __init__(self, world, colour, name, controls):
        super().__init__(world, colour, name)
        self.controls = controls

    def getAction(self):
        pressed = pygame.key.get_pressed()
        return [pressed[a] - pressed[b] for a, b in self.controls]
