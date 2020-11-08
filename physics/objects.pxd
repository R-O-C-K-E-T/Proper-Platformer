# distutils: language = c++

from vector cimport Vec2, float_type
from aabb cimport AABB, Node

from libcpp.vector cimport vector
from libcpp.utility cimport pair
from libcpp cimport bool

ctypedef bool (*handler)(Object*, Object*, Vec2, Vec2, Vec2)

cdef extern from "objects.h":
   cdef cppclass BaseConstraint:
      Object *objA
      Object *objB
      apply(float_type, float_type, float_type)
   
   cdef cppclass SliderConstraint(BaseConstraint):
      SliderConstraint(Object*, Object*, Vec2, Vec2, Vec2)

   cdef cppclass PivotConstraint(BaseConstraint):
      PivotConstraint(Object*, Object*, Vec2, Vec2)

   cdef cppclass FixedConstraint(BaseConstraint):
      FixedConstraint(Object*, Object*, Vec2, Vec2)

   cdef struct ContactPoint:
      Vec2 localA
      Vec2 localB
      Vec2 globalA
      Vec2 globalB
      Vec2 normal

      float_type penetration
      float_type nImpulseSum
      float_type tImpulseSum

   cdef cppclass ContactConstraint:
      Object *objA
      Object *objB
      const float_type friction
      const float_type restitution
      vector[ContactPoint] points

      ContactConstraint()
      ContactConstraint(Object*, Object*, float_type, float_type)

      apply(float_type, float_type, float_type)

   cdef cppclass CustomConstraint[T](BaseConstraint):
      ctypedef void (*callback)(T, Object*, Object*)
      CustomConstraint(Object*, Object*, T, callback)

   cdef cppclass BaseCollider:
      pair[Vec2,Vec2] bounds()

      Vec2 support(Vec2)

   cdef cppclass CircleCollider(BaseCollider):
      CircleCollider(Object*, float_type)
   
   cdef cppclass PolyCollider(BaseCollider):
      PolyCollider(Object*, vector[Vec2])

   cdef cppclass Object(Node):
      float_type friction
      float_type restitution

      vector[BaseCollider*] colliders
      vector[BaseConstraint*] constraints

      float_type rot
      float_type rotV
      Vec2 pos
      Vec2 vel
      handler collisionHandler
      
      Object(float_type, float_type, float_type, float_type, handler)

      void setMass(float_type)
      float_type getInvMass()
      float_type getMass()

      void setMoment(float_type)
      float_type getInvMoment()
      float_type getMoment()

      Vec2 globalToLocal(Vec2)
      Vec2 localToGlobal(Vec2)

      Vec2 globalToLocalVec(Vec2)
      Vec2 localToGlobalVec(Vec2)

      AABB getBounds()

      void updateRotMat()
      void updateBounds()