# distutils: language = c++

from libcpp.vector cimport vector
from libcpp cimport bool
from libcpp.unordered_map cimport unordered_map
from libcpp.utility cimport pair
from morelibcpp cimport remove
cimport libcpp.iterator
from cpython.ref cimport PyObject

cimport objects, aabb
cimport physics as cPhysics
from vector cimport Vec2d

import copy, sys

cdef class CustomList:
   cdef _list
   
   def _add(self, obj):
      raise NotImplemented

   def _remove(self, obj):
      raise NotImplemented
   
   def _clear(self):
      for obj in self._list:
         self._remove(obj)
   
   def __cinit__(self, *args, **kwargs):
      self._list = []

   def __init__(self, source=None):
      self._list = []
      if source is not None:
         for item in source:
            self.append(item)
   
   def __getstate__(self):
      state = {}
      state['_list'] = self._list
      if hasattr(self, '__dict__'):
         state.update(self.__dict__)
      return state

   def __setstate__(self, state):
      self._clear()
      self._list = state['_list']
      del state['_list']
      for item in self._list:
         self._add(item)
      if hasattr(self, '__dict__'):
         self.__dict__.update(state)

   def clear(self):
      self._clear()
      self._list.clear()

   def append(self, obj):
      self._add(obj)
      self._list.append(obj)
   
   def remove(self, obj):
      self._remove(obj)
      self._list.remove(obj)
   
   def pop(self, index=-1):
      obj = self._list[index]
      self._remove(obj)
      del self._list[index]
      return obj
   
   def index(self, obj):
      return self._list.index(obj)
   
   def __getitem__(self, key):
      return self._list[key]
   
   def __setitem__(self,key,value):
      prev = self._list[key]
      self._list[key] = value

      self._remove(prev)
      self._add(value)
   
   def __delitem__(self, key):
      self.pop(key)
   def __len__(self):
      return len(self._list)
   def __contains__(self, obj):
      return obj in self._list
   def __iter__(self):
      return iter(self._list)
   def __str__(self):
      return str(self._list)
   def __repr__(self):
      return repr(self._list)

cdef Vec2d convertToVec(obj):
   return Vec2d(obj[0],obj[1])
cdef convertFromVec(Vec2d vec):
   return vec.x, vec.y

cdef class BaseCollider:
   cdef objects.BaseCollider* generate(self, objects.Object *obj):
      raise NotImplemented

cdef class CircleCollider(BaseCollider):
   cdef radius
   
   def __init__(self, radius):
      self.radius = radius

   @property
   def radius(self):
      return self.radius

   cdef objects.BaseCollider* generate(self, objects.Object *obj):
      return new objects.CircleCollider(obj, self.radius)

cdef class PolyCollider:
   cdef points

   def __init__(self, points):
      self.points = points
   
   @property
   def points(self):
      return self.points

   cdef objects.BaseCollider* generate(self, objects.Object *obj):
      cdef vector[Vec2d] pointsVec
      for point in self.points:
         pointsVec.push_back(convertToVec(point))
      
      return new objects.PolyCollider(obj, pointsVec)

cdef class BaseConstraint:
   cdef objects.BaseConstraint* generate(self, objects.Object *objA, objects.Object *objB):
      raise NotImplemented


cdef void apply(PyObject *self, objects.Object* objA, objects.Object* objB):
   pyObjA = <object>objectMap[objA]
   pyObjB = <object>objectMap[objB]
   (<object>self).apply(pyObjA, pyObjB)

cdef class CustomConstraint(BaseConstraint):
   cdef objects.BaseConstraint* generate(self, objects.Object *objA, objects.Object *objB):
      return new objects.CustomConstraint[PyObject*](objA, objB, <PyObject*>self, apply)

   def apply(self, objA, objB):
      raise NotImplemented


