#ifndef __PHYSICS_H_INCLUDED__
#define __PHYSICS_H_INCLUDED__

#include <unordered_map>
#include <vector>

#include "aabb.h"
#include "objects.h"
#include "vector.h"

//#define DEBUG

#ifdef DEBUG
extern std::vector<Vec2d> collisions;
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

    // std::vector<ContactConstraint> contactConstraints; // TODO make better
    // solution
    std::unordered_map<std::pair<Object *, Object *>, ContactConstraint>
        contactConstraints = std::unordered_map<std::pair<Object *, Object *>,
                                                ContactConstraint>();

   public:
    std::unordered_map<Node *, Object *> nodeMap;
    AABBTree tree;

    Vec2d gravity;
    double baumgarteBias;
    int solverSteps;
    double slopP, slopR;

    World(Vec2d gravity, double baumgarteBias, int solverSteps, double slopP,
          double slopR, double aabbMargin)
        : tree(AABBTree(aabbMargin)),
          gravity(gravity),
          baumgarteBias(baumgarteBias),
          solverSteps(solverSteps),
          slopP(slopP),
          slopR(slopR){};

    void update(double stepSize);

    const std::vector<Object *> getObjects() { return objects; };
    void clear();
    void add_object(Object *obj);
    void removeObject(Object *obj);

    std::vector<ContactConstraint> getContacts() const;
};

#endif