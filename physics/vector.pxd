
cdef extern from "vector.h":
   cdef cppclass Vec2d:
      double x
      double y
      
      Vec2d() except +
      Vec2d(double, double) except +