cdef class PivotConstraint(BaseConstraint):
   cdef localA
   cdef localB

   @property
   def localA(self):
      return self.localA
   @property
   def localB(self):
      return self.localB

   def __init__(self, localA, localB):
      self.localA = localA
      self.localB = localB

   cdef objects.BaseConstraint* generate(self, objects.Object *objA, objects.Object *objB):
      return new objects.PivotConstraint(objA, objB, convertToVec(self.localA), convertToVec(self.localB))

cdef class FixedConstraint:
   cdef localA
   cdef localB

   def __init__(self, localA, localB):
      self.localA = localA
      self.localB = localB

   @property
   def localA(self):
      return self.localA
   @property
   def localB(self):
      return self.localB

   cdef objects.BaseConstraint* generate(self, objects.Object *objA, objects.Object *objB):
      return new objects.FixedConstraint(objA, objB, convertToVec(self.localA), convertToVec(self.localB))
   
cdef class SliderConstraint:
   cdef localA
   cdef localB
   cdef normal

   @property
   def localA(self):
      return self.localA
   @property
   def localB(self):
      return self.localB
   @property
   def normal(self):
      return self.normal

   def __init__(self, localA, localB, normal):
      self.localA = localA
      self.localB = localB
      self.normal = normal

   cdef objects.BaseConstraint* generate(self, objects.Object *objA, objects.Object *objB):
      return new objects.SliderConstraint(objA, objB, convertToVec(self.localA), convertToVec(self.localB), convertToVec(self.normal))

ctypedef PyObject* pyPointer
ctypedef objects.Object* objPointer
ctypedef objects.BaseCollider* colliderPointer
ctypedef objects.BaseConstraint* constraintPointer

cdef unordered_map[objPointer, pyPointer] objectMap
cdef bool collisionHandler(objects.Object* objA, objects.Object* objB, Vec2d normal, Vec2d localA, Vec2d localB):
   pyObjA = <object>objectMap[objA]
   pyObjB = <object>objectMap[objB]
   
   return pyObjA.collide(pyObjB, convertFromVec(normal), convertFromVec(localA), convertFromVec(localB))

ctypedef bool (*handler)(objects.Object*, objects.Object*, Vec2d, Vec2d, Vec2d)

cdef class ColliderList(CustomList):
   cdef unordered_map[pyPointer, colliderPointer] colliderMap
   cdef obj

   def __init__(self, obj):
      super().__init__()
      self.obj = obj

   def _add(self, obj):
      cdef colliderPointer collider = (<BaseCollider>obj).generate((<Object>self.obj).thisptr)
      cdef pair[pyPointer, colliderPointer] pair
      pair.first = <PyObject*>obj
      pair.second = collider
      self.colliderMap.insert(pair)
      (<Object>self.obj).thisptr.updateBounds()
   
   def _remove(self, col):
      cdef colliderPointer collider = self.colliderMap[<PyObject*>col]
      self.colliderMap.erase(<PyObject*>col)
      cdef objPointer obj = (<Object>self.obj).thisptr
      obj.colliders.erase(remove(obj.colliders.begin(), obj.colliders.end(), collider), obj.colliders.end())
      del collider
   
   def _clear(self):
      for obj in self._list:
         del self.colliderMap[<PyObject*>obj]
      self.colliderMap.clear()
      (<Object>self.obj).thisptr.colliders.clear()
   
   def __getstate__(self):
      state = {'obj': self.obj}
      state.update(super().__getstate__())
      return state
   
   def __setstate__(self, state):
      self.obj = state['obj']
      del state['obj']
      super().__setstate__(state)
      

cdef class ConstraintList(CustomList):
   cdef obj
   cdef unordered_map[pyPointer, constraintPointer] constraintMap

   def __init__(self, obj):
      super().__init__()
      self.obj = obj

   def _add(self, constraint):
      other, pyConstraintDef = constraint
      cdef constraintPointer cConstraint = (<BaseConstraint>pyConstraintDef).generate((<Object>self.obj).thisptr, (<Object>other).thisptr)
      

      cdef pair[pyPointer, constraintPointer] pair
      pair.first = <PyObject*>constraint
      pair.second = cConstraint
      self.constraintMap.insert(pair)
   
   def _remove(self, constraint):
      constraint = self._list[self._list.index(constraint)] # Get true version
      cdef constraintPointer cConstraint = self.constraintMap[<PyObject*>constraint]
      self.constraintMap.erase(<PyObject*>constraint)

      del cConstraint
   
   def __getstate__(self):
      state = {'obj': self.obj}
      state.update(super().__getstate__())
      return state

   def __setstate__(self, state):
      self.obj = state['obj']
      del state['obj']
      super().__setstate__(state)

