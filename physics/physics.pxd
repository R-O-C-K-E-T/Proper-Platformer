# distutils: language = c++

from libcpp.vector cimport vector
cimport objects, util, aabb, sph
from vector cimport Vec2, Vec3, float_type


ctypedef objects.Object* objectP

cdef extern from "physics.h":
   extern vector[Vec2] collisions
   cdef cppclass World:
      aabb.AABBTree tree

      Vec2 gravity
      int solverSteps
      float_type baumgarteBias
      float_type slopP
      float_type slopR

      World(Vec2, float_type, int, float_type, float_type, float_type)
      void update(float_type)

      void clear()
      void addObject(objects.Object* obj)
      void removeObject(objects.Object* obj)

      void addFluidParticle(Vec2, Vec2, Vec3, float_type)
      void addRigidParticle(Vec2, objects.Object*)

      vector[sph.Particle] getFluidParticles()
      vector[sph.RigidParticle] getRigidParticles()

      float_type getSPHScaleFactor()

      vector[objects.ContactConstraint] getContacts()
