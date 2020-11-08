from distutils.core import setup
from distutils.extension import Extension
from Cython.Build import cythonize

setup(name='Physics Engine', ext_modules=cythonize(
    [
        Extension("physics", 
            ["main.pyx", "physics.cpp", "objects.cpp", "aabb.cpp"])
        ], 
        language="c++", 
        gdb_debug=True)
    )