cdef class Object:
   cdef objects.Object *thisptr
   cdef colliders
   cdef constraints

   def __cinit__(self, *args, **kwargs):
      self.thisptr = new objects.Object(-1,-1,-1,-1,NULL)
      cdef pair[objPointer,pyPointer] pair
      pair.first = self.thisptr
      pair.second = <PyObject*>self
      objectMap.insert(pair)

   def __init__(self, double mass, double moment, double restitution, double friction):
      cdef handler colHandler
      if hasattr(self, 'collide'):
         colHandler = collisionHandler
      else:
         colHandler = NULL
      
      #self.thisptr = new objects.Object(mass, moment, restitution, friction, colHandler)
      self.setMass(mass)
      self.setMoment(moment)
      self.restitution = restitution
      self.friction = friction
      self.thisptr.collisionHandler = colHandler

      self.colliders = ColliderList(self)
      self.constraints = ConstraintList(self)

   def __dealloc__(self):
      objectMap.erase(self.thisptr)
      del self.thisptr

   def __getstate__(self):
      state = {'colliders': self.colliders, 'constraints': self.constraints,
               'mass': self.mass, 'moment': self.moment, 'restitution': self.restitution, 'friction': self.friction,
               'pos': self.pos, 'vel': self.vel, 'rot': self.rot, 'rotV': self.rotV}
      if hasattr(self, '__dict__'):
         state.update(self.__dict__)
      return state
   
   def __setstate__(self, state):
      self.pos = state['pos']
      self.vel = state['vel']
      self.rot = state['rot']
      self.rotV = state['rotV']

      colliders = state['colliders']
      constraints = state['constraints']
      mass = state['mass']
      moment = state['moment']
      restitution = state['restitution']
      friction = state['friction']

      for key in ('colliders', 'pos', 'vel', 'rot', 'rotV', 'mass', 'moment','restitution', 'friction'):
         del state[key]
      
      if hasattr(self, '__dict__'):
         self.__dict__.update(state)
      
      Object.__init__(self, mass, moment, restitution, friction)

      self.colliders = colliders
      self.constraints = constraints

   @property
   def colliders(self):
      return self.colliders
   @property
   def constraints(self):
      return self.constraints

   @property
   def restitution(self):
      return self.thisptr.restitution
   @restitution.setter
   def restitution(self, val):
      self.thisptr.restitution = val

   @property
   def friction(self):
      return self.thisptr.friction
   @friction.setter
   def friction(self, val):
      self.thisptr.friction = val

   def setMass(self, double mass):
      self.thisptr.setMass(mass)
   @property
   def mass(self):
      return self.thisptr.getMass()
   @property
   def invMass(self):
      return self.thisptr.getInvMass()

   def setMoment(self, double moment):
      self.thisptr.setMoment(moment)
   @property
   def moment(self):
      return self.thisptr.getMoment()
   @property
   def invMoment(self):
      return self.thisptr.getInvMoment()

   @property
   def pos(self):
      cdef Vec2d pos = self.thisptr.pos
      return pos.x, pos.y
   @pos.setter
   def pos(self, pos):
      self.thisptr.pos = convertToVec(pos)
      self.thisptr.updateBounds()
   
   @property
   def vel(self):
      cdef Vec2d vel = self.thisptr.vel
      return vel.x, vel.y
   @vel.setter
   def vel(self,vel):
      self.thisptr.vel = convertToVec(vel)
   
   @property
   def rot(self):
      return self.thisptr.rot
   @rot.setter
   def rot(self, rot):
      self.thisptr.rot = rot
      self.thisptr.updateRotMat()
      self.thisptr.updateBounds()
   
   @property
   def rotV(self):
      return self.thisptr.rotV
   @rotV.setter
   def rotV(self,rotV):
      self.thisptr.rotV = rotV
   
   @property
   def bounds(self):
      cdef pair[Vec2d, Vec2d] bounds = self.thisptr.getBounds()
      return convertFromVec(bounds.first), convertFromVec(bounds.second)

   def localToGlobal(self, point):
      return convertFromVec(self.thisptr.localToGlobal(convertToVec(point)))
   
   def globalToLocal(self, point):
      return convertFromVec(self.thisptr.globalToLocal(convertToVec(point)))

   def localToGlobalVec(self, vec):
      return convertFromVec(self.thisptr.localToGlobalVec(convertToVec(vec)))
   
   def globalToLocalVec(self, vec):
      return convertFromVec(self.thisptr.globalToLocalVec(convertToVec(vec)))

