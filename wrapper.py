import numpy as np
import math, functools, types, random, copy
from traceback import print_exc

import physics.physics as physics
import util, objects, actions

class World(physics.World):
    def __init__(self, isHost):
        super().__init__(baumgarte_bias=0.1, solver_steps=10, slop_p=0.3, slop_r=0.01)
        self.steps = 3
        self.script = {}
        self.spawn = 0,0

        self.current_object_id = 0
        self.objects = {}
        self.players = []

        self.tick = 0
        self.isHost = isHost

    def copy(self): # Too slow, rip
        script = dict(filter(lambda item: type(item[1]) != types.ModuleType, self.script.items()))

        memo = {}
        for obj in self:
            if hasattr(obj, 'displaylist'):
                memo[id(obj.displaylist)] = obj.displaylist
            if hasattr(obj, 'fancy_displaylist'):
                memo[id(obj.fancy_displaylist)] = obj.fancy_displaylist
            if hasattr(obj,'data'):
                memo[id(obj.data)] = obj.data
            if hasattr(obj,'initial_state'):
                memo[id(obj.initial_state)] = obj.initial_state
            if hasattr(obj,'points'):
                memo[id(obj.points)] = obj.points
            for constraint in obj.constraints:
                memo[id(constraint[1])] = constraint[1]
            for collider in obj.colliders:
                memo[id(collider)] = collider

        if '__builtins__' in script:
            memo[id(script['__builtins__'])] = script['__builtins__']
        res = copy.deepcopy(self, memo=memo)

        for key, val in res.script.items(): # Update script scopes
            if type(val) == types.FunctionType and val.__globals__ is self.script:
                func = types.FunctionType(val.__code__, res.script, name=val.__name__,
                               argdefs=val.__defaults__,
                               closure=val.__closure__)
                func = functools.update_wrapper(func, val)
                func.__kwdefaults__ = val.__kwdefaults__
                res.script[key] = func
        return res

    def update(self, dt=1):
        steps = math.ceil(self.steps * dt)
        for _ in range(steps):
            super().update(dt/steps)
        self.tick += dt

        self.script['time'] = self.tick
        if 'tick' in self.script:
            try:
                self.script['tick']()
            except:
                print_exc()

        for obj in self:
            obj.update(dt)

    def copy_objects(self, objects, ID):
        memo = {id(self) : self}
        new_objects = copy.deepcopy(objects, memo=memo)

        for obj in new_objects:
            obj.groups.append(ID)

        for obj in new_objects:
            self.add_object(obj)

        return new_objects

    def make_prototype(self, objects):
        objects = list(objects)

        for obj in objects:
            self.remove_object(obj)

        i = 0
        def prototype():
            nonlocal i
            new_objects = self.copy_objects(objects, i)
            i += 1
            return new_objects
        return prototype

    def create_object(self, data):
        obj = objects.Object(self, actions.add_default_properties(data))
        self.add_object(obj)
        return obj

    def add_object(self, obj):
        if isinstance(obj, objects.Object):
            self.objects[self.current_object_id] = obj
            self.current_object_id += 1
        if isinstance(obj, objects.BasePlayer):
            self.players.append(obj)
        self.append(obj)

    def remove_object(self, obj):
        self.remove(obj)
        obj.cleanup()
        if isinstance(obj, objects.Object):
            ID = util.find_key(self.objects, obj)
            del self.objects[ID]
        if isinstance(obj, objects.BasePlayer):
            self.players.remove(obj)

    def add_constraint(self, obj_a, obj_b, data):
        if data['type'] == 'pivot':
            point = np.array(data['pos'], dtype=float)
            constraint = physics.PivotConstraint(util.rotate(
                  point - obj_a.pos, -obj_a.rot), util.rotate(point - obj_b.pos, -obj_b.rot))
        elif data['type'] == 'fixed':
            point = np.array(data['pos'], dtype=float)
            constraint = physics.FixedConstraint(util.rotate(
                  point - obj_a.pos, -obj_a.rot), util.rotate(point - obj_b.pos, -obj_b.rot))
        elif data['type'] == 'slider':
            pointA, pointB = np.array(data['pos'], dtype=float)
            normal = util.get_normal(pointA, pointB)
            constraint = physics.SliderConstraint(util.rotate(pointA - obj_a.pos, -obj_a.rot),
                                             util.rotate(pointB - obj_b.pos, -obj_b.rot),
                                             util.rotate(normal, -obj_a.rot))
        obj_a.constraints.append((obj_b, constraint))

    def get_group(self, *names):
        return [obj for obj in self.objects.values() if all(name in obj.groups for name in names)]

    def load_script(self, script):
        self.script = {'players': self.players, 'time': self.tick, 'get_group': self.get_group, 'math': math, 'random':random, 'objects': self.objects, 'BasePlayer': objects.BasePlayer, 'Object': objects.Object}
        if self.isHost:
            self.script.update({'add_object': self.add_object, 'remove_object': self.remove_object, 'create_object' : self.create_object, 'make_prototype': self.make_prototype})
        else:
            self.script.update({})

        exec(script, self.script, self.script)

        if 'load' in self.script:
            try:
                self.script['load']()
            except Exception:
                print_exc()
