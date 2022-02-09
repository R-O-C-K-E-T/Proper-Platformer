#include "physics.h"

#include <algorithm>
#include <cmath>
#include <iostream>
#include <list>
#include <optional>

#include "aabb.h"
#include "util.h"
#include "vector.h"
#include "constraint.h"

#ifdef DEBUG
std::vector<Vec2> collisions;
#endif

struct CSOResult {
    Vec2 res;
    Vec2 src;
    //std::pair<Vec2, Vec2> locals;
};

inline CSOResult CSOSupport(BaseCollider *a, BaseCollider *b, const Vec2& vec) {
    return {
        a->globalSupport(vec) - b->globalSupport(-vec),
        vec
    };
}

Vec2 pointToLine(const Vec2 &a, const Vec2 &b, const Vec2 &p) {
    Vec2 d = b - a;
    float_type v = d.dot(p - a);
    if (v <= 0) return a;
    float_type m = d.length2();
    if (v >= m) return b;
    return a + d * (v / m);
}

Vec2 originToLine(const Vec2 &a, const Vec2 &b) {
    Vec2 d = a - b;
    float_type v = d.dot(a);
    if (v <= 0) return a;
    float_type m = d.length2();
    if (v >= m) return b;
    return a - d * (v / m);
}

Vec2 pointToTriangle(const Vec2 &a, const Vec2 &b, const Vec2 &c,
                      const Vec2 &p) {
    float_type u = (a - b).cross(p - b);
    float_type v = (c - a).cross(p - a);
    float_type w = (b - c).cross(p - c);

    if (u <= 0 && v <= 0) return a;
    if (u <= 0 && w <= 0) return b;
    if (v <= 0 && w <= 0) return c;

    if (u <= 0) return pointToLine(a, b, p);
    if (v <= 0) return pointToLine(a, c, p);
    if (w <= 0) return pointToLine(b, c, p);

    return p;
}

Vec2 originToTriangle(const Vec2 &a, const Vec2 &b, const Vec2 &c) {
    float_type u = (b - a).cross(b);
    float_type v = (a - c).cross(a);
    float_type w = (c - b).cross(c);

    if (u <= 0 && v <= 0) return a;
    if (u <= 0 && w <= 0) return b;
    if (v <= 0 && w <= 0) return c;

    if (u <= 0) return originToLine(a, b);
    if (v <= 0) return originToLine(a, c);
    if (w <= 0) return originToLine(b, c);

    return ORIGIN;
}

const Collision nocollision = {-1.0, Vec2(), Vec2(), Vec2()};

