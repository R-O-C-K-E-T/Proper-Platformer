import numpy as np
import math, random, pygame
from typing import *

from OpenGL import GL as gl
from OpenGL import GLU as glu

import physics.physics as physics

import util, camera, font, decomposition, render, actions

OFFSET = 5
SCALE = 0.3

def calculate_props(polygon: List[util.Vec], density: float):
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

def gen_polygon(points: List[util.Vec], density: float):
    points = np.array(points, dtype=float)
    if not util.check_winding(points):
        points = points[::-1]

    mass, moment, com = calculate_props(points, density)
    points -= com

    colliders = [physics.PolyCollider(decomposition.convert_from(polygon)) for polygon in decomposition.decompose(decomposition.convert_into(points[::-1]))]

    return com, points, colliders, mass, moment

def circle_mass_moment(radius: float, density: float):
    mass = math.pi * radius**2 * density
    moment = mass * radius**2 / 2
    return mass, moment


def gen_circle(radius: float, density: float):
    massMoment = (-1, -1) if density is None else circle_mass_moment(radius, density)
    return ([physics.CircleCollider(radius)], *massMoment)


class Object(physics.Object):
    def __init__(self, world, data: Dict[str, Any]):
        self.world = world
        self.data = data
        density = data['physics']['density'] if 'physics' in data else None
        self.type = data['type']
        if self.type == 'polygon':
            pos, self.points, colliders, mass, moment = gen_polygon(data['points'], density)
        elif self.type == 'circle':
            self.radius = data['radius']
            colliders, mass, moment = gen_circle(data['radius'], density)
            pos = data['pos']
        elif self.type == 'text':
            self.drawn_character = font.create_character(data['char'], data['size'])

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
            def handler(other, normal, local_a, local_b):
                if self.trigger in self.world.script:
                    return self.world.script[self.trigger](self, other, normal, local_a, local_b)
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

        self.dirty_state = False
        self.dirty_props = False

        self.displaylist = None
        self.fancy_displaylist = None

        self.initial_state = {'colour': list(self.colour), 'pos': self.pos, 'vel': self.vel, 'rot': self.rot, 'rot_vel': self.rot_vel}

    def __setstate__(self, state):
        super().__setstate__(state)
        if self.trigger is not None:
            def handler(other, normal, local_a, local_b):
                if self.trigger in self.world.script:
                    return self.world.script[self.trigger](self, other, normal, local_a, local_b)
                return False
            self.collide = handler
        elif hasattr(self, 'collide'):
            delattr(self, 'collide')

    def reset(self):
        self.colour = self.initial_state['colour']
        self.pos = self.initial_state['pos']
        self.vel = self.initial_state['vel']
        self.rot = self.initial_state['rot']
        self.rot_vel = self.initial_state['rot_vel']
        self.dirty_state = True

    def update(self, dt):
        if self.animated is not None:
            period = self.animated['period']
            max_offset = self.animated['dx'], self.animated['dy']
            time_offset = self.animated['dt']

            t = 2*((self.world.tick+time_offset) % period) / period  # time 0-2
            if t > 1:
                t = 2 - t

            tn = 2*((self.world.tick+1+time_offset) % period) / period
            if tn > 1:
                tn = 2-tn
            dt = tn-t

            self.pos = np.array(max_offset, dtype=float) * t + self.initial_state['pos']
            self.vel = np.array(max_offset, dtype=float) * dt

    def create_displaylist(self):
        if self.displaylist is None:
            self.displaylist = gl.glGenLists(1)
        gl.glNewList(self.displaylist, gl.GL_COMPILE)
        if self.type == 'polygon':
            gl.glBegin(gl.GL_TRIANGLES)
            try:
                for tri in util.triangulate_single(self.points):
                    for point in tri:
                        gl.glVertex2fv(point)
            except Exception as e:
                print(self, self.points.tolist())
                raise e
            gl.glEnd()
            gl.glColor3ub(0,0,0)

            #render.draw_loop(self.points, 1.5)

            #gl.glLineWidth(1.5)
            gl.glBegin(gl.GL_LINE_LOOP)
            for point in self.points:
                gl.glVertex2fv(point)
            gl.glEnd()
        elif self.type == 'text':
            gl.glBegin(gl.GL_TRIANGLES)
            for tri in self.drawn_character.triangles:
                for point in tri:
                    gl.glVertex2fv(point)
            gl.glEnd()

            gl.glColor3ub(0,0,0)

            #gl.glLineWidth(1.5)
            for loop in self.drawn_character.loops:
                #render.draw_loop(loop, 1.5)
                gl.glBegin(gl.GL_LINE_LOOP)
                for point in loop:
                    gl.glVertex2fv(point)
                gl.glEnd()

        elif self.type == 'circle':
            circle = render.gen_circle(self.radius)
            gl.glBegin(gl.GL_TRIANGLE_FAN)
            for point in circle:
                gl.glVertex2fv(point)
            gl.glEnd()
            gl.glColor3ub(0,0,0)
            #render.draw_loop(circle, 1.5)

            #gl.glLineWidth(1.5)
            gl.glBegin(gl.GL_LINE_LOOP)
            for point in circle:
                gl.glVertex2fv(point)
            gl.glEnd()
            if self.mass >= 0:
                gl.glBegin(gl.GL_LINES)
                gl.glVertex2f(0,0)
                gl.glVertex2f(self.radius,0)
                gl.glEnd()
        gl.glEndList()

    def render(self, camera):
        if not camera.is_visible(*self.bounds):
            return

        if self.displaylist is None:
            self.create_displaylist()
        colour = self.checkpoint['colour'] if hasattr(camera, 'player') and self is camera.player.checkpoint else self.colour

        gl.glPushMatrix()

        gl.glTranslatef(*self.pos, 0)
        gl.glRotatef(math.degrees(self.rot), 0, 0, 1)

        gl.glColor3ub(*colour)
        gl.glCallList(self.displaylist)

        gl.glPopMatrix()

    def create_fancy_displaylist(self, colour: Tuple[float, float, float]):
        if self.fancy_displaylist is None:
            displaylist = gl.glGenLists(1)
        else:
            displaylist, _ = self.fancy_displaylist

        gl.glNewList(displaylist, gl.GL_COMPILE)
        if self.type == 'polygon':
            loops = [self.points]
        elif self.type == 'text':
            loops = [loop[::-1] for loop in self.drawn_character.loops]
        elif self.type == 'circle':
            loops = [render.gen_circle(self.radius)[::-1]]
        else:
            assert False

        float_colour = np.array(util.convert_to_linear(np.divide(colour, 255)))

        render.draw_shaded(loops, float_colour, float_colour*SCALE, OFFSET)

        if self.type == 'circle' and self.mass >= 0:
            gl.glBegin(gl.GL_LINES)
            gl.glVertex2f(0,0)
            gl.glVertex2f(self.radius,0)
            gl.glEnd()
        gl.glEndList()

        self.fancy_displaylist = displaylist, colour

    def render_fancy(self, camera):
        if not camera.is_visible(*self.bounds):
            return
        colour = tuple(self.checkpoint['colour'] if hasattr(camera, 'player') and self is camera.player.checkpoint else self.colour)

        if self.fancy_displaylist is None:
            self.create_fancy_displaylist(colour)
        else:
            _, prev_colour = self.fancy_displaylist
            if prev_colour != colour:
                self.create_fancy_displaylist(colour)

        gl.glPushMatrix()

        gl.glTranslatef(*self.pos, 0)
        gl.glRotatef(math.degrees(self.rot), 0, 0, 1)
        gl.glCallList(self.fancy_displaylist[0])

        gl.glPopMatrix()


    def cleanup(self):
        if self.displaylist is not None:
            gl.glDeleteLists(self.displaylist, 1)
            self.displaylist = None
        if self.fancy_displaylist is not None:
            gl.glDeleteLists(self.fancy_displaylist[0], 1)
            self.fancy_displaylist = None

