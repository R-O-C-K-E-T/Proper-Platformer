import numpy as np
import math, functools, types, json, random, copy
from traceback import print_exc

import physics.physics as physics
import util, camera, shared, safe, objects, actions

class World(physics.World):
    def __init__(self, isHost):
        super().__init__(baumgarteBias=0.1, solverSteps=10, slopP=0.3, slopR=0.01)
        self.steps = 3
        self.script = {}
        self.spawn = 0,0

        self.curObjID = 0
        self.objects = {}
        self.players = []

        self.tick = 0
        self.isHost = isHost

    def copy(self): # Too slow, rip
        script = dict(filter(lambda item: type(item[1]) != types.ModuleType, self.script.items()))

        memo = {}
        for obj in self:
            if hasattr(obj, 'displayList'):
                memo[id(obj.displayList)] = obj.displayList
            if hasattr(obj,'data'):
                memo[id(obj.data)] = obj.data
            if hasattr(obj,'initialState'):
                memo[id(obj.initialState)] = obj.initialState
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

    def copyObjects(self, objects, ID):
        memo = {id(self) : self}
        newObjects = copy.deepcopy(objects, memo=memo)

        for obj in newObjects:
            obj.groups.append(ID)

        for obj in newObjects:
            self.add_object(obj)

        return newObjects

    def makePrototype(self, objects):
        objects = list(objects)

        for obj in objects:
            self.removeObject(obj)

        i = 0
        def prototype():
            nonlocal i
            newObjects = self.copyObjects(objects, i)
            i += 1
            return newObjects
        return prototype

    def createObject(self, data):
        obj = objects.Object(self, actions.add_default_properties(data))
        self.add_object(obj)
        return obj

    def add_object(self, obj):
        if isinstance(obj, objects.Object):
            self.objects[self.curObjID] = obj
            self.curObjID += 1
        if isinstance(obj, objects.BasePlayer):
            self.players.append(obj)
        self.append(obj)

    def removeObject(self, obj):
        self.remove(obj)
        obj.cleanup()
        if isinstance(obj, objects.Object):
            ID = util.findKey(self.objects, obj)
            del self.objects[ID]
        if isinstance(obj, objects.BasePlayer):
            self.players.remove(obj)

    def addConstraint(self, objA, objB, data):
        if data['type'] == 'pivot':
            point = np.array(data['pos'], dtype=float)
            constraint = physics.PivotConstraint(util.rotate(
                  point - objA.pos, -objA.rot), util.rotate(point - objB.pos, -objB.rot))
        elif data['type'] == 'fixed':
            point = np.array(data['pos'], dtype=float)
            constraint = physics.FixedConstraint(util.rotate(
                  point - objA.pos, -objA.rot), util.rotate(point - objB.pos, -objB.rot))
        elif data['type'] == 'slider':
            pointA, pointB = np.array(data['pos'], dtype=float)
            normal = util.getNormal(pointA, pointB)
            constraint = physics.SliderConstraint(util.rotate(pointA - objA.pos, -objA.rot),
                                             util.rotate(pointB - objB.pos, -objB.rot),
                                             util.rotate(normal, -objA.rot))
        objA.constraints.append((objB, constraint))

    def getGroup(self, *names):
        return [obj for obj in self.objects.values() if all(name in obj.groups for name in names)]

    def loadScript(self, script):
        self.script = {'players': self.players, 'time': self.tick, 'getGroup': self.getGroup, 'math': math, 'random':random, 'objects': self.objects, 'BasePlayer': objects.BasePlayer, 'Object': objects.Object}
        if self.isHost:
            self.script.update({'add_object': self.add_object, 'removeObject': self.removeObject, 'createObject' : self.createObject, 'makePrototype': self.makePrototype})
        else:
            self.script.update({})

        exec(script, self.script, self.script)

        if 'load' in self.script:
            try:
                self.script['load']()
            except Exception:
                print_exc()