Collision evaluateCollision(BaseCollider *a, BaseCollider *b,
                            Vec2 initialDir) {  // const Vec2& initialAxis) {
    CSOResult simplex[3];

    // initialDir = Vec2(0.7, 0.4);
    const float_type epsilon = 0.03 * 0.03;
    // const float_type epsilon2 = 0.001*0.001;

    // GJK
    simplex[0] = CSOSupport(a, b, initialDir);
    if (simplex[0].res.dot(initialDir) <= 0) return nocollision;

    Vec2 direction = -simplex[0].res;

    unsigned int length = 1;
    unsigned int i;
    for (i = 0; i < 20; i++) {
        simplex[length] = CSOSupport(a, b, direction);
        if (simplex[length].res.dot(direction) <= 0) return nocollision;

        if (length == 1) {
            Vec2 d = simplex[0].res - simplex[1].res;
            direction =
                d * d.dot(simplex[0].res) - simplex[0].res * d.length2();
            if (direction == ORIGIN) {
                Vec2 normal(simplex[0].res.y - simplex[1].res.y,
                             simplex[1].res.x - simplex[0].res.x);
                simplex[2] = CSOSupport(a, b, normal);
                if (simplex[2].res == simplex[0].res ||
                    simplex[2].res == simplex[1].res) {
                    simplex[2] = CSOSupport(a, b, -normal);
                }
                if (!checkWinding(simplex[0].res, simplex[1].res,
                                  simplex[2].res)) {
                    std::swap(simplex[0], simplex[1]);
                }
                break;
            }
            length = 2;
        } else {
            if (!checkWinding(simplex[0].res, simplex[1].res, simplex[2].res)) {
                std::swap(simplex[0], simplex[1]);
            }
            if (simplex[1].res.dot(simplex[2].res.y - simplex[1].res.y,
                                   simplex[1].res.x - simplex[2].res.x) > 0) {
                if ((simplex[2].res - simplex[1].res).dot(simplex[2].res) > 0) {
                    simplex[0] = simplex[2];
                    direction = Vec2(simplex[1].res.y - simplex[2].res.y,
                                      simplex[2].res.x - simplex[1].res.x);
                } else if ((simplex[2].res - simplex[0].res)
                               .dot(simplex[0].res) > 0) {
                    simplex[1] = simplex[2];
                    direction = Vec2(simplex[2].res.y - simplex[0].res.y,
                                      simplex[0].res.x - simplex[2].res.x);
                } else {
                    simplex[0] = simplex[2];
                    direction = -simplex[2].res;
                    length = 1;
                }
            } else if (simplex[0].res.dot(simplex[0].res.y - simplex[2].res.y,
                                          simplex[2].res.x - simplex[0].res.x) >
                       0) {
                if ((simplex[0].res - simplex[2].res).dot(simplex[0].res) > 0) {
                    simplex[1] = simplex[2];
                    direction = Vec2(simplex[2].res.y - simplex[0].res.y,
                                      simplex[0].res.x - simplex[2].res.x);
                } else {
                    simplex[0] = simplex[2];
                    direction = -simplex[2].res;
                    length = 1;
                }
            } else {
                break;
            }
        }
    }
    if (i == 20) return nocollision;

    struct node {
        float_type dist;
        CSOResult val;
        node *next;
    };

    const int EPA_ITERATIONS = 20;
    node nodes[EPA_ITERATIONS + 2];
    nodes[0].dist = originLineDistance(simplex[0].res, simplex[1].res);
    nodes[0].val = simplex[0];
    nodes[0].next = &nodes[1];

    nodes[1].dist = originLineDistance(simplex[1].res, simplex[2].res);
    nodes[1].val = simplex[1];
    nodes[1].next = &nodes[2];

    nodes[2].dist = originLineDistance(simplex[2].res, simplex[0].res);
    nodes[2].val = simplex[2];
    nodes[2].next = &nodes[0];

    // EPA
    node *next;
    node *best;
    for (uint i = 3;; i++) {
        /*node *current = nodes[0].next;
        best = &nodes[0];
        while (current != &nodes[0]) {
            if (current->dist < best->dist) {
                best = current;
            }
            current = current->next;
        }
        next = best->next;*/
        best = &nodes[0];
        for (uint j = 1; j < i; j++) {
            node* current = &nodes[j];
            if (current->dist < best->dist) {
                best = current;
            }
        }
        next = best->next;

        Vec2 normal(best->val.res.y - next->val.res.y,
                     next->val.res.x - best->val.res.x);

        CSOResult result = CSOSupport(a, b, normal);

        if ((result.res - next->val.res).length2() < epsilon ||
            (result.res - best->val.res).length2() < epsilon) {
            break;
        }

        if (i == EPA_ITERATIONS + 2) return nocollision;

        node *newNode = &nodes[i];

        best->next = newNode;
        best->dist = originLineDistance(best->val.res, result.res);

        newNode->next = next;
        newNode->dist = originLineDistance(result.res, next->val.res);
        newNode->val = result;
    }
    const CSOResult pA = best->val;
    const CSOResult pB = next->val;
    const float_type dist = best->dist;

    Vec2 delta = pB.res - pA.res;
    float_type proportion =
        -delta.dot(pA.res) / delta.length2();  // How far along the edge are we

    Collision col;
    col.penetration = dist;
    col.normal = Vec2(pA.res.y - pB.res.y, pB.res.x - pA.res.x).normalised();
    
    col.localA = a->support(a->globalToLocalVec(pA.src)) * (1 - proportion) + a->support(a->globalToLocalVec(pB.src)) * proportion;
    col.localB = b->support(b->globalToLocalVec(-pA.src)) * (1 - proportion) + b->support(b->globalToLocalVec(-pB.src)) * proportion;

#ifdef DEBUG
    collisions.push_back(a->localToGlobal(col.localA));
    collisions.push_back(b->localToGlobal(col.localB));
#endif

    return col;
}

