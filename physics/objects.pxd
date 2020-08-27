# distutils: language = c++

from vector cimport Vec2d

from libcpp.vector cimport vector
from libcpp.utility cimport pair
from libcpp cimport bool

ctypedef bool (*handler)(Object*, Object*, Vec2d, Vec2d, Vec2d)

cdef extern from "objects.h":
   cdef cppclass BaseConstraint:
      Object *objA
      Object *objB
      apply(double, double, double)
   
   cdef cppclass SliderConstraint(BaseConstraint):
      SliderConstraint(Object*, Object*, Vec2d, Vec2d, Vec2d)

   cdef cppclass PivotConstraint(BaseConstraint):
      PivotConstraint(Object*, Object*, Vec2d, Vec2d)

   cdef cppclass FixedConstraint(BaseConstraint):
      FixedConstraint(Object*, Object*, Vec2d, Vec2d)

   cdef struct ContactPoint:
      Vec2d localA
      Vec2d localB
      Vec2d globalA
      Vec2d globalB
      Vec2d normal

      double penetration
      double nImpulseSum
      double tImpulseSum

   cdef cppclass ContactConstraint:
      Object *objA
      Object *objB
      const double friction
      const double restitution
      vector[ContactPoint] points

      ContactConstraint()
      ContactConstraint(Object*, Object*, double, double)

      apply(double, double, double)

   cdef cppclass CustomConstraint[T](BaseConstraint):
      ctypedef void (*callback)(T, Object*, Object*)
      CustomConstraint(Object*, Object*, T, callback)

   cdef cppclass BaseCollider:
      pair[Vec2d,Vec2d] bounds()

      Vec2d support(Vec2d)

   cdef cppclass CircleCollider(BaseCollider):
      CircleCollider(Object*, double)
   
   cdef cppclass PolyCollider(BaseCollider):
      PolyCollider(Object*, vector[Vec2d])

   cdef cppclass Object:
      double friction
      double restitution

      vector[BaseCollider*] colliders
      vector[BaseConstraint*] constraints

      double rot
      double rotV
      Vec2d pos
      Vec2d vel
      handler collisionHandler
      
      Object(double, double, double, double, handler)

      void setMass(double)
      double getInvMass()
      double getMass()

      void setMoment(double)
      double getInvMoment()
      double getMoment()

      Vec2d globalToLocal(Vec2d)
      Vec2d localToGlobal(Vec2d)

      Vec2d globalToLocalVec(Vec2d)
      Vec2d localToGlobalVec(Vec2d)

      pair[Vec2d,Vec2d] getBounds()

      void updateRotMat()
      void updateBounds()