#include "objects.h"

#include <algorithm>
#include <cmath>

#include "util.h"

const float_type persistenceThresh = 0.05;

Object::Object(float_type mass, float_type moment, float_type restitution, float_type friction,
               bool (*collisionHandler)(Object*, Object*, Vec2, Vec2, Vec2)) {
    this->restitution = restitution;
    this->friction = friction;

    this->collisionHandler = collisionHandler;

    setMass(mass);
    setMoment(moment);

    rot = 0;
    rotV = 0;

    pos = Vec2(0, 0);
    vel = Vec2(0, 0);

    rotMat.a = 1;
    rotMat.b = 0;
    rotMat.c = 0;
    rotMat.d = 1;

    inner.lower = ORIGIN;
    inner.upper = ORIGIN;

    updateBounds();
}

Object::~Object() {
    for (BaseCollider* collider : colliders) {
        delete collider;
    }

    std::vector<BaseConstraint*> copy;
    copy = constraints;
    for (BaseConstraint* constraint : copy) {
        delete constraint;
    }
}

void Object::update(float_type stepSize) {  // Needs good velocity before executing
    if (vel != ORIGIN || rotV != 0) {
        pos = pos + vel * stepSize;
        rot += rotV * stepSize;

        updateRotMat();

        updateBounds();
    }
}

void Object::updateConstraints(const float_type baumgarteBias, const float_type slopP,
                               const float_type slopR) {
    for (BaseConstraint* constraint : constraints) {
        if (this == constraint->objB) continue;
        constraint->apply(baumgarteBias, slopP, slopR);
    }
}

void Object::updateBounds() {
    Vec2 min(std::numeric_limits<float_type>::infinity(),
              std::numeric_limits<float_type>::infinity());
    Vec2 max(-std::numeric_limits<float_type>::infinity(),
              -std::numeric_limits<float_type>::infinity());

    for (uint i = 0; i < colliders.size(); i++) {
        std::pair<Vec2, Vec2> colliderBounds = colliders[i]->bounds();
        min.x = std::min(min.x, colliderBounds.first.x);
        min.y = std::min(min.y, colliderBounds.first.y);

        max.x = std::max(max.x, colliderBounds.second.x);
        max.y = std::max(max.y, colliderBounds.second.y);
    }

    inner.lower = min;
    inner.upper = max;
}

void Object::updateAABB(const float_type margin) {
    // We must be leaf
    outer = inner.expand(margin);

    const float_type factor = 2;

    if (vel.x > 0) {
        outer.upper.x += vel.x*factor; 
    } else {
        outer.lower.x += vel.x*factor;
    }
    if (vel.y > 0) {
        outer.upper.y += vel.y*factor; 
    } else {
        outer.lower.y += vel.y*factor;
    }
}

void Object::updateRotMat() { rotMat = genRotationMat(rot); }

void Object::setMass(float_type m) {
    if (m < 0) {
        mass = -1;
        invMass = 0;
    } else {
        mass = m;
        invMass = 1 / m;
    }
    for (BaseConstraint* constraint : constraints) {
        constraint->updateMassMatrix();
    }
}

void Object::setMoment(float_type m) {
    if (m < 0) {
        moment = -1;
        invMoment = 0;
    } else {
        moment = m;
        invMoment = 1 / m;
    }
    for (BaseConstraint* constraint : constraints) {
        constraint->updateMassMatrix();
    }
}

Vec2 CircleCollider::support(const Vec2& dir) const {
    return dir * (radius / dir.length());
}

Vec2 CircleCollider::globalSupport(const Vec2& dir) const {
    return obj->pos + dir * (radius / dir.length());
}

std::pair<Vec2, Vec2> CircleCollider::bounds() {
    const Vec2 size(radius, radius);
    return std::pair<Vec2, Vec2>{obj->pos - size, obj->pos + size};
}

Vec2 PolyCollider::support(const Vec2& dir) const {
    Vec2 point = points[0];
    float_type maxDot = point.dot(dir);
    for (uint i = 1; i < points.size(); i++) {
        float_type curDot = points[i].dot(dir);
        if (curDot > maxDot) {
            point = points[i];
            maxDot = curDot;
        }
    }
    return point;
}

