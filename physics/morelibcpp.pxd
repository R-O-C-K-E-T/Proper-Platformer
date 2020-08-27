cdef extern from "<algorithm>" namespace "std" nogil:
   ForwardIt remove[ForwardIt, T](ForwardIt first, ForwardIt last, const T& value )