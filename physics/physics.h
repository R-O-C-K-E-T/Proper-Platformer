#pragma once

#include <unordered_map>
#include <vector>

#include "aabb.h"
#include "objects.h"
#include "vector.h"
#include "sph.h"

//#define DEBUG

#ifdef DEBUG
extern std::vector<Vec2> collisions;
#endif


template <typename T, typename U> 
struct std::hash<std::pair<T, U>> {
    std::size_t operator()(const std::pair<T, U> &key) const {
      return std::hash<T>()(key.first) ^ std::hash<U>()(key.second);
   }
};



class World {
   private:
      std::vector<Object *> objects;

      std::vector<std::pair<Object *, Object *>> broadphase();
      void resolveCollision(Object *a, Object *b, const Collision &col);

      std::unordered_map<std::pair<Object *, Object *>, ContactConstraint>
         contactConstraints = std::unordered_map<std::pair<Object *, Object *>,
                                                   ContactConstraint>();

      SPHSolver sph = SPHSolver(0.08);

   public:
      AABBTree tree;

      Vec2 gravity;
      float_type baumgarteBias;
      int solverSteps;
      float_type slopP, slopR;

      World(Vec2 gravity, float_type baumgarteBias, int solverSteps, float_type slopP,
            float_type slopR, float_type aabbMargin)
         : tree(aabbMargin),
            gravity(gravity),
            baumgarteBias(baumgarteBias),
            solverSteps(solverSteps),
            slopP(slopP),
            slopR(slopR) {};

      void update(float_type stepSize);

      const std::vector<Object*> getObjects() { return objects; };
      void clear();
      void addObject(Object *obj);
      void removeObject(Object *obj);

      void addFluidParticle(const Vec2& pos, const Vec2& vel, const Vec3& col, float_type mass) { sph.addFluidParticle(pos, vel, col, mass); }
      void addRigidParticle(const Vec2& localPos, Object* object) { sph.addRigidParticle(localPos, *object); }

      std::vector<Particle>& getFluidParticles() { return sph.getParticles(); }
      std::vector<RigidParticle>& getRigidParticles() { return sph.getRigidParticles(); }

      float_type getSPHScaleFactor() { return sph.getScaleFactor(); }

      std::vector<ContactConstraint> getContacts() const;
};