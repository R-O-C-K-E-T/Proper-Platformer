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

cdef Vec2d convert_to_vec(obj):
   return Vec2d(obj[0],obj[1])
cdef convert_from_vec(Vec2d vec):
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
      cdef vector[Vec2d] points_vec
      for point in self.points:
         points_vec.push_back(convert_to_vec(point))
      
      return new objects.PolyCollider(obj, points_vec)

cdef class BaseConstraint:
   cdef objects.BaseConstraint* generate(self, objects.Object *obj_a, objects.Object *obj_b):
      raise NotImplemented


cdef void apply(PyObject *self, objects.Object* obj_a, objects.Object* obj_b):
   py_obj_a = <object>object_map[obj_a]
   py_obj_b = <object>object_map[obj_b]
   (<object>self).apply(py_obj_a, py_obj_b)

cdef class CustomConstraint(BaseConstraint):
   cdef objects.BaseConstraint* generate(self, objects.Object *obj_a, objects.Object *obj_b):
      return new objects.CustomConstraint[PyObject*](obj_a, obj_b, <PyObject*>self, apply)

   def apply(self, obj_a, obj_b):
      raise NotImplemented


cdef class PivotConstraint(BaseConstraint):
   cdef local_a
   cdef local_b

   @property
   def local_a(self):
      return self.local_a
   @property
   def local_b(self):
      return self.local_b

   def __init__(self, local_a, local_b):
      self.local_a = local_a
      self.local_b = local_b

   cdef objects.BaseConstraint* generate(self, objects.Object *obj_a, objects.Object *obj_b):
      return new objects.PivotConstraint(obj_a, obj_b, convert_to_vec(self.local_a), convert_to_vec(self.local_b))

cdef class FixedConstraint:
   cdef local_a
   cdef local_b

   def __init__(self, local_a, local_b):
      self.local_a = local_a
      self.local_b = local_b

   @property
   def local_a(self):
      return self.local_a
   @property
   def local_b(self):
      return self.local_b

   cdef objects.BaseConstraint* generate(self, objects.Object *obj_a, objects.Object *obj_b):
      return new objects.FixedConstraint(obj_a, obj_b, convert_to_vec(self.local_a), convert_to_vec(self.local_b))
   
cdef class SliderConstraint:
   cdef local_a
   cdef local_b
   cdef normal

   @property
   def local_a(self):
      return self.local_a
   @property
   def local_b(self):
      return self.local_b
   @property
   def normal(self):
      return self.normal

   def __init__(self, local_a, local_b, normal):
      self.local_a = local_a
      self.local_b = local_b
      self.normal = normal

   cdef objects.BaseConstraint* generate(self, objects.Object *obj_a, objects.Object *obj_b):
      return new objects.SliderConstraint(obj_a, obj_b, convert_to_vec(self.local_a), convert_to_vec(self.local_b), convert_to_vec(self.normal))

ctypedef PyObject* py_pointer
ctypedef objects.Object* obj_pointer
ctypedef objects.BaseCollider* collider_pointer
ctypedef objects.BaseConstraint* constraint_pointer

cdef unordered_map[obj_pointer, py_pointer] object_map
cdef bool global_collision_handler(objects.Object* obj_a, objects.Object* obj_b, Vec2d normal, Vec2d local_a, Vec2d local_b):
   py_obj_a = <object>object_map[obj_a]
   py_obj_b = <object>object_map[obj_b]
   
   return py_obj_a.collide(py_obj_b, convert_from_vec(normal), convert_from_vec(local_a), convert_from_vec(local_b))

ctypedef bool (*handler)(objects.Object*, objects.Object*, Vec2d, Vec2d, Vec2d)

