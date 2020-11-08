#pragma once

#include <iostream>
#include <vector>

#include "vector.h"
#include "aabb.h"

class BaseCollider;
class BaseConstraint;

class Object final : public Node {
    private:
        float_type mass;
        float_type moment;

        float_type invMass;
        float_type invMoment;

    public:
        float_type restitution;
        float_type friction;

        std::vector<BaseConstraint *> constraints;
        std::vector<BaseCollider *> colliders;

        float_type rot, rotV;
        Vec2 pos, vel;
        mat2x2 rotMat;

        bool (*collisionHandler)(Object *, Object *, Vec2, Vec2, Vec2);

        Object(float_type mass, float_type moment, float_type restitution, float_type friction,
            bool (*collisionHandler)(Object *, Object *, Vec2, Vec2, Vec2));
        virtual ~Object();

        void update(const float_type stepSize);
        void updateConstraints(const float_type baumgarteBias, const float_type slopP,
                            const float_type slopR);

        void setMass(const float_type mass);
        float_type getMass() const { return mass; }
        float_type getInvMass() const { return invMass; }

        void setMoment(const float_type moment);
        float_type getMoment() const { return moment; }
        float_type getInvMoment() const { return invMoment; }

        Vec2 localToGlobal(const Vec2& point) const {
            return rotMat.apply(point) + pos;
        }
        Vec2 globalToLocal(const Vec2& point) const {
            return rotMat.applyT(point - pos);
        }

        Vec2 localToGlobalVec(const Vec2& vec) const {
            return rotMat.apply(vec);
        }
        Vec2 globalToLocalVec(const Vec2& vec) const {
            return rotMat.applyT(vec);
        }

        AABB getBounds() const { return inner; };
        void updateBounds();
        void updateRotMat();
    
    protected:
        virtual void updateAABB(const float_type margin) override;
};

class BaseCollider {
    public:
        BaseCollider(Object *obj) : obj(obj) {
            obj->colliders.push_back(this);
            obj->updateBounds();
        }
        virtual ~BaseCollider() {};

        virtual std::pair<Vec2, Vec2> bounds() {
            return std::pair<Vec2, Vec2>(Vec2(0, 0), Vec2(0, 0));
        }

        virtual Vec2 support(const Vec2 &direction) const { return ORIGIN; };
        virtual Vec2 globalSupport(const Vec2 &direction) const { 
            return localToGlobal(support(globalToLocalVec(direction))); 
        }

        Vec2 localToGlobal(const Vec2& point) const {
            return obj->localToGlobal(point);
        }
        Vec2 globalToLocal(const Vec2& point) const {
            return obj->globalToLocal(point);
        }

        Vec2 localToGlobalVec(const Vec2& vec) const {
            return obj->localToGlobalVec(vec);
        }
        Vec2 globalToLocalVec(const Vec2& vec) const {
            return obj->globalToLocalVec(vec);
        }


    protected:
        Object *obj;
};

class CircleCollider : public BaseCollider {
    private:
        float_type radius;

    public:
        CircleCollider(Object *obj, float_type radius)
            : BaseCollider(obj), radius(radius) {}

        std::pair<Vec2, Vec2> bounds();
        Vec2 support(const Vec2& direction) const override;
        Vec2 globalSupport(const Vec2& direction) const override;
};

class PolyCollider : public BaseCollider {
    private:
        std::vector<Vec2> points;  // Winding must be pre checked
    public:
        PolyCollider(Object *obj, std::vector<Vec2> points)
            : BaseCollider(obj), points(points) {
            /*centre = ORIGIN;
            for (const Vec2 point : points) centre = centre + point;
            centre = centre / points.size();*/
        }

        std::pair<Vec2, Vec2> bounds();
        Vec2 support(const Vec2 &direction) const;
};

class BaseConstraint {
    friend Object;

    protected:
        Vec6 M;

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
        virtual void apply(const float_type baumgarteBias, const float_type slopP,
                        const float_type slopR) {}
        void updateMassMatrix();
};

struct Collision {
    float_type penetration;
    Vec2 normal;

    Vec2 localA, localB;
};

struct ContactPoint {
    Vec2 localA, localB, globalA, globalB, normal;
    Vec6 J, JM, JT, JTM;
    float_type bias, tangentBias, effectiveMass, effectiveTangentMass, penetration;
    float_type nImpulseSum = 0;
    float_type tImpulseSum = 0;
};

class ContactConstraint {
    public:
        Object *objA, *objB;
        float_type friction, restitution;  // TODO better solution
        std::vector<ContactPoint> points;

        ContactConstraint()
            : objA(nullptr), objB(nullptr), friction(0), restitution(0) {}
        ContactConstraint(Object *objA, Object *objB, float_type friction,
                        float_type restitution)
            : objA(objA),
            objB(objB),
            friction(friction),
            restitution(restitution) {}

        ~ContactConstraint();

        void apply();
        void updatePoints(const float_type baumgarteBias, const float_type slopP, const float_type slopR, const Vec2& tickGravity);
        void addPoint(Collision col);
        size_t numPoints() { return points.size(); }
};

class PivotConstraint : public BaseConstraint {
    private:
        const Vec2 localA, localB;

    public:
        PivotConstraint(Object *objA, Object *objB, Vec2 localA, Vec2 localB)
            : BaseConstraint(objA, objB), localA(localA), localB(localB) {}

        void apply(const float_type baumgarteBias, const float_type slopP,
                const float_type slopR);
};

class FixedConstraint : public BaseConstraint {
    private:
        const Vec2 localA, localB;

    public:
        FixedConstraint(Object *objA, Object *objB, Vec2 localA, Vec2 localB)
            : BaseConstraint(objA, objB), localA(localA), localB(localB){};

        void apply(const float_type baumgarteBias, const float_type slopP,
                const float_type slopR);
};

class SliderConstraint : public BaseConstraint {
    private:
        const Vec2 localA, localB, localN;  // normal in A local space
    public:
        SliderConstraint(Object *objA, Object *objB, Vec2 localA, Vec2 localB,
                        Vec2 localN)
            : BaseConstraint(objA, objB),
            localA(localA),
            localB(localB),
            localN(localN){};

        void apply(const float_type baumgarteBias, const float_type slopP,
                const float_type slopR);
};

template <typename T>
class CustomConstraint : public BaseConstraint {
    private:
        void (*callback)(T value, Object *objA, Object *objB);
        T value;

    public:
        CustomConstraint(Object *objA, Object *objB, T value,
                        void (*callback)(T value, Object *objA, Object *objB))
            : BaseConstraint(objA, objB), callback(callback), value(value){};

        void apply(const float_type baumgarteBias, const float_type slopP,
                const float_type slopR) {
            callback(value, objA, objB);
        }
};