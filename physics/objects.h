#ifndef __OBJECTS_H_INCLUDED__
#define __OBJECTS_H_INCLUDED__

#include <iostream>
#include <vector>

#include "vector.h"

class BaseCollider;
class BaseConstraint;

class Object {
    double mass;
    double moment;

    double invMass;
    double invMoment;

   public:
    double restitution;
    double friction;

    std::vector<BaseConstraint *> constraints;
    std::vector<BaseCollider *> colliders;

    double rot, rotV;
    Vec2d pos, vel;
    mat2x2 rotMat;

    bool (*collisionHandler)(Object *, Object *, Vec2d, Vec2d, Vec2d);

    Object(double mass, double moment, double restitution, double friction,
           bool (*collisionHandler)(Object *, Object *, Vec2d, Vec2d, Vec2d));
    ~Object();
    void update(const double stepSize);
    void updateConstraints(const double baumgarteBias, const double slopP,
                           const double slopR);

    void setMass(const double mass);
    double getInvMass() const;
    double getMass() const;

    void setMoment(const double moment);
    double getInvMoment() const;
    double getMoment() const;

    Vec2d globalToLocal(const Vec2d &point) const;
    Vec2d localToGlobal(const Vec2d &point) const;

    Vec2d globalToLocalVec(const Vec2d &vec) const;
    Vec2d localToGlobalVec(const Vec2d &vec) const;

    std::pair<Vec2d, Vec2d> getBounds() const;
    void updateBounds();
    void updateRotMat();

   protected:
    std::pair<Vec2d, Vec2d> bounds;
};

class BaseCollider {
    /*protected:
     Vec2d centre;*/

   public:
    BaseCollider(Object *obj) : obj(obj) {
        obj->colliders.push_back(this);
        obj->updateBounds();
    }
    virtual ~BaseCollider(){};

    virtual std::pair<Vec2d, Vec2d> bounds() {
        return std::pair<Vec2d, Vec2d>(Vec2d(0, 0), Vec2d(0, 0));
    }

    virtual Vec2d support(const Vec2d &direction) const { return ORIGIN; };

    Vec2d globalToLocal(const Vec2d &point) const;
    Vec2d localToGlobal(const Vec2d &point) const;

    Vec2d globalToLocalVec(const Vec2d &vec) const;
    Vec2d localToGlobalVec(const Vec2d &vec) const;

    // Vec2d getCentre() const { return centre; }

   protected:
    Object *obj;
};

class CircleCollider : public BaseCollider {
    double radius;

   public:
    CircleCollider(Object *obj, double radius)
        : BaseCollider(obj), radius(radius) {
        // centre = ORIGIN;
    }

    std::pair<Vec2d, Vec2d> bounds();
    Vec2d support(const Vec2d &direction) const;
};

class PolyCollider : public BaseCollider {
    std::vector<Vec2d> points;  // Winding must be pre checked
   public:
    PolyCollider(Object *obj, std::vector<Vec2d> points)
        : BaseCollider(obj), points(points) {
        /*centre = ORIGIN;
        for (const Vec2d point : points) centre = centre + point;
        centre = centre / points.size();*/
    }

    std::pair<Vec2d, Vec2d> bounds();
    Vec2d support(const Vec2d &direction) const;
};

class BaseConstraint {
    friend Object;

   protected:
    Vec6d M;

    BaseConstraint(Object *objA, Object *objB, bool allowCollision = false)
        : objA(objA), objB(objB), allowCollision(allowCollision) {
        objA->constraints.push_back(this);
        objB->constraints.push_back(this);
        updateMassMatrix();
    }

   public:
    Object *objA, *objB;
    const bool allowCollision;

    virtual ~BaseConstraint();
    virtual void apply(const double baumgarteBias, const double slopP,
                       const double slopR) {}
    void updateMassMatrix();
};

struct Collision {
    double penetration;
    Vec2d normal;

    Vec2d localA, localB;
};

struct ContactPoint {
    Vec2d localA, localB, globalA, globalB, normal;
    double penetration, closingVelocity;
    double nImpulseSum = 0;
    double tImpulseSum = 0;
    Vec6d jacobian;
};

class ContactConstraint {
   public:
    Object *objA, *objB;
    double friction, restitution;  // TODO better solution
    std::vector<ContactPoint> points;

    ContactConstraint()
        : objA(nullptr), objB(nullptr), friction(0), restitution(0) {}
    ContactConstraint(Object *objA, Object *objB, double friction,
                      double restitution)
        : objA(objA),
          objB(objB),
          friction(friction),
          restitution(restitution) {}

    void apply(const double baumgarteBias, const double slopP,
               const double slopR);
    void updatePoints();
    void addPoint(Collision col);
    uint numPoints();
};

class PivotConstraint : public BaseConstraint {
    const Vec2d localA, localB;

   public:
    PivotConstraint(Object *objA, Object *objB, Vec2d localA, Vec2d localB)
        : BaseConstraint(objA, objB), localA(localA), localB(localB) {}

    void apply(const double baumgarteBias, const double slopP,
               const double slopR);
};

class FixedConstraint : public BaseConstraint {
    const Vec2d localA, localB;

   public:
    FixedConstraint(Object *objA, Object *objB, Vec2d localA, Vec2d localB)
        : BaseConstraint(objA, objB), localA(localA), localB(localB){};

    void apply(const double baumgarteBias, const double slopP,
               const double slopR);
};

class SliderConstraint : public BaseConstraint {
    const Vec2d localA, localB, localN;  // normal in A local space
   public:
    SliderConstraint(Object *objA, Object *objB, Vec2d localA, Vec2d localB,
                     Vec2d localN)
        : BaseConstraint(objA, objB),
          localA(localA),
          localB(localB),
          localN(localN){};

    void apply(const double baumgarteBias, const double slopP,
               const double slopR);
};

template <typename T>
class CustomConstraint : public BaseConstraint {
    void (*callback)(T value, Object *objA, Object *objB);
    T value;

   public:
    CustomConstraint(Object *objA, Object *objB, T value,
                     void (*callback)(T value, Object *objA, Object *objB))
        : BaseConstraint(objA, objB), callback(callback), value(value){};

    void apply(const double baumgarteBias, const double slopP,
               const double slopR) {
        callback(value, objA, objB);
    }
};

#endif