bool originInTriangle(const Vec2 &a, const Vec2 &b, const Vec2 &c) {
    Vec2 ab = b - a;
    Vec2 bc = c - b;
    Vec2 ca = a - c;

    float_type pab = ab.cross(a);
    float_type pbc = bc.cross(b);
    if (pab * pbc < 0) return false;

    float_type pca = ca.cross(c);
    if (pab * pca < 0) return false;

    return true;
}

// f(x,0) = 0, f(x,y) = f(y,x), f(x,x) = x
float_type combineProperties(float_type a, float_type b) { return sqrt(a * b); }

void World::resolveCollision(Object *a, Object *b, const Collision &col) {
    bool resA = a->collisionHandler != nullptr &&
                a->collisionHandler(a, b, -col.normal, col.localA, col.localB);
    bool resB =
        b->collisionHandler != nullptr && b->collisionHandler(b, a, col.normal, col.localB, col.localA);
    if (resA || resB) return;

    try {
        contactConstraints.at({a,b}).addPoint(col);
    } catch (std::out_of_range&) {
        ContactConstraint newConstraint = ContactConstraint(a, b, combineProperties(a->friction, b->friction), combineProperties(a->restitution, b->restitution));
        newConstraint.addPoint(col);
        contactConstraints[{a,b}] = newConstraint;
    }
    
    /*ContactConstraint *emptyConstraint = nullptr;
    for (ContactConstraint &contact : contactConstraints) {
        if (contact.objA == a && contact.objB == b) {
            contact.addPoint(col);
            return;
        }
        if (emptyConstraint == nullptr && contact.points.size() == 0) {
            emptyConstraint = &contact;
        }
    }
    if (emptyConstraint == nullptr) {
        contactConstraints.emplace_back(
        a, b, combineProperties(a->friction, b->friction),
        combineProperties(a->restitution, b->restitution));
        contactConstraints[contactConstraints.size() - 1].addPoint(col);
    } else {
        *emptyConstraint = ContactConstraint(a, b, combineProperties(a->friction, b->friction), combineProperties(a->restitution, b->restitution));
        emptyConstraint->addPoint(col);
    }*/
}

std::vector<std::pair<Object *, Object *>> World::broadphase() {
    /*for (std::pair<Node *, Object *> pair : nodeMap) {
        const std::pair<Vec2, Vec2> bounds = pair.second->getBounds();
        pair.first->inner = AABB(bounds.second, bounds.first);
    }*/

    tree.update();

    // std::cout << objects.size() << std::endl;

    std::vector<std::pair<Object *, Object *>> result;
    for (auto& pair : tree.computePairs()) {
        Object *objA = reinterpret_cast<Object*>(pair.first); //nodeMap.at(pair.first);
        Object *objB = reinterpret_cast<Object*>(pair.second); //nodeMap.at(pair.second);

        if (objA->getInvMass() == 0 && objB->getInvMass() == 0 &&
            objA->getInvMoment() == 0 && objB->getInvMoment() == 0)
            continue;
        if (std::any_of(objA->constraints.begin(), objA->constraints.end(),
                        [objB](BaseConstraint *c) {
                            return !c->allowCollision &&
                                   (c->objA == objB || c->objB == objB);
                        }))
            continue;
        result.emplace_back(objA, objB);
    }

    return result;
}

void World::update(float_type stepSize) {
#ifdef DEBUG
    collisions.clear();
#endif
    for (auto& potential : broadphase()) {
        const Object *a = potential.first;
        const Object *b = potential.second;

        Vec2 initialDir = Vec2(0.7, 0.4);  // b->pos - a->pos;

        for (BaseCollider *colliderA : a->colliders) {
            for (BaseCollider *colliderB : b->colliders) {
                Collision col =
                    evaluateCollision(colliderA, colliderB, initialDir);
                if (col.penetration < 0) continue;
                resolveCollision(potential.first, potential.second, col);
            }
        }
    }

    float_type adjustedBaumgarteBias = baumgarteBias / stepSize;
    Vec2 tickGravity = gravity * stepSize;

    for (auto& entry : contactConstraints)
        entry.second.updatePoints(adjustedBaumgarteBias, slopP, slopR, tickGravity);


    for (auto& entry : contactConstraints) {
        auto V = get_velocity_vector(*entry.second.objA, *entry.second.objB);
        auto M = get_inverse_mass_matrix(*entry.second.objA, *entry.second.objB);
        for (auto& point : entry.second.points) {
            V += apply_constraint(point.J, M, point.nImpulseSum);
        }
        set_velocity(*entry.second.objA, *entry.second.objB, V);
    }
    
    for (int j = 0; j < solverSteps; j++) {
        for (Object *obj : objects)
            obj->updateConstraints(adjustedBaumgarteBias, slopP, slopR);
        for (auto& entry : contactConstraints) {
            if (entry.second.points.size() != 0) {
                entry.second.apply();
            }
        }
    }

    for (Object *obj : objects) {
        obj->update(stepSize);
        if (obj->getInvMass() != 0) {
            obj->vel += tickGravity;
        }
    }
}

