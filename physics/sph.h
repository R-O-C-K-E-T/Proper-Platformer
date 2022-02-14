#pragma once

#include <vector>
#include <functional>

#ifndef M_PI
#define M_PI 3.141592653589
#endif

#include "vector.h"
#include "objects.h"

#define BLOCK_SIZE 256

uint16_t mapToZCurve(uint8_t x, uint8_t y);

// Moser–de Bruijn sequence
const uint16_t lookup[] = {0, 1, 4, 5, 16, 17, 20, 21, 64, 65, 68, 69, 80, 81, 84, 85, 256, 257, 260, 261, 272, 273, 276, 277, 320, 321, 324, 325, 336, 337, 340, 341, 1024, 1025, 1028, 1029, 1040, 1041, 1044, 1045, 1088, 1089, 1092, 1093, 1104, 1105, 1108, 1109, 1280, 1281, 1284, 1285, 1296, 1297, 1300, 1301, 1344, 1345, 1348, 1349, 1360, 1361, 1364, 1365, 4096, 4097, 4100, 4101, 4112, 4113, 4116, 4117, 4160, 4161, 4164, 4165, 4176, 4177, 4180, 4181, 4352, 4353, 4356, 4357, 4368, 4369, 4372, 4373, 4416, 4417, 4420, 4421, 4432, 4433, 4436, 4437, 5120, 5121, 5124, 5125, 5136, 5137, 5140, 5141, 5184, 5185, 5188, 5189, 5200, 5201, 5204, 5205, 5376, 5377, 5380, 5381, 5392, 5393, 5396, 5397, 5440, 5441, 5444, 5445, 5456, 5457, 5460, 5461, 16384, 16385, 16388, 16389, 16400, 16401, 16404, 16405, 16448, 16449, 16452, 16453, 16464, 16465, 16468, 16469, 16640, 16641, 16644, 16645, 16656, 16657, 16660, 16661, 16704, 16705, 16708, 16709, 16720, 16721, 16724, 16725, 17408, 17409, 17412, 17413, 17424, 17425, 17428, 17429, 17472, 17473, 17476, 17477, 17488, 17489, 17492, 17493, 17664, 17665, 17668, 17669, 17680, 17681, 17684, 17685, 17728, 17729, 17732, 17733, 17744, 17745, 17748, 17749, 20480, 20481, 20484, 20485, 20496, 20497, 20500, 20501, 20544, 20545, 20548, 20549, 20560, 20561, 20564, 20565, 20736, 20737, 20740, 20741, 20752, 20753, 20756, 20757, 20800, 20801, 20804, 20805, 20816, 20817, 20820, 20821, 21504, 21505, 21508, 21509, 21520, 21521, 21524, 21525, 21568, 21569, 21572, 21573, 21584, 21585, 21588, 21589, 21760, 21761, 21764, 21765, 21776, 21777, 21780, 21781, 21824, 21825, 21828, 21829, 21840, 21841, 21844, 21845};

const float_type coefficient = 40.0 / (7.0*M_PI);

float_type constexpr kernel(const float_type dist) {
    if (dist < 0.5) {
        return coefficient * (6*dist*dist*(dist - 1) + 1);
    } else if (dist < 1) {
        float_type inverse = 1 - dist;
        return coefficient * 2*inverse*inverse*inverse;
    } else {
        return 0;
    }
}


class SPHSolver;

template<class T>
class NeighbourhoodSolver;

class BaseParticle {
    friend SPHSolver;
    template<class T>
    friend class NeighbourhoodSolver;

    public:
        Vec2 pos;
        Vec2 vel;  
        float_type volume; 
    
    protected:
        BaseParticle(const Vec2& pos, const Vec2& vel) : pos(pos), vel(vel) {}

    private:
        float_type alpha;
        union {
            struct {
                float_type volumeDerivative;
                float_type outward;
            };
            Vec2 normal;
        };
        

        std::vector<BaseParticle*> neighbours;
};

class Particle : public BaseParticle {
    public:
        Vec3 col;
        float_type invMass;

        Particle(const Vec2& pos, const Vec2& vel, const Vec3& col, const float_type invMass) : BaseParticle(pos, vel), col(col), invMass(invMass) {}
};

class RigidParticle : public BaseParticle {
    public:
        RigidParticle(const Vec2& localPosition, Object& object) : 
            BaseParticle(ORIGIN, ORIGIN),
            localPosition(localPosition), 
            object(object) {}

        Vec2 localPosition;
        Object& object;
};

template<class T>
class NeighbourhoodSolver {
    template<class U>
    friend class NeighbourhoodSolver;

    private:
        std::vector<T> particles;

        struct handlePair {
            uint16_t cell;  
            uint32_t particle;
        };
        std::vector<handlePair> handles;

        uint32_t block[BLOCK_SIZE * BLOCK_SIZE];

    public:
        NeighbourhoodSolver() {
            static_assert(std::is_base_of<BaseParticle, T>::value, "Type T must derive from \"BaseParticle\"");
        }

        void addParticle(T particle);
        void update();
        //void reorder();

        template<class U>
        void crossNeighbours(NeighbourhoodSolver<U>&);

        std::vector<T>& getParticles() { return particles; }
};

class SPHSolver {
    private:
        NeighbourhoodSolver<Particle> fluid;
        NeighbourhoodSolver<RigidParticle> rigid;

        float_type scaleFactor;
        float_type invScaleFactor;
        float_type scaleFactor2;
        float_type massConversionFactor;
        float_type invMassConversionFactor;

        float_type targetNeighbourhoodVolume = 3.0;

        void fixParticles();
        void correctDivergence();
        void applyNonPressureForces(float_type timeStep);
        void correctDensity(float_type timeStep);

        void updateVolumeDerivative();

        void updateRigidParticleVelocities();

        void applySeparationImpulse(RigidParticle& rigid, Particle& fluid, float_type separationFactor);
        void applySeparationImpulse(Particle& fluidA, Particle& fluidB, float_type separationFactor);
        
    public:
        float_type viscosity = 0.001;
        float_type surfaceTension = 0.001;

        explicit SPHSolver(float_type scaleFactor) : scaleFactor(scaleFactor), invScaleFactor(1.0 / scaleFactor) {
            scaleFactor2 = scaleFactor*scaleFactor;
            massConversionFactor = (invScaleFactor * invScaleFactor) * targetNeighbourhoodVolume;
            invMassConversionFactor = 1.0 / massConversionFactor;
        }

        void update(float_type totalStep);
        void singleStep(float_type timeStep);
        
        void addFluidParticle(const Vec2& pos, const Vec2& vel, const Vec3& col, float_type mass) { fluid.addParticle(Particle(pos * scaleFactor, vel * scaleFactor, col, 1.0/mass)); }
        void addRigidParticle(const Vec2& localPos, Object& object) { rigid.addParticle(RigidParticle(localPos, object)); }

        std::vector<Particle>& getParticles() { return fluid.getParticles(); }
        std::vector<RigidParticle>& getRigidParticles() { return rigid.getParticles(); }

        float_type getScaleFactor() { return scaleFactor; }
};