class ContactPoint:
   def __init__(self, *args):
      self.localA,self.localB,self.globalA,self.globalB,self.normal,self.penetration,self.nImpulseSum,self.tImpulseSum = args

class ContactConstraint:
   def __init__(self, objA, objB, points, restitution, friction):
      self.objA = objA
      self.objB = objB
      self.points = []
      for point in points:
         self.points.append(ContactPoint(*point))
      self.restitution = restitution
      self.friction = friction


cdef class Node:
   cdef aabb.Node *ptr
   cdef cPhysics.World *world

   @property
   def children(self):
      return createNode(self.world, self.ptr.children[0]), createNode(self.world, self.ptr.children[1])

   @property
   def bounds(self):
      return convertFromVec(self.ptr.outer.lower), convertFromVec(self.ptr.outer.upper)

cdef class LeafNode:
   cdef aabb.Node *ptr
   cdef obj

   @property
   def obj(self):
      return self.obj

   @property
   def inner_bounds(self):
      return convertFromVec(self.ptr.inner.lower), convertFromVec(self.ptr.inner.upper)
   
   @property
   def bounds(self):
      return convertFromVec(self.ptr.outer.lower), convertFromVec(self.ptr.outer.upper)

cdef createNode(cPhysics.World *world, aabb.Node *cNode):
   if cNode.isLeaf():
      leaf = LeafNode()
      leaf.ptr = cNode
      leaf.obj = <object>objectMap[world.nodeMap[cNode]]
      return leaf
   else:
      node = Node()
      node.ptr = cNode
      node.world = world
      return node

cdef class AABBTree:
   cdef cPhysics.World *world
   def __init__(self, world):
      self.world = (<PyWorld>world)._world

   @property
   def root(self):
      if self.world.tree.root == NULL:
         return None
      else:
         return createNode(self.world, self.world.tree.root)


