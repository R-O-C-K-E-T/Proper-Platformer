from libcpp.vector cimport vector
from libcpp.utility cimport pair
from libcpp cimport bool
from vector cimport Vec2d

ctypedef Node* nodeP

cdef extern from "aabb.h":
   cdef struct AABB:
      Vec2d upper
      Vec2d lower

      #AABB()
      AABB(Vec2d, Vec2d)

      AABB mkUnion(const AABB other)
      AABB expand(double radius)
      double area()
      bool contains(const AABB other)
      bool intersect(const AABB other)

   cdef struct Node:
      Node* parent
      Node* children[2]
      AABB inner
      AABB outer
      bool visited

      Node()

      void updateAABB(double)

      bool isLeaf()
      Node* getSibling()
   
   cdef cppclass AABBTree:
      Node *root
      const double margin

      AABBTree(double)

      vector[pair[nodeP,nodeP]] computePairs()
      void update()