std::pair<Vec2, Vec2> PolyCollider::bounds() {
    Vec2 point = obj->rotMat.apply(points[0]);
    float_type minX = point.x;
    float_type minY = point.y;

    float_type maxX = point.x;
    float_type maxY = point.y;

    for (uint i = 1; i < points.size(); i++) {
        Vec2 point = obj->rotMat.apply(points[i]);
        if (point.x < minX) {
            minX = point.x;
        } else if (point.x > maxX) {
            maxX = point.x;
        }

        if (point.y < minY) {
            minY = point.y;
        } else if (point.y > maxY) {
            maxY = point.y;
        }
    }

    return std::pair<Vec2, Vec2>{Vec2(minX, minY) + obj->pos,
                                   Vec2(maxX, maxY) + obj->pos};
}

BaseConstraint::~BaseConstraint() {
    objA->constraints.erase(
        std::remove(objA->constraints.begin(), objA->constraints.end(), this),
        objA->constraints.end());
    objB->constraints.erase(
        std::remove(objB->constraints.begin(), objB->constraints.end(), this),
        objB->constraints.end());
}

void BaseConstraint::updateMassMatrix() { M = getMassMatrix(objA, objB); }

ContactConstraint::~ContactConstraint() {}

void ContactConstraint::apply() {
    Vec6 V = getVelocityVector(objA, objB);

    if (points.size() == 1) {
        ContactPoint& point = points[0];

        float_type lambda = -(point.J.dot(V) + point.bias) / point.effectiveMass;

        if (point.nImpulseSum + lambda < 0) {
            lambda = -point.nImpulseSum;
            point.nImpulseSum = 0;
        } else {
            point.nImpulseSum += lambda;
        }

        if (std::isnan(lambda)) return;

        addVelocity(objA, objB, point.JM * lambda);
    } else if (points.size() == 2) {
        ContactPoint& pointA = points[0];
        ContactPoint& pointB = points[1];

        mat2x2 mat;
        mat.a = pointA.effectiveMass;
        mat.b = mat.c = pointB.J.dot(pointA.JM);
        mat.d = pointB.effectiveMass;

        Vec2 lambda = mat.solve(-(pointA.J.dot(V) + pointA.bias), -(pointB.J.dot(V) + pointB.bias));

        if (std::isnan(lambda.x) || std::isnan(lambda.y)) return;

        bool sepA = lambda.x + pointA.nImpulseSum < 0;
        bool sepB = lambda.y + pointB.nImpulseSum < 0;

        if (sepA && !sepB) {  // A separating, B holding
            addVelocity(objA, objB, pointA.JM * -pointA.nImpulseSum);
            pointA.nImpulseSum = 0;

            V = getVelocityVector(objA, objB);

            float_type lambda = -(pointB.J.dot(V) + pointB.bias) / pointB.effectiveMass;

            if (pointB.nImpulseSum + lambda < 0) {
                lambda = -pointB.nImpulseSum;
                pointB.nImpulseSum = 0;
            } else {
                pointB.nImpulseSum += lambda;
            }

            addVelocity(objA, objB, pointB.JM * lambda);
        } else if (sepB && !sepA) {  // B separating, A holding
            addVelocity(objA, objB, pointB.JM * -pointB.nImpulseSum);
            pointB.nImpulseSum = 0;

            V = getVelocityVector(objA, objB);

            float_type lambda = -(pointA.J.dot(V) + pointA.bias) / pointA.effectiveMass;

            if (pointA.nImpulseSum + lambda < 0) {
                lambda = -pointA.nImpulseSum;
                pointA.nImpulseSum = 0;
            } else {
                pointA.nImpulseSum += lambda;
            }

            addVelocity(objA, objB, pointA.JM * lambda);
        } else {
            if (sepA && sepB) {  // Both separating
                lambda.x = -pointA.nImpulseSum;
                lambda.y = -pointB.nImpulseSum;
                pointA.nImpulseSum = 0;
                pointB.nImpulseSum = 0;
            } else {  // Both holding
                pointA.nImpulseSum += lambda.x;
                pointB.nImpulseSum += lambda.y;
            }
            addVelocity(objA, objB, pointA.JM * lambda.x + pointB.JM * lambda.y);
        }
    }

    for (ContactPoint& point : points) {  // Friction
        V = getVelocityVector(objA, objB);

        float_type lambda = -(point.JT.dot(V) + point.tangentBias) / point.effectiveTangentMass;


        if (points.size() == 2) lambda *= 0.5;

        float_type newTImpulseSum =
            std::min(
                std::max(point.tImpulseSum + lambda, -point.nImpulseSum * friction),
                point.nImpulseSum * friction
            );

        lambda = newTImpulseSum - point.tImpulseSum;
        point.tImpulseSum = newTImpulseSum;

        addVelocity(objA, objB, point.JTM * lambda);
    }
}

