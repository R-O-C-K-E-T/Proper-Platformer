#include "objects.h"

#include <algorithm>
#include <cmath>

#include "util.h"

#define uint unsigned int

const double persistenceThresh = 0.01;

Object::Object(double mass, double moment, double restitution, double friction,
               bool (*collisionHandler)(Object*, Object*, Vec2d, Vec2d, Vec2d)) {
    this->colliders = colliders;

    this->restitution = restitution;
    this->friction = friction;

    this->collisionHandler = collisionHandler;

    setMass(mass);
    setMoment(moment);

    rot = 0;
    rotV = 0;

    pos = Vec2d(0, 0);
    vel = Vec2d(0, 0);

    rotMat.a = 1;
    rotMat.b = 0;
    rotMat.c = 0;
    rotMat.d = 1;

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

void Object::update(double stepSize) {  // Needs good velocity before executing
    if (vel.length2() != 0 || rotV != 0) {
        pos = pos + vel * stepSize;
        rot += rotV * stepSize;

        updateRotMat();

        updateBounds();
    }
}

void Object::updateConstraints(const double baumgarteBias, const double slopP,
                               const double slopR) {
    for (BaseConstraint* constraint : constraints) {
        if (this == constraint->objB) continue;
        constraint->apply(baumgarteBias, slopP, slopR);
    }
}

void Object::updateBounds() {
    Vec2d min(std::numeric_limits<double>::infinity(),
              std::numeric_limits<double>::infinity());
    Vec2d max(-std::numeric_limits<double>::infinity(),
              -std::numeric_limits<double>::infinity());

    for (uint i = 0; i < colliders.size(); i++) {
        std::pair<Vec2d, Vec2d> colliderBounds = colliders[i]->bounds();
        min.x = std::min(min.x, colliderBounds.first.x);
        min.y = std::min(min.y, colliderBounds.first.y);

        max.x = std::max(max.x, colliderBounds.second.x);
        max.y = std::max(max.y, colliderBounds.second.y);
    }

    bounds = std::make_pair(min, max);
}

void Object::updateRotMat() { rotMat = genRotationMat(rot); }

void Object::setMass(double m) {
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
double Object::getMass() const { return mass; }
double Object::getInvMass() const { return invMass; }

void Object::setMoment(double m) {
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
double Object::getMoment() const { return moment; }
double Object::getInvMoment() const { return invMoment; }

Vec2d Object::localToGlobal(const Vec2d& point) const {
    return rotMat.apply(point) + pos;
}
Vec2d Object::globalToLocal(const Vec2d& point) const {
    return rotMat.applyT(point - pos);
}

Vec2d Object::localToGlobalVec(const Vec2d& vec) const {
    return rotMat.apply(vec);
}
Vec2d Object::globalToLocalVec(const Vec2d& vec) const {
    return rotMat.applyT(vec);
}

std::pair<Vec2d, Vec2d> Object::getBounds() const { return bounds; }

Vec2d BaseCollider::localToGlobal(const Vec2d& point) const {
    return obj->localToGlobal(point);
}
Vec2d BaseCollider::globalToLocal(const Vec2d& point) const {
    return obj->globalToLocal(point);
}

Vec2d BaseCollider::localToGlobalVec(const Vec2d& vec) const {
    return obj->localToGlobalVec(vec);
}
Vec2d BaseCollider::globalToLocalVec(const Vec2d& vec) const {
    return obj->globalToLocalVec(vec);
}

Vec2d CircleCollider::support(const Vec2d& dir) const {
    return dir * (radius / dir.length());
}

std::pair<Vec2d, Vec2d> CircleCollider::bounds() {
    const Vec2d size(radius, radius);
    return std::pair<Vec2d, Vec2d>{obj->pos - size, obj->pos + size};
}

Vec2d PolyCollider::support(const Vec2d& dir) const {
    Vec2d point = points[0];
    double maxDot = point.dot(dir);
    for (uint i = 1; i < points.size(); i++) {
        double curDot = points[i].dot(dir);
        if (curDot > maxDot) {
            point = points[i];
            maxDot = curDot;
        }
    }
    return point;
}

std::pair<Vec2d, Vec2d> PolyCollider::bounds() {
    Vec2d point = obj->rotMat.apply(points[0]);
    double minX = point.x;
    double minY = point.y;

    double maxX = point.x;
    double maxY = point.y;

    for (uint i = 1; i < points.size(); i++) {
        Vec2d point = obj->rotMat.apply(points[i]);
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

    return std::pair<Vec2d, Vec2d>{Vec2d(minX, minY) + obj->pos,
                                   Vec2d(maxX, maxY) + obj->pos};
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

void ContactConstraint::apply(const double baumgarteBias, const double slopP,
                              const double slopR) {
    Vec6d V = getVelocityVector(objA, objB);
    const Vec6d M = getMassMatrix(objA, objB);
    //  std::vector<double> bias;
    //  for (ContactPoint p : points) {  // Get normal jacobians and biases
    //      bias.push_back(-baumgarteBias * std::max(p.penetration - slopP, 0.0)
    //      +
    //                     std::min(p.closingVelocity + slopR, 0.0) *
    //                     restitution);
    //      // bias.push_back(-baumgarteBias*std::max(p.penetration-slopP,0.0) -
    //      // std::max(p.closingVelocity-slopR,0.0) * restitution);
    //      // bias.push_back(-baumgarteBias*std::max(p.penetration-slopP,0.0) +
    //      );
    //  }   
    if (points.size() == 1) {
        ContactPoint& p = points[0];
        const Vec6d J = p.jacobian;
        double bias = -baumgarteBias * std::max(p.penetration - slopP, 0.0) +
                      std::min(p.closingVelocity + slopR, 0.0) * restitution;

        double lambda = -(V.dot(J) + bias) / ((J.componentMultiply(J)).dot(M));

        if (p.nImpulseSum + lambda < 0) {
            lambda = -p.nImpulseSum;
            p.nImpulseSum = 0;
        } else {
            p.nImpulseSum += lambda;
        }

        addVelocity(objA, objB, J.componentMultiply(M) * lambda);

        // std::cout << "a " << lambda << "\n";

    } else {
        ContactPoint& pA = points[0];
        ContactPoint& pB = points[1];
        const Vec6d J1 = pA.jacobian;
        const Vec6d J2 = pB.jacobian;

        double biasA = -baumgarteBias * std::max(pA.penetration - slopP, 0.0) +
                       std::min(pA.closingVelocity + slopR, 0.0) * restitution;
        double biasB = -baumgarteBias * std::max(pB.penetration - slopP, 0.0) +
                       std::min(pB.closingVelocity + slopR, 0.0) * restitution;

        Vec6d J1M = J1.componentMultiply(M);
        Vec6d J2M = J2.componentMultiply(M);

        mat2x2 mat{J1.dot(J1M), J1.dot(J2M), J2.dot(J1M), J2.dot(J2M)};

        Vec2d lambda = mat.solve(-J1.dot(V) - biasA, -J2.dot(V) - biasB);

        bool sepA = lambda.x + pA.nImpulseSum < 0;
        bool sepB = lambda.y + pB.nImpulseSum < 0;

        if (sepA && !sepB) {  // A separating, B holding
            addVelocity(objA, objB, J1M * -pA.nImpulseSum);

            V = getVelocityVector(objA, objB);

            double l = -(V.dot(J2) + biasB) / J2M.dot(J2);

            if (l + pB.nImpulseSum < 0) {
                l = -pB.nImpulseSum;
                pB.nImpulseSum = 0;
            } else {
                pB.nImpulseSum += l;
            }

            addVelocity(objA, objB, J2M * l);
            // std::cout << "d " << -pA.nImpulseSum << " " << l << "\n";
            pA.nImpulseSum = 0;
        } else if (sepB && !sepA) {  // B separating, A holding
            addVelocity(objA, objB, J2M * -pB.nImpulseSum);

            V = getVelocityVector(objA, objB);

            double l = -(V.dot(J1) + biasA) / J1M.dot(J1);

            if (l + pA.nImpulseSum < 0) {
                l = -pA.nImpulseSum;
                pA.nImpulseSum = 0;
            } else {
                pA.nImpulseSum += l;
            }

            addVelocity(objA, objB, J1M * l);

            // std::cout << "c " << l << " " << -pB.nImpulseSum << "\n";
            pB.nImpulseSum = 0;
        } else {
            if (sepA && sepB) {  // Both separating
                lambda.x = -pA.nImpulseSum;
                lambda.y = -pB.nImpulseSum;
                pA.nImpulseSum = 0;
                pB.nImpulseSum = 0;
            } else {  // Both holding
                pA.nImpulseSum += lambda.x;
                pB.nImpulseSum += lambda.y;
            }
            addVelocity(objA, objB, J1M * lambda.x + J2M * lambda.y);

            // std::cout << "b " << lambda.x << " " << lambda.y << "\n";
        }
    }

    for (ContactPoint& p : points) {  // Friction
        V = getVelocityVector(objA, objB);

        Vec2d offsetA = objA->localToGlobalVec(p.localA);
        Vec2d offsetB = objB->localToGlobalVec(p.localB);

        Vec2d tangent(-p.normal.y, p.normal.x);
        Vec6d JT(-tangent.x, -tangent.y, tangent.cross(offsetA), tangent.x,
                 tangent.y, -tangent.cross(offsetB));

        double lT = -JT.dot(V) / ((JT.componentMultiply(JT)).dot(M));

        // double newTImpulseSum = std::clamp(p.tImpulseSum + lT, -p.nImpulseSum
        // * friction, p.nImpulseSum * friction);
        double newTImpulseSum =
            std::min(std::max(p.tImpulseSum + lT, -p.nImpulseSum * friction),
                     p.nImpulseSum * friction);

        lT = newTImpulseSum - p.tImpulseSum;
        p.tImpulseSum = newTImpulseSum;
        // std::cout << i << p.globalA << p.globalB << "\n";
        addVelocity(objA, objB, JT.componentMultiply(M) * lT);
    }
}

void ContactConstraint::updatePoints() {
    for (auto it = points.begin(); it != points.end();) {
        ContactPoint& point = *it;

        Vec2d globalA = this->objA->localToGlobal(point.localA);
        Vec2d globalB = this->objB->localToGlobal(point.localB);

        if ((globalB - globalA).dot(point.normal) > 0 ||
            (globalA - point.globalA).length2() > persistenceThresh ||
            (globalB - point.globalB).length2() > persistenceThresh) {
            it = points.erase(it);
            continue;
        }
        point.penetration = (globalA - globalB).dot(point.normal);
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
        double dist = (pB.globalA - pA.globalA).length2();
        for (uint i = 1; i < points.size(); i++) {
            ContactPoint current = points[i];
            double curDist = (current.globalA - pA.globalA).length2();
            if (curDist > dist) {
                pB = current;
                dist = curDist;
            }
        }

        points.clear();
        points.push_back(pA);
        points.push_back(pB);
    }

    for (ContactPoint& point : points) {
        point.nImpulseSum = 0;
        point.tImpulseSum = 0;

        Vec2d offsetA = objA->localToGlobalVec(point.localA);
        Vec2d offsetB = objB->localToGlobalVec(point.localB);

        Vec2d velA = objA->vel + Vec2d(-offsetA.y, offsetA.x) * objA->rotV;
        Vec2d velB = objB->vel + Vec2d(-offsetB.y, offsetB.x) * objB->rotV;
        point.closingVelocity = (velB - velA).dot(point.normal);
    }
}

void ContactConstraint::addPoint(Collision col) {
    Vec2d globalA = objA->localToGlobal(col.localA);
    Vec2d globalB = objB->localToGlobal(col.localB);

    for (ContactPoint point : points) {
        if ((point.globalA - globalA).length2() < persistenceThresh ||
            (point.globalB - globalB).length2() < persistenceThresh) {
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

    Vec2d offsetA = objA->localToGlobalVec(point.localA);
    Vec2d offsetB = objB->localToGlobalVec(point.localB);
    point.jacobian =
        Vec6d(-point.normal.x, -point.normal.y, point.normal.cross(offsetA),
              point.normal.x, point.normal.y, -point.normal.cross(offsetB));

    points.push_back(point);
}

uint ContactConstraint::numPoints() { return points.size(); }

void PivotConstraint::apply(const double baumgarteBias, const double slopP,
                            const double slopR) {
    Vec2d rA = objA->localToGlobalVec(localA);
    Vec2d rB = objB->localToGlobalVec(localB);

    Vec6d V = getVelocityVector(objA, objB);

    Vec2d d = objB->pos + rB - objA->pos - rA;

    Vec6d J1(-1, 0, rA.y, 1, 0, -rB.y);
    Vec6d J2(0, -1, -rA.x, 0, 1, rB.x);

    Vec6d J1M = J1.componentMultiply(M);
    Vec6d J2M = J2.componentMultiply(M);
    mat2x2 mat{J1.dot(J1M), J1.dot(J2M), J2.dot(J1M), J2.dot(J2M)};
    Vec2d l = mat.invert().apply(-J1.dot(V) - baumgarteBias * d.x,
                                 -J2.dot(V) - baumgarteBias * d.y);

    // std::cout << l << std::endl;

    addVelocity(objA, objB, J1M * l.x + J2M * l.y);
}

void FixedConstraint::apply(const double baumgarteBias, const double slopP,
                            const double slopR) {
    Vec2d rA = objA->localToGlobalVec(localA);
    Vec2d rB = objB->localToGlobalVec(localB);

    Vec6d V = getVelocityVector(objA, objB);

    Vec2d d = objB->pos + rB - objA->pos - rA;

    Vec6d J1(-1, 0, rA.y, 1, 0, -rB.y);
    Vec6d J2(0, -1, -rA.x, 0, 1, rB.x);
    Vec6d J3(0, 0, -1, 0, 0, 1);

    Vec6d J1M = J1.componentMultiply(M);
    Vec6d J2M = J2.componentMultiply(M);
    Vec6d J3M = J3.componentMultiply(M);

    mat3x3 mat{J1.dot(J1M), J1.dot(J2M), J1.dot(J3M), 
               J2.dot(J1M), J2.dot(J2M), J2.dot(J3M), 
               J3.dot(J1M), J3.dot(J2M), J3.dot(J3M)
            };

    Vec3d l = mat.invert().apply(
        -J1.dot(V) - baumgarteBias * d.x, -J2.dot(V) - baumgarteBias * d.y,
        -J3.dot(V) - 2 * baumgarteBias * (objB->rot - objA->rot));

    addVelocity(objA, objB, J1M * l.x + J2M * l.y + J3M * l.z);
}

void SliderConstraint::apply(const double baumgarteBias, const double slopP,
                             const double slopR) {
    Vec2d rA = objA->localToGlobalVec(localA);
    Vec2d rB = objB->localToGlobalVec(localB);
    Vec2d normal = objA->localToGlobalVec(localN);

    Vec6d V = getVelocityVector(objA, objB);

    Vec2d d = objB->pos + rB - objA->pos - rA;

    Vec6d J1(-normal.x, -normal.y, -(rA + d).cross(normal), normal.x, normal.y,
             rB.cross(normal));
    Vec6d J2(0, 0, -1, 0, 0, 1);

    Vec6d J1M = J1.componentMultiply(M);
    Vec6d J2M = J2.componentMultiply(M);

    mat2x2 mat{J1.dot(J1M), J1.dot(J2M), J2.dot(J1M), J2.dot(J2M)};

    Vec2d l = mat.invert().apply(
        -J1.dot(V) - baumgarteBias * d.dot(normal),
        -J2.dot(V) - 2 * baumgarteBias * (objB->rot - objA->rot));

    addVelocity(objA, objB, J1M * l.x + J2M * l.y);
}
