from libcpp.vector cimport vector
cimport objects
from vector cimport Vec2, Vec3, float_type

cdef extern from "sph.h":
    cdef cppclass BaseParticle:
        Vec2 pos
        Vec2 vel
        float_type volume

    cdef cppclass RigidParticle(BaseParticle):
        RigidParticle(Vec2, objects.Object)
        
        Vec2 localPosition
        objects.Object object

    cdef cppclass Particle(BaseParticle):
        Vec3 col
        float_type invMass

    cdef cppclass SPHSolver:
        float_type viscosity
        float_type surfaceTension

        SPHSolver(float_type)

        void update(float_type)
        void singleStep(float_type)

        void addFluidParticle(Vec2, Vec2, Vec3, float_type)
        void addRigidParticle(Vec2, objects.Object)

        vector[Particle] getFluidParticles()
        vector[RigidParticle] getRigidParticles()

        float_type getScaleFactor()