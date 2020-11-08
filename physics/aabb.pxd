from libcpp.vector cimport vector
from libcpp.utility cimport pair
from libcpp cimport bool
from vector cimport Vec2, float_type

ctypedef Node* nodeP

cdef extern from "aabb.h":
   cdef struct AABB:
      Vec2 upper
      Vec2 lower

      #AABB()
      AABB(Vec2, Vec2)

      AABB mkUnion(const AABB other)
      AABB expand(float_type radius)
      float_type area()
      bool contains(const AABB other)
      bool intersect(const AABB other)

   cdef cppclass Node:
      Node()

      void updateAABB(float_type)

      AABB getInner()
      AABB getOuter()

      bool isLeaf()
      Node* getParent()
      Node** getChildren()
      Node* getSibling()
   
   cdef cppclass AABBTree:
      const float_type margin

      AABBTree(float_type)

      nodeP getRoot()

      vector[pair[nodeP,nodeP]] computePairs()
      void update()