void ContactConstraint::updatePoints(const float_type baumgarteBias, const float_type slopP, const float_type slopR, const Vec2& tickGravity) {
    for (auto it = points.begin(); it != points.end();) {
        ContactPoint& point = *it;

        Vec2 globalA = this->objA->localToGlobal(point.localA);
        Vec2 globalB = this->objB->localToGlobal(point.localB);
        
        point.penetration = (globalA - globalB).dot(point.normal);

        if (
            point.penetration < 0 ||
            (globalA - point.globalA).length2() > 0.1 ||
            (globalB - point.globalB).length2() > 0.1 ||
            std::abs((globalA - globalB).cross(point.normal)) > 0.05   
        ) {
            it = points.erase(it);
            continue;
        }

        point.globalA = globalA;
        point.globalB = globalB;

        it++;
    }

    if (points.size() > 2) {
        ContactPoint pA = points[0];
        for (uint i = 1; i < points.size(); i++) {  // Trim contacts
            ContactPoint current = points[i];
            if (current.penetration > pA.penetration) {
                pA = current;
            }
        }

        ContactPoint pB = points[0];
        float_type dist = (pB.globalA - pA.globalA).length2();
        for (uint i = 1; i < points.size(); i++) {
            ContactPoint current = points[i];
            float_type curDist = (current.globalA - pA.globalA).length2();
            if (curDist > dist) {
                pB = current;
                dist = curDist;
            }
        }

        points.clear();
        points.push_back(pA);
        points.push_back(pB);
    }

    const Vec6 M = getMassMatrix(objA, objB);
    const float_type factor = 1.0;
    for (ContactPoint& point : points) {
        Vec2 offsetA = objA->localToGlobalVec(point.localA);
        Vec2 offsetB = objB->localToGlobalVec(point.localB);

        point.J = Vec6(-point.normal.x, -point.normal.y, point.normal.cross(offsetA), point.normal.x, point.normal.y, -point.normal.cross(offsetB));
        point.JM = point.J.componentMultiply(M);
        point.effectiveMass = point.JM.dot(point.J);

        /*std::cout << objA->pos << "," << objB->pos << "," << point.effectiveMass << std::endl;
        */
        if (std::isnan(point.effectiveMass)) {
            exit(1);
        }

        Vec2 tangent(-point.normal.y, point.normal.x);
        point.JT = Vec6(-tangent.x, -tangent.y, tangent.cross(offsetA), tangent.x,
                 tangent.y, -tangent.cross(offsetB));
        point.JTM = point.JT.componentMultiply(M);
        point.effectiveTangentMass = point.JTM.dot(point.JT);

        Vec2 velA = objA->vel + Vec2(-offsetA.y, offsetA.x) * objA->rotV;
        if (objA->getInvMass() != 0) velA -= tickGravity;

        Vec2 velB = objB->vel + Vec2(-offsetB.y, offsetB.x) * objB->rotV;
        if (objB->getInvMass() != 0) velB -= tickGravity;

        float_type prevBias = point.bias;
        
        float_type closingVelocity = (velB - velA).dot(point.normal);

        /*if (objA->getInvMass() != 0 && objB->getInvMass() == 0) {
            closingVelocity -= (tickGravity - ORIGIN).dot(point.normal);
        } else if (objA->getInvMass() == 0 && objB->getInvMass() != 0) {
            closingVelocity -= (ORIGIN - tickGravity).dot(point.normal);
        }*/

        point.bias = -baumgarteBias * std::max(point.penetration - slopP, -slopP*(float_type)0.5) + 
                    std::min(closingVelocity + slopR, (float_type)0.0) * restitution;

        point.tangentBias = 0.0;// -1000 * (point.globalB - point.globalA).dot(tangent);

        //point.nImpulseSum = 0.0;
        point.nImpulseSum *= factor;
        //point.nImpulseSum = std::max((point.nImpulseSum * factor) + (prevBias - point.bias) / point.effectiveMass, 0.0);
        point.tImpulseSum = 0;
    }
}