cdef class PyWorld(CustomList):
   cdef cPhysics.World *_world
   cdef AABBTree

   def __cinit__(self, *args, **kwargs):
      self._world = new cPhysics.World(Vec2d(0,0), -1, -1, -1, -1, 5)
      self.AABBTree = AABBTree(self)

   def __init__(self, gravity=(0,0.3), baumgarteBias=0.05, solverSteps=4, slopP=0.1, slopR=0.05):
      self.gravity = gravity
      self.baumgarteBias = baumgarteBias
      self.solverSteps = solverSteps
      self.slopP = slopP
      self.slopR = slopR

   def _add(self, obj):
      self._world.add_object((<Object>obj).thisptr)
   def _remove(self, obj):
      self._world.removeObject((<Object>obj).thisptr)
   def _clear(self):
      self._world.clear()

   def update(self, stepSize):
      self._world.update(stepSize)
   
   def __deepcopy__(self, memo):
      res = type(self).__new__(type(self))

      memo[id(self)] = res
      state = copy.deepcopy(self.__getstate__(), memo)
      res.__setstate__(state)
      return res

   def __getstate__(self):
      state = {
         'gravity': self.gravity, 
         'baumgarteBias': self.baumgarteBias, 
         'solverSteps': self.solverSteps, 
         'slopP': self.slopP, 
         'slopR': self.slopR, 
         #'AABBTree': self.AABBTree,
         #'contacts': self.contacts,
      }
      state.update(super().__getstate__())
      return state
   
   def __setstate__(self, state):
      self.gravity = state['gravity']
      self.baumgarteBias = state['baumgarteBias']
      self.solverSteps = state['solverSteps']
      self.slopP = state['slopP']
      self.slopR = state['slopR']
      #self.AABBTree = state['AABBTree']
      
      #contacts = state['contacts']

      for key in ('gravity', 'baumgarteBias', 'solverSteps', 'slopP', 'slopR'):
         del state[key]
      super().__setstate__(state)

      #self._setContacts(contacts)

   '''def _setContacts(self, contacts):
      self._world.contactConstraints.clear()
      cdef objects.ContactConstraint cContact
      cdef objects.ContactPoint cPoint
      for contact in contacts:
         cContact = objects.ContactConstraint((<Object>contact.objA).thisptr, (<Object>contact.objB).thisptr, contact.friction, contact.restitution)
         for point in contact.points:
            cPoint.localA  = convertToVec(point.localA)
            cPoint.localB  = convertToVec(point.localB)
            cPoint.globalA = convertToVec(point.globalA)
            cPoint.globalB = convertToVec(point.globalB)
            cPoint.normal  = convertToVec(point.normal)
            cPoint.penetration = point.penetration
            cPoint.nImpulseSum = point.nImpulseSum
            cPoint.tImpulseSum = point.tImpulseSum
            cContact.points.push_back(cPoint)
         self._world.contactConstraints.push_back(cContact)'''

   @property
   def baumgarteBias(self):
      return self._world.baumgarteBias
   @baumgarteBias.setter
   def baumgarteBias(self, val):
      self._world.baumgarteBias = val

   @property
   def solverSteps(self):
      return self._world.solverSteps
   @solverSteps.setter
   def solverSteps(self, val):
      self._world.solverSteps = val

   @property
   def gravity(self):
      return self._world.gravity.x, self._world.gravity.y
   @gravity.setter
   def gravity(self, val):
      self._world.gravity.x = val[0]
      self._world.gravity.y = val[1]

   @property
   def slopP(self):
      return self._world.slopP
   @slopP.setter
   def slopP(self, val):
      self._world.slopP = val

   @property
   def slopR(self):
      return self._world.slopR
   @slopR.setter
   def slopR(self, val):
      self._world.slopR = val

   @property
   def contacts(self):
      cdef objects.ContactPoint cPoint
      pyContacts = []


      cdef vector[objects.ContactConstraint] cContacts = self._world.getContacts()
      for cContact in cContacts:
         points = []

         for cPoint in cContact.points:
            points.append((convertFromVec(cPoint.localA),convertFromVec(cPoint.localB),
                           convertFromVec(cPoint.globalA),convertFromVec(cPoint.globalB),
                           convertFromVec(cPoint.normal),cPoint.penetration,
                           cPoint.nImpulseSum, cPoint.tImpulseSum))

         objA = <object>objectMap[cContact.objA]
         objB = <object>objectMap[cContact.objB]

         pyContacts.append(ContactConstraint(objA, objB, points, cContact.restitution, cContact.friction))
      return pyContacts
   
   @property
   def AABBTree(self):
      return self.AABBTree

class Module(object):
   def __init__(self):
      self.World = PyWorld
      self.CircleCollider = CircleCollider
      self.PolyCollider = PolyCollider
      self.PivotConstraint = PivotConstraint
      self.FixedConstraint = FixedConstraint
      self.SliderConstraint = SliderConstraint
      self.CustomConstraint = CustomConstraint
      self.Object = Object

sys.modules[__name__] = Module()