void World::clear() {
    for (Object *obj : objects) delete obj;
    objects.clear();
    contactConstraints.clear();
}

void World::addObject(Object *obj) {
    objects.push_back(obj);

    tree.addNode(obj);
}

void World::removeObject(Object *obj) {
    objects.erase(std::remove(objects.begin(), objects.end(), obj),
                  objects.end());

    for (auto iter = contactConstraints.begin(); iter != contactConstraints.end();) {
        ContactConstraint &contact = (*iter).second;
        if (contact.objA == obj || contact.objB == obj) {
            iter = contactConstraints.erase(iter);
        } else {
            iter++;
        }
    }

    tree.removeNode(obj);
}

std::vector<ContactConstraint> World::getContacts() const {
    std::vector<ContactConstraint> contacts;
    contacts.reserve(contacts.size());
    for (auto& entry : contactConstraints) contacts.push_back(entry.second);
    return contacts;
}

/*
int main(int argc, const char *argv[]) {
    // if (argc != 7) {
    //     std::cout << "Wrong number of arguments\n";
    //     return 1;
    // }

    // float_type values[6];
    // for (int i = 0; i<6; i++) {
    //     values[i] = std::stod(argv[i+1]);
    // }

    std::vector<Vec2> square = {Vec2(-1, -1), Vec2(+1, -1), Vec2(+1, +1),
                                 Vec2(-1, +1)};
    if (!checkWinding(square)) std::reverse(square.begin(), square.end());

    Object *objA = new Object(1.0, 1.0, 1.0, 1.0, nullptr);
    // BaseCollider *colliderA = new PolyCollider(objA, square);
    BaseCollider *colliderA = new CircleCollider(objA, 1.0);

    Object *objB = new Object(1.0, 1.0, 1.0, 1.0, nullptr);
    // BaseCollider *colliderB = new PolyCollider(objB, square);
    BaseCollider *colliderB = new CircleCollider(objB, 1.0);

    for (uint i = 0; i < 10; i++) {
        objA->pos = Vec2(0, 0);
        objA->rot = 0;
        objA->updateRotMat();

        objB->pos = Vec2(1.999, 0).rotate(M_PI * i / 20);
        objB->rot = 0;
        objB->updateRotMat();

        Vec2 initialDir = Vec2(0.7, 0.4);  // objA->pos - objB->pos;

        Collision collisions[2] = {
            evaluateCollisionSlow(colliderA, colliderB, initialDir),
            evaluateCollision(colliderA, colliderB, initialDir)};

        std::cout << i << std::endl;
        for (Collision col : collisions) {
            std::cout << col.penetration << " " << col.normal << " "
                      << col.localA << " " << col.localB << std::endl;
        }
    }
}*/

/*int main() {
    Object *objA = new Object( -1, -1, 0, 0.5, nullptr);

    std::vector<Vec2> pointsA;
    pointsA.push_back(Vec2(-10,-10));
    pointsA.push_back(Vec2(-10,10));
    pointsA.push_back(Vec2(10,10));
    pointsA.push_back(Vec2(10,-10));

    new PolyCollider(objA, pointsA);
    

    
    Object *objB = new Object(157.07963267948966, 7853.981633974483, 0, 0.5, nullptr); objB->pos = Vec2(15,15);

    new CircleCollider(objB, 10);

    auto result = evaluateCollision(objA->colliders[0], objB->colliders[0], objA->pos - objB->pos); 
    
    std::cout << result.normal << result.penetration << result.localA << result.localB << "\n";
}*/