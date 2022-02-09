
cdef extern from "vector.h":
   ctypedef float float_type

   cdef cppclass Vec2:
      float_type x
      float_type y
      
      Vec2() except +
      Vec2(float_type, float_type) except +

   cdef cppclass Vec3:
      float_type x
      float_type y
      float_type z

      Vec3() except +
      Vec3(float_type, float_type, float_type) except +