void ContactConstraint::addPoint(Collision col) {
    Vec2 globalA = objA->localToGlobal(col.localA);
    Vec2 globalB = objB->localToGlobal(col.localB);

    
    for (ContactPoint point : points) {
        if ((point.globalA - globalA).length2() < persistenceThresh ||
            (point.globalB - globalB).length2() < persistenceThresh) {
            
            point.localA = col.localA;
            point.localB = col.localB;
            point.globalA = globalA;
            point.globalB = globalB;
            point.normal = col.normal;
            point.penetration = col.penetration;
            
            return;
        };
    }

    ContactPoint point;
    point.localA = col.localA;
    point.localB = col.localB;
    point.globalA = globalA;
    point.globalB = globalB;
    point.normal = col.normal;
    point.penetration = col.penetration;

    //Vec2 offsetA = objA->localToGlobalVec(point.localA);
    //Vec2 offsetB = objB->localToGlobalVec(point.localB);
    //point.jacobian = Vec6(-point.normal.x, -point.normal.y, point.normal.cross(offsetA), point.normal.x, point.normal.y, -point.normal.cross(offsetB));

    points.push_back(point);
}

void PivotConstraint::apply(const float_type baumgarteBias, const float_type slopP,
                            const float_type slopR) {
    Vec2 rA = objA->localToGlobalVec(localA);
    Vec2 rB = objB->localToGlobalVec(localB);

    Vec6 V = getVelocityVector(objA, objB);

    Vec2 d = objB->pos + rB - objA->pos - rA;

    Vec6 J1(-1,  0,  rA.y, 1, 0, -rB.y);
    Vec6 J2( 0, -1, -rA.x, 0, 1,  rB.x);

    Vec6 J1M = J1.componentMultiply(M);
    Vec6 J2M = J2.componentMultiply(M);
    mat2x2 mat{J1.dot(J1M), J1.dot(J2M), J2.dot(J1M), J2.dot(J2M)};
    Vec2 l = mat.invert().apply(-J1.dot(V) - baumgarteBias * d.x,
                                 -J2.dot(V) - baumgarteBias * d.y);


    addVelocity(objA, objB, J1M * l.x + J2M * l.y);
}

void FixedConstraint::apply(const float_type baumgarteBias, const float_type slopP,
                            const float_type slopR) {
    Vec2 rA = objA->localToGlobalVec(localA);
    Vec2 rB = objB->localToGlobalVec(localB);

    Vec6 V = getVelocityVector(objA, objB);

    Vec2 d = objB->pos + rB - objA->pos - rA;

    Vec6 J1(-1,  0,  rA.y, 1, 0, -rB.y);
    Vec6 J2( 0, -1, -rA.x, 0, 1,  rB.x);
    Vec6 J3( 0,  0,    -1, 0, 0,     1);

    Vec6 J1M = J1.componentMultiply(M);
    Vec6 J2M = J2.componentMultiply(M);
    Vec6 J3M = J3.componentMultiply(M);

    mat3x3 mat{J1.dot(J1M), J1.dot(J2M), J1.dot(J3M), 
               J2.dot(J1M), J2.dot(J2M), J2.dot(J3M), 
               J3.dot(J1M), J3.dot(J2M), J3.dot(J3M)
            };

    Vec3 l = mat.invert().apply(
        -J1.dot(V) - baumgarteBias * d.x, -J2.dot(V) - baumgarteBias * d.y,
        -J3.dot(V) - 2 * baumgarteBias * (objB->rot - objA->rot));

    addVelocity(objA, objB, J1M * l.x + J2M * l.y + J3M * l.z);
}

void SliderConstraint::apply(const float_type baumgarteBias, const float_type slopP,
                             const float_type slopR) {
    Vec2 rA = objA->localToGlobalVec(localA);
    Vec2 rB = objB->localToGlobalVec(localB);
    Vec2 normal = objA->localToGlobalVec(localN);

    Vec6 V = getVelocityVector(objA, objB);

    Vec2 d = objB->pos + rB - objA->pos - rA;

    Vec6 J1(-normal.x, -normal.y, -(rA + d).cross(normal), normal.x, normal.y, rB.cross(normal));
    Vec6 J2(0, 0, -1, 0, 0, 1);

    Vec6 J1M = J1.componentMultiply(M);
    Vec6 J2M = J2.componentMultiply(M);

    mat2x2 mat{J1.dot(J1M), J1.dot(J2M), J2.dot(J1M), J2.dot(J2M)};

    Vec2 l = mat.invert().apply(
        -J1.dot(V) - baumgarteBias * d.dot(normal),
        -J2.dot(V) - 2 * baumgarteBias * (objB->rot - objA->rot));

    addVelocity(objA, objB, J1M * l.x + J2M * l.y);
}