cdef class ColliderList(CustomList):
   cdef unordered_map[py_pointer, collider_pointer] collider_map
   cdef obj

   def __init__(self, obj):
      super().__init__()
      self.obj = obj

   def _add(self, obj):
      cdef collider_pointer collider = (<BaseCollider>obj).generate((<Object>self.obj).thisptr)
      cdef pair[py_pointer, collider_pointer] pair
      pair.first = <PyObject*>obj
      pair.second = collider
      self.collider_map.insert(pair)
      (<Object>self.obj).thisptr.updateBounds()
   
   def _remove(self, col):
      cdef collider_pointer collider = self.collider_map[<PyObject*>col]
      self.collider_map.erase(<PyObject*>col)
      cdef obj_pointer obj = (<Object>self.obj).thisptr
      obj.colliders.erase(remove(obj.colliders.begin(), obj.colliders.end(), collider), obj.colliders.end())
      del collider
   
   def _clear(self):
      for obj in self._list:
         del self.collider_map[<PyObject*>obj]
      self.collider_map.clear()
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
   cdef unordered_map[py_pointer, constraint_pointer] constraint_map

   def __init__(self, obj):
      super().__init__()
      self.obj = obj

   def _add(self, constraint):
      other, py_constraint_def = constraint
      cdef constraint_pointer c_constraint = (<BaseConstraint>py_constraint_def).generate((<Object>self.obj).thisptr, (<Object>other).thisptr)
      

      cdef pair[py_pointer, constraint_pointer] pair
      pair.first = <PyObject*>constraint
      pair.second = c_constraint
      self.constraint_map.insert(pair)
   
   def _remove(self, constraint):
      constraint = self._list[self._list.index(constraint)] # Get true version
      cdef constraint_pointer c_constraint = self.constraint_map[<PyObject*>constraint]
      self.constraint_map.erase(<PyObject*>constraint)

      del c_constraint
   
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
      cdef pair[obj_pointer,py_pointer] pair
      pair.first = self.thisptr
      pair.second = <PyObject*>self
      object_map.insert(pair)

   def __init__(self, double mass, double moment, double restitution, double friction):
      cdef handler collision_handler
      if hasattr(self, 'collide'):
         collision_handler = global_collision_handler
      else:
         collision_handler = NULL
      
      #self.thisptr = new objects.Object(mass, moment, restitution, friction, collision_handler)
      self.set_mass(mass)
      self.set_moment(moment)
      self.restitution = restitution
      self.friction = friction
      self.thisptr.collisionHandler = collision_handler

      self.colliders = ColliderList(self)
      self.constraints = ConstraintList(self)

   def __dealloc__(self):
      object_map.erase(self.thisptr)
      del self.thisptr

   def __getstate__(self):
      state = {'colliders': self.colliders, 'constraints': self.constraints,
               'mass': self.mass, 'moment': self.moment, 'restitution': self.restitution, 'friction': self.friction,
               'pos': self.pos, 'vel': self.vel, 'rot': self.rot, 'rot_vel': self.rot_vel}
      if hasattr(self, '__dict__'):
         state.update(self.__dict__)
      return state
   
   def __setstate__(self, state):
      self.pos = state['pos']
      self.vel = state['vel']
      self.rot = state['rot']
      self.rot_vel = state['rot_vel']

      colliders = state['colliders']
      constraints = state['constraints']
      mass = state['mass']
      moment = state['moment']
      restitution = state['restitution']
      friction = state['friction']

      for key in ('colliders', 'pos', 'vel', 'rot', 'rot_vel', 'mass', 'moment','restitution', 'friction'):
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

   def set_mass(self, double mass):
      self.thisptr.setMass(mass)
   @property
   def mass(self):
      return self.thisptr.getMass()
   @property
   def inv_mass(self):
      return self.thisptr.getInvMass()

   def set_moment(self, double moment):
      self.thisptr.setMoment(moment)
   @property
   def moment(self):
      return self.thisptr.getMoment()
   @property
   def inv_moment(self):
      return self.thisptr.getInvMoment()

   @property
   def pos(self):
      cdef Vec2d pos = self.thisptr.pos
      return pos.x, pos.y
   @pos.setter
   def pos(self, pos):
      self.thisptr.pos = convert_to_vec(pos)
      self.thisptr.updateBounds()
   
   @property
   def vel(self):
      cdef Vec2d vel = self.thisptr.vel
      return vel.x, vel.y
   @vel.setter
   def vel(self,vel):
      self.thisptr.vel = convert_to_vec(vel)
   
   @property
   def rot(self):
      return self.thisptr.rot
   @rot.setter
   def rot(self, rot):
      self.thisptr.rot = rot
      self.thisptr.updateRotMat()
      self.thisptr.updateBounds()
   
   @property
   def rot_vel(self):
      return self.thisptr.rotV
   @rot_vel.setter
   def rot_vel(self,rot_vel):
      self.thisptr.rotV = rot_vel
   
   @property
   def bounds(self):
      cdef pair[Vec2d, Vec2d] bounds = self.thisptr.getBounds()
      return convert_from_vec(bounds.first), convert_from_vec(bounds.second)

   def local_to_global(self, point):
      return convert_from_vec(self.thisptr.localToGlobal(convert_to_vec(point)))
   
   def global_to_local(self, point):
      return convert_from_vec(self.thisptr.globalToLocal(convert_to_vec(point)))

   def local_to_global_vec(self, vec):
      return convert_from_vec(self.thisptr.localToGlobalVec(convert_to_vec(vec)))
   
   def global_to_local_vec(self, vec):
      return convert_from_vec(self.thisptr.globalToLocalVec(convert_to_vec(vec)))

class ContactPoint:
   def __init__(self, *args):
      self.local_a,self.local_b,self.global_a,self.global_b,self.normal,self.penetration,self.normal_impulse_sum,self.tangent_impulse_sum = args

class ContactConstraint:
   def __init__(self, obj_a, obj_b, points, restitution, friction):
      self.obj_a = obj_a
      self.obj_b = obj_b
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
      return create_node(self.world, self.ptr.children[0]), create_node(self.world, self.ptr.children[1])

   @property
   def bounds(self):
      return convert_from_vec(self.ptr.outer.lower), convert_from_vec(self.ptr.outer.upper)

cdef class LeafNode:
   cdef aabb.Node *ptr
   cdef obj

   @property
   def obj(self):
      return self.obj

   @property
   def inner_bounds(self):
      return convert_from_vec(self.ptr.inner.lower), convert_from_vec(self.ptr.inner.upper)
   
   @property
   def bounds(self):
      return convert_from_vec(self.ptr.outer.lower), convert_from_vec(self.ptr.outer.upper)

