# distutils: language = c++

from vector cimport Vec2d

from libcpp.vector cimport vector
from libcpp cimport bool

cimport objects

cdef extern from "util.h":
   bool checkWinding(vector[Vec2d])
   bool checkWinding(Vec2d, Vec2d, Vec2d)

   double originLineDistance(Vec2d, Vec2d)
   double lineDistance(Vec2d, Vec2d, Vec2d)