class JumpConstraint(physics.CustomConstraint):
    def __init__(self, normal, local_a, local_b, strength):
        self.normal = np.array(normal, float)
        self.local_a = local_a
        self.local_b = local_b

        player_mass = BasePlayer.density * math.pi * BasePlayer.size**2

        self.target_velocity = 8 * strength
        #self.target_energy = player_mass*self.target_velocity**2/2
        self.max_impulse = player_mass * self.target_velocity * 2

        self.impulse = 0

    def apply(self, obj_a, obj_b):
        V = np.array([*obj_a.vel, 0, *obj_b.vel, obj_b.rot_vel]) # [ms-1, ms-1, s-1, ms-1, ms-1, s-1]
        M = np.array([obj_a.inv_mass, obj_a.inv_mass, obj_a.inv_moment,
                      obj_b.inv_mass, obj_b.inv_mass, obj_b.inv_moment]) # kg-1, kg-1, kg-1m-2, kg-1, kg-1, kg-1m-2

        #M[3:] *= 0.5

        offsetA = obj_a.local_to_global_vec(self.local_a)
        offsetB = obj_b.local_to_global_vec(self.local_b)
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

        obj_a.vel = np.array(obj_a.vel) + dV[0:2]
        obj_a.rot_vel = obj_a.rot_vel + dV[2]
        obj_b.vel = np.array(obj_b.vel) + dV[3:5]
        obj_b.rot_vel = obj_b.rot_vel + dV[5]