cdef create_node(cPhysics.World *world, aabb.Node *c_node):
   if c_node.isLeaf():
      leaf = LeafNode()
      leaf.ptr = c_node
      leaf.obj = <object>object_map[world.nodeMap[c_node]]
      return leaf
   else:
      node = Node()
      node.ptr = c_node
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
         return create_node(self.world, self.world.tree.root)


cdef class PyWorld(CustomList):
   cdef cPhysics.World *_world
   cdef AABBTree

   def __cinit__(self, *args, **kwargs):
      self._world = new cPhysics.World(Vec2d(0,0), -1, -1, -1, -1, 5)
      self.AABBTree = AABBTree(self)

   def __init__(self, gravity=(0,0.3), baumgarte_bias=0.05, solver_steps=4, slop_p=0.1, slop_r=0.05):
      self.gravity = gravity
      self.baumgarte_bias = baumgarte_bias
      self.solver_steps = solver_steps
      self.slop_p = slop_p
      self.slop_r = slop_r

   def _add(self, obj):
      self._world.addObject((<Object>obj).thisptr)
   def _remove(self, obj):
      self._world.removeObject((<Object>obj).thisptr)
   def _clear(self):
      self._world.clear()

   def update(self, step_size):
      self._world.update(step_size)
   
   def __deepcopy__(self, memo):
      res = type(self).__new__(type(self))

      memo[id(self)] = res
      state = copy.deepcopy(self.__getstate__(), memo)
      res.__setstate__(state)
      return res

   def __getstate__(self):
      state = {
         'gravity': self.gravity, 
         'baumgarte_bias': self.baumgarte_bias, 
         'solver_steps': self.solver_steps, 
         'slop_p': self.slop_p, 
         'slop_r': self.slop_r, 
         #'AABBTree': self.AABBTree,
         #'contacts': self.contacts,
      }
      state.update(super().__getstate__())
      return state
   
   def __setstate__(self, state):
      self.gravity = state['gravity']
      self.baumgarte_bias = state['baumgarte_bias']
      self.solver_steps = state['solver_steps']
      self.slop_p = state['slop_p']
      self.slop_r = state['slop_r']
      
      #contacts = state['contacts']

      for key in ('gravity', 'baumgarte_bias', 'solver_steps', 'slop_p', 'slop_r'):
         del state[key]
      super().__setstate__(state)

      #self._set_contacts(contacts)

   '''def _set_contacts(self, contacts):
      self._world.contactConstraints.clear()
      cdef objects.ContactConstraint c_contact
      cdef objects.ContactPoint c_point
      for contact in contacts:
         c_contact = objects.ContactConstraint((<Object>contact.obj_a).thisptr, (<Object>contact.obj_b).thisptr, contact.friction, contact.restitution)
         for point in contact.points:
            c_point.localA  = convert_to_vec(point.local_a)
            c_point.localB  = convert_to_vec(point.local_b)
            c_point.globalA = convert_to_vec(point.global_a)
            c_point.globalB = convert_to_vec(point.global_b)
            c_point.normal  = convert_to_vec(point.normal)
            c_point.penetration = point.penetration
            c_point.nImpulseSum = point.normal_impulse_sum
            c_point.tImpulseSum = point.tangent_impulse_sum
            c_contact.points.push_back(c_point)
         self._world.contactConstraints.push_back(c_contact)'''

   @property
   def baumgarte_bias(self):
      return self._world.baumgarteBias
   @baumgarte_bias.setter
   def baumgarte_bias(self, val):
      self._world.baumgarteBias = val

   @property
   def solver_steps(self):
      return self._world.solverSteps
   @solver_steps.setter
   def solver_steps(self, val):
      self._world.solverSteps = val

   @property
   def gravity(self):
      return self._world.gravity.x, self._world.gravity.y
   @gravity.setter
   def gravity(self, val):
      self._world.gravity.x = val[0]
      self._world.gravity.y = val[1]

   @property
   def slop_p(self):
      return self._world.slopP
   @slop_p.setter
   def slop_p(self, val):
      self._world.slopP = val

   @property
   def slop_r(self):
      return self._world.slopR
   @slop_r.setter
   def slop_r(self, val):
      self._world.slopR = val

   @property
   def contacts(self):
      cdef objects.ContactPoint c_point
      py_contacts = []


      cdef vector[objects.ContactConstraint] c_contacts = self._world.getContacts()
      for c_contact in c_contacts:
         points = []

         for c_point in c_contact.points:
            points.append((convert_from_vec(c_point.localA),convert_from_vec(c_point.localB),
                           convert_from_vec(c_point.globalA),convert_from_vec(c_point.globalB),
                           convert_from_vec(c_point.normal),c_point.penetration,
                           c_point.nImpulseSum, c_point.tImpulseSum))

         obj_a = <object>object_map[c_contact.objA]
         obj_b = <object>object_map[c_contact.objB]

         py_contacts.append(ContactConstraint(obj_a, obj_b, points, c_contact.restitution, c_contact.friction))
      return py_contacts
   
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
