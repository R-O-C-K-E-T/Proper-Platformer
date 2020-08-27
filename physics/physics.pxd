# distutils: language = c++

from libcpp.vector cimport vector
from libcpp.unordered_map cimport unordered_map
cimport objects, util, aabb
from vector cimport Vec2d


ctypedef objects.Object* objectP

cdef extern from "physics.h":
   extern vector[Vec2d] collisions
   cdef cppclass World:
      unordered_map[aabb.nodeP, objectP] nodeMap
      aabb.AABBTree tree

      Vec2d gravity
      int solverSteps
      double baumgarteBias
      double slopP
      double slopR

      World(Vec2d, double, int, double, double, double)
      void update(double)

      void clear()
      void add_object(objects.Object* obj)
      void removeObject(objects.Object* obj)

      vector[objects.ContactConstraint] getContacts()