class BasePlayer(physics.Object):
    size = 15
    density = 0.5

    def __init__(self, world, colour: Tuple[float, float, float], name: str):
        super().__init__(*circle_mass_moment(BasePlayer.size, BasePlayer.density), 0.2, 0.8)
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
            self.displaylist = gl.glGenLists(1)

        circle = render.gen_circle(BasePlayer.size)
        gl.glNewList(self.displaylist, gl.GL_COMPILE)
        gl.glBegin(gl.GL_TRIANGLE_FAN)
        for point in circle:
            gl.glVertex2fv(point)
        gl.glEnd()
        gl.glColor3ub(0,0,0)

        #render.draw_loop(circle, 1.5)
        #gl.glLineWidth(1.5)

        gl.glBegin(gl.GL_LINE_LOOP)
        for point in circle:
            gl.glVertex2fv(point)
        gl.glEnd()

        gl.glBegin(gl.GL_LINES)
        gl.glVertex2f(0,0)
        gl.glVertex2f(BasePlayer.size, 0)
        gl.glEnd()
        gl.glEndList()

    def create_fancy_displaylist(self):
        if self.fancy_displaylist is None:
            self.fancy_displaylist = gl.glGenLists(1)
        circle = render.gen_circle(BasePlayer.size)
        gl.glNewList(self.fancy_displaylist, gl.GL_COMPILE)
        gl.glBegin(gl.GL_TRIANGLE_FAN)
        for point in circle:
            gl.glVertex2fv(point)
        gl.glEnd()
        gl.glColor3ub(0,0,0)

        #render.draw_loop(circle, 1.5)
        #gl.glLineWidth(1.5)
        colour = np.array(util.convert_to_linear(np.divide(self.colour, 255)))
        render.draw_shaded([circle[::-1]], colour, colour*SCALE, OFFSET)

        gl.glBegin(gl.GL_LINES)
        gl.glVertex2f(0,0)
        gl.glVertex2f(BasePlayer.size, 0)
        gl.glEnd()
        gl.glEndList()

    def get_action(self):
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
                stopping = self.rot_vel
                roll = -1 if self.rot_vel > 0 else 1
            else:
                stopping = None
                roll = self.action[0]
            
            roll *= delta
            energy = abs(self.rot_vel)*self.rot_vel + roll
            self.rot_vel = math.sqrt(abs(energy))*util.sign(energy)

            if stopping is not None and util.sign(self.rot_vel) != util.sign(stopping):
                self.rot_vel = 0

            if not isinstance(self.jump, bool):
                for i, (_, constraint) in enumerate(self.constraints):
                    if constraint is self.jump:
                        break
                else:
                    raise ValueError
                del self.constraints[i]
            self.jump = self.action[1] < -0.1

            if abs(self.rot_vel + roll) < max(0.7, abs(self.rot_vel)):
                self.rot_vel += roll
        elif self.dead >= 3:
            self.die()
        else:
            self.dead += 1

    def render(self, camera):
        if self.displaylist is None:
            self.create_displaylist()

        gl.glPushMatrix()

        gl.glTranslatef(*self.pos, 0)
        gl.glRotatef(math.degrees(self.rot), 0, 0, 1)
        gl.glColor3ubv(self.colour)

        #render.draw_circle((0,0), BasePlayer.size, self.colour)
        gl.glCallList(self.displaylist)

        gl.glPopMatrix()

    def render_fancy(self, camera):
        if self.fancy_displaylist is None:
            self.create_fancy_displaylist()

        gl.glPushMatrix()

        gl.glTranslatef(*self.pos, 0)
        gl.glRotatef(math.degrees(self.rot), 0, 0, 1)

        #render.draw_circle((0,0), BasePlayer.size, self.colour)

        gl.glColor3ub(*self.colour)
        gl.glCallList(self.fancy_displaylist)

        gl.glPopMatrix()


    def collide(self, other, normal, local_a, local_b):
        if hasattr(other, 'lethal') and other.lethal:
            self.dead = max(self.dead, 0)

        if hasattr(other, 'checkpoint') and type(other.checkpoint) == dict: # make sure it's not another player
            self.checkpoint = other

        gravity = util.normalise(np.array(self.world.gravity, dtype=float))
        if np.dot(normal, gravity) < -0.7 and self.jump is True:
            self.jump = JumpConstraint(normal, local_a, local_b, -self.action[1])
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
            spawn = np.add(obj.pos, (obj.checkpoint['dx'], obj.checkpoint['dy']))
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
        if 'on_death' in self.world.script:
            self.world.script['on_death'](self)

    def cleanup(self):
        if self.displaylist is not None:
            gl.glDeleteLists(self.displaylist, 1)
            self.displaylist = None

