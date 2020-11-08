# distutils: language = c++

from vector cimport Vec2, float_type

from libcpp.vector cimport vector
from libcpp cimport bool

cimport objects

cdef extern from "util.h":
   bool checkWinding(vector[Vec2])
   bool checkWinding(Vec2, Vec2, Vec2)

   float_type originLineDistance(Vec2, Vec2)
   float_type lineDistance(Vec2, Vec2, Vec2)