class OtherPlayer(BasePlayer):
    font = None
    def __init__(self, world, colour: Tuple[float, float, float], name: str):
        super().__init__(world, colour, name)
        self.texture = None

    def initialise_texture(self):
        if OtherPlayer.font is None:
            OtherPlayer.font = pygame.font.SysFont(None, 25)
        surface = OtherPlayer.font.render(self.name, True, (255,0,0), (0,0,0))

        if self.texture is None:
            self.texture = int(gl.glGenTextures(1)) # sometimes retures np.uintc
        self.texture_size = surface.get_size()

        arr = np.zeros((*self.texture_size[::-1],4), np.ubyte) + 0xff
        arr[:,:,3] = [[surface.get_at((x,y))[0] for x in range(self.texture_size[0])] for y in range(self.texture_size[1])]
        #arr = (np.random.random((*self.texture_size[::-1], 4)) * 256).astype(np.ubyte)

        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture)

        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_REPEAT)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_REPEAT)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)

        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA8, *self.texture_size, 0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, arr)

    def create_fancy_displaylist(self):
        super().create_fancy_displaylist()
        self.initialise_texture()

    def create_displaylist(self):
        super().create_displaylist()
        self.initialise_texture()

    def cleanup(self):
        super().cleanup()
        if self.texture is not None:
            gl.glDeleteTextures(self.texture)
            self.texture = None

    def get_action(self):
        return self.action

    def render_texture(self, fancy):
        gl.glPushMatrix()

        if fancy:
            gl.glDepthFunc(gl.GL_ALWAYS)

        gl.glTranslatef(self.pos[0]-self.texture_size[0]/2, self.pos[1]-self.texture_size[1]/2 - 25,0)
        gl.glScale(*self.texture_size, 0)

        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture)

        gl.glEnable(gl.GL_TEXTURE_2D)

        gl.glEnable(gl.GL_BLEND) # Dunno why initial call in main.py doesn't work
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

        colour = [0.3] * 3
        if fancy:
            colour = util.convert_to_linear(colour)
        gl.glColor3fv(colour)

        gl.glBegin(gl.GL_TRIANGLE_FAN)
        gl.glTexCoord2f(0, 0)
        gl.glVertex2f(0,0)
        gl.glTexCoord2f(1, 0)
        gl.glVertex2f(1,0)
        gl.glTexCoord2f(1, 1)
        gl.glVertex2f(1,1)
        gl.glTexCoord2f(0, 1)
        gl.glVertex2f(0,1)
        gl.glEnd()

        gl.glDisable(gl.GL_TEXTURE_2D)

        if fancy:
            gl.glDepthFunc(gl.GL_LEQUAL) # Restore

        gl.glPopMatrix()

    def render(self, camera):
        super().render(camera)
        self.render_texture(False)

    def render_fancy(self, camera):
        super().render_fancy(camera)
        self.render_texture(True)
        

class Player(BasePlayer):
    def __init__(self, world, colour: Tuple[float, float, float], name: str, controls):
        super().__init__(world, colour, name)
        self.controls = controls

    def get_action(self):
        pressed = pygame.key.get_pressed()
        return [pressed[a] - pressed[b] for a, b in self.controls]
