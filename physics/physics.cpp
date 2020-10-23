#include "physics.h"

#include <algorithm>
#include <cmath>
#include <iostream>
#include <list>
#include <optional>

#include "aabb.h"
#include "util.h"
#include "vector.h"

#ifdef DEBUG
std::vector<Vec2d> collisions;
#endif

struct CSOResult {
    Vec2d res;
    std::pair<Vec2d, Vec2d> locals;
};

CSOResult CSOSupport(BaseCollider *a, BaseCollider *b, const Vec2d &vec) {
    Vec2d pointA = a->support(a->globalToLocalVec(vec));
    Vec2d pointB = b->support(b->globalToLocalVec(vec * -1));

    return CSOResult{a->localToGlobal(pointA) - b->localToGlobal(pointB),
                     std::pair<Vec2d, Vec2d>{pointA, pointB}};
}

Vec2d pointToLine(const Vec2d &a, const Vec2d &b, const Vec2d &p) {
    Vec2d d = b - a;
    double v = d.dot(p - a);
    if (v <= 0) return a;
    double m = d.length2();
    if (v >= m) return b;
    return a + d * (v / m);
}

Vec2d originToLine(const Vec2d &a, const Vec2d &b) {
    Vec2d d = a - b;
    double v = d.dot(a);
    if (v <= 0) return a;
    double m = d.length2();
    if (v >= m) return b;
    return a - d * (v / m);
}

Vec2d pointToTriangle(const Vec2d &a, const Vec2d &b, const Vec2d &c,
                      const Vec2d &p) {
    double u = (a - b).cross(p - b);
    double v = (c - a).cross(p - a);
    double w = (b - c).cross(p - c);

    if (u <= 0 && v <= 0) return a;
    if (u <= 0 && w <= 0) return b;
    if (v <= 0 && w <= 0) return c;

    if (u <= 0) return pointToLine(a, b, p);
    if (v <= 0) return pointToLine(a, c, p);
    if (w <= 0) return pointToLine(b, c, p);

    return p;
}

Vec2d originToTriangle(const Vec2d &a, const Vec2d &b, const Vec2d &c) {
    double u = (b - a).cross(b);
    double v = (a - c).cross(a);
    double w = (c - b).cross(c);

    if (u <= 0 && v <= 0) return a;
    if (u <= 0 && w <= 0) return b;
    if (v <= 0 && w <= 0) return c;

    if (u <= 0) return originToLine(a, b);
    if (v <= 0) return originToLine(a, c);
    if (w <= 0) return originToLine(b, c);

    return ORIGIN;
}

const Collision nocollision = {-1.0, Vec2d(), Vec2d(), Vec2d()};

/*Vec2d d = a - b;
    double v = d.dot(a);
    if (v <= 0) return a;
    double m = d.length2();
    if (v >= m) return b;
    return a - d * (v / m);*/

Collision evaluateCollision(BaseCollider *a, BaseCollider *b,
                            Vec2d initialDir) {  // const Vec2d& initialAxis) {
    CSOResult simplex[3];

    // initialDir = Vec2d(0.7, 0.4);
    const double epsilon = 0.03 * 0.03;
    // const double epsilon2 = 0.001*0.001;

    // GJK
    simplex[0] = CSOSupport(a, b, initialDir);
    if (simplex[0].res.dot(initialDir) <= 0) return nocollision;

    Vec2d direction = -simplex[0].res;

    unsigned int length = 1;
    unsigned int i;
    for (i = 0; i < 20; i++) {
        simplex[length] = CSOSupport(a, b, direction);
        if (simplex[length].res.dot(direction) <= 0) return nocollision;

        if (length == 1) {
            Vec2d d = simplex[0].res - simplex[1].res;
            direction =
                d * d.dot(simplex[0].res) - simplex[0].res * d.length2();
            if (direction == ORIGIN) {
                Vec2d normal(simplex[0].res.y - simplex[1].res.y,
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
                    direction = Vec2d(simplex[1].res.y - simplex[2].res.y,
                                      simplex[2].res.x - simplex[1].res.x);
                } else if ((simplex[2].res - simplex[0].res)
                               .dot(simplex[0].res) > 0) {
                    simplex[1] = simplex[2];
                    direction = Vec2d(simplex[2].res.y - simplex[0].res.y,
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
                    direction = Vec2d(simplex[2].res.y - simplex[0].res.y,
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
        double dist;
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
    for (unsigned int i = 0;; i++) {
        node *current = nodes[0].next;
        best = &nodes[0];
        while (current != &nodes[0]) {
            if (current->dist < best->dist) {
                best = current;
            }
            current = current->next;
        }
        next = best->next;

        Vec2d normal(best->val.res.y - next->val.res.y,
                     next->val.res.x - best->val.res.x);

        CSOResult result = CSOSupport(a, b, normal);

        if ((result.res - next->val.res).length2() < epsilon ||
            (result.res - best->val.res).length2() < epsilon) {
            break;
        }

        if (i == EPA_ITERATIONS - 1) return nocollision;

        node *newNode = &nodes[i + 3];

        best->next = newNode;
        best->dist = originLineDistance(best->val.res, result.res);

        newNode->next = next;
        newNode->dist = originLineDistance(result.res, next->val.res);
        newNode->val = result;
    }
    const CSOResult pA = best->val;
    const CSOResult pB = next->val;

    Vec2d delta = pB.res - pA.res;
    double proportion =
        -delta.dot(pA.res) / delta.length2();  // How far along the edge are we

    Collision col;
    col.penetration = best->dist;
    col.normal = Vec2d(pA.res.y - pB.res.y, pB.res.x - pA.res.x).normalise();

    col.localA =
        pA.locals.first + (pB.locals.first - pA.locals.first) * proportion;
    col.localB =
        pA.locals.second + (pB.locals.second - pA.locals.second) * proportion;

#ifdef DEBUG
    collisions.push_back(a->localToGlobal(col.localA));
    collisions.push_back(b->localToGlobal(col.localB));
#endif

    return col;
}

Collision evaluateCollisionSlow(
    BaseCollider *a, BaseCollider *b,
    Vec2d initialDir) {  // const Vec2d& initialAxis) {

    std::vector<CSOResult> polygon(3);

    // initialDir = Vec2d(0.7, 0.4);
    const double epsilon = 0.03 * 0.03;
    // const double epsilon2 = 0.001*0.001;

    // GJK
    polygon[0] = CSOSupport(a, b, initialDir);
    if (polygon[0].res.dot(initialDir) <= 0) return nocollision;

    if (false) {  //(polygon[0].res == ORIGIN) {
        std::cout << "fuk\n";
        return nocollision;
    } else {
        Vec2d direction = -polygon[0].res;

        polygon[1] = CSOSupport(a, b, direction);
        if (polygon[1].res.dot(direction) <= 0) return nocollision;

        Vec2d closest = originToLine(polygon[0].res, polygon[1].res);

        if (closest == ORIGIN) {
            Vec2d normal(polygon[0].res.y - polygon[1].res.y,
                         polygon[1].res.x - polygon[0].res.x);
            polygon[2] = CSOSupport(a, b, normal);
            if (polygon[2].res == polygon[0].res ||
                polygon[2].res == polygon[1].res) {
                polygon[2] = CSOSupport(a, b, -normal);
            }
            if (!checkWinding(polygon[0].res, polygon[1].res, polygon[2].res)) {
                std::swap(polygon[1], polygon[2]);
            }
        } else {
            unsigned int i;
            for (i = 0; i < 20; i++) {
                direction = -closest;

                polygon[2] = CSOSupport(a, b, direction);
                if (polygon[2].res.dot(direction) <= 0) return nocollision;

                if (!checkWinding(polygon[0].res, polygon[1].res,
                                  polygon[2].res)) {
                    std::swap(polygon[0], polygon[1]);
                }

                closest = originToTriangle(polygon[0].res, polygon[1].res,
                                           polygon[2].res);
                if (closest == ORIGIN) break;

                double distA =
                    originLineDistance(polygon[1].res, polygon[2].res);
                double distB =
                    originLineDistance(polygon[2].res, polygon[0].res);
                double distC =
                    originLineDistance(polygon[0].res, polygon[1].res);

                if (distA < distB && distA < distC) {
                    polygon[0] = polygon[1];
                    polygon[1] = polygon[2];
                } else if (distB < distC) {
                    polygon[1] = polygon[2];
                }
            }
            if (i == 20) return nocollision;
        }
    }

    // EPA
    unsigned int i, index, prevIndex;
    for (i = 0; i < 20; i++) {
        prevIndex = polygon.size() - 1;
        index = 0;
        double minDist =
            originLineDistance(polygon[prevIndex].res, polygon[index].res);
        for (uint j = 1; j < polygon.size(); j++) {
            double dist =
                originLineDistance(polygon[j - 1].res, polygon[j].res);
            if (dist < minDist) {
                index = j;
                prevIndex = j - 1;
                minDist = dist;
            }
        }

        Vec2d normal(polygon[prevIndex].res.y - polygon[index].res.y,
                     polygon[index].res.x - polygon[prevIndex].res.x);

        CSOResult result = CSOSupport(a, b, normal);

        if ((result.res - polygon[index].res).length2() < epsilon ||
            (result.res - polygon[prevIndex].res).length2() < epsilon) {
            break;
        }
        polygon.insert(polygon.begin() + index, result);
    }
    if (i == 20) return nocollision;

    Vec2d delta = polygon[index].res - polygon[prevIndex].res;
    double proportion = -delta.dot(polygon[prevIndex].res) /
                        delta.length2();  // How far along the edge are we

    Collision col;
    col.penetration =
        originLineDistance(polygon[prevIndex].res, polygon[index].res);
    col.normal = Vec2d(polygon[prevIndex].res.y - polygon[index].res.y,
                       polygon[index].res.x - polygon[prevIndex].res.x)
                     .normalise();

    col.localA =
        polygon[prevIndex].locals.first +
        (polygon[index].locals.first - polygon[prevIndex].locals.first) *
            proportion;
    col.localB =
        polygon[prevIndex].locals.second +
        (polygon[index].locals.second - polygon[prevIndex].locals.second) *
            proportion;

#ifdef DEBUG
    collisions.push_back(a->localToGlobal(col.localA));
    collisions.push_back(b->localToGlobal(col.localB));
#endif

    return col;
}

bool originInTriangle(const Vec2d &a, const Vec2d &b, const Vec2d &c) {
    Vec2d ab = b - a;
    Vec2d bc = c - b;
    Vec2d ca = a - c;

    double pab = ab.cross(a);
    double pbc = bc.cross(b);
    if (pab * pbc < 0) return false;

    double pca = ca.cross(c);
    if (pab * pca < 0) return false;

    return true;
}

Collision evaluateCollisionMPR(BaseCollider *a, BaseCollider *b) {
    // Vec2d pivot = a->localToGlobal(a->getCentre()) -
    // b->localToGlobal(b->getCentre());

    Vec2d pivot = (CSOSupport(a, b, Vec2d(-1, -1)).res +
                   CSOSupport(a, b, Vec2d(+1, -1)).res +
                   CSOSupport(a, b, Vec2d(-1, +1)).res +
                   CSOSupport(a, b, Vec2d(+1, +1)).res) *
                  (1.0 / 4.0);

    if (pivot == ORIGIN) pivot.x = 0.00001;

    CSOResult portal[2];
    portal[0] = CSOSupport(a, b, -pivot);

    if (portal[0].res.dot(ORIGIN - pivot) <= 0) return nocollision;

    Vec2d rayDir(portal[0].res.y - pivot.y, pivot.x - portal[0].res.x);

    if (rayDir.dot(portal[0].res) > 0) rayDir *= -1;

    portal[1] = CSOSupport(a, b, rayDir);
    if (portal[1].res.dot(rayDir) <= 0) return nocollision;

    unsigned int i;
    for (i = 0; i < 10; i++) {
        /*if (originInTriangle(portal[0].res, portal[1].res, pivot)) {
            break;
        }*/

        rayDir = Vec2d(portal[1].res.y - portal[0].res.y,
                       portal[0].res.x - portal[1].res.x);
        if (rayDir.dot(pivot) > 0) rayDir *= -1;

        CSOResult next = CSOSupport(a, b, rayDir);

        if (rayDir.dot(next.res) < 0) return nocollision;

        if (i > 4 && originInTriangle(portal[0].res, portal[1].res, pivot))
            break;

        Vec2d lineNormal(pivot.y - next.res.y, next.res.x - pivot.x);
        if (lineNormal.dot(next.res) > 0) lineNormal *= -1;

        if (lineNormal.dot(portal[0].res - next.res) > 0) {
            portal[1] = next;
        } else {
            portal[0] = next;
        }
    }
    if (i == 10) return nocollision;

    Collision col;

    Vec2d delta = portal[1].res - portal[0].res;
    double proportion = -portal[0].res.dot(delta) / delta.length2();
    proportion = std::min(std::max(proportion, 0.0), 1.0);

    col.normal = Vec2d(-delta.y, delta.x).normalise();
    col.penetration = portal[0].res.dot(col.normal);
    if (col.penetration < 0) {
        col.normal *= -1;
        col.penetration *= -1;
    }

    col.localA = portal[0].locals.first +
                 (portal[1].locals.first - portal[0].locals.first) * proportion;
    col.localB =
        portal[0].locals.second +
        (portal[1].locals.second - portal[0].locals.second) * proportion;

    return col;
}

// f(x,0) = 0, f(x,y) = f(y,x), f(x,x) = x
double combineProperties(double a, double b) { return sqrt(a * b); }

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
    for (std::pair<Node *, Object *> pair : nodeMap) {
        const std::pair<Vec2d, Vec2d> bounds = pair.second->getBounds();
        pair.first->inner = AABB(bounds.second, bounds.first);
    }

    tree.update();

    // std::cout << objects.size() << std::endl;

    std::vector<std::pair<Object *, Object *>> result;
    for (std::pair<Node *, Node *> pair : tree.computePairs()) {
        Object *objA = nodeMap.at(pair.first);
        Object *objB = nodeMap.at(pair.second);

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

void World::update(double stepSize) {
#ifdef DEBUG
    collisions.clear();
#endif
    for (auto& potential : broadphase()) {
        const Object *a = potential.first;
        const Object *b = potential.second;
        // std::cout << "Potential " << a->pos << " " << b->pos << " " << a->rot
        // << " " << b->rot << " " << a->rotV << " " << b->rotV << std::endl;

        Vec2d initialDir = Vec2d(0.7, 0.4);  // b->pos - a->pos;

        for (BaseCollider *colliderA : a->colliders) {
            for (BaseCollider *colliderB : b->colliders) {
                Collision col =
                    evaluateCollision(colliderA, colliderB, initialDir);
                if (col.penetration < 0) continue;
                resolveCollision(potential.first, potential.second, col);
            }
        }
    }

    /*for (auto it = contactConstraints.begin();
         it != contactConstraints.end();) {
        ContactConstraint &constraint = *it;
        constraint.updatePoints();
        if (constraint.numPoints() == 0) {
            it = contactConstraints.erase(it);
        } else {
            it++;
        }
    }*/

    for (auto& entry : contactConstraints)
        entry.second.updatePoints();

    double adjustedBaumgarteBias = baumgarteBias / stepSize;
    for (int j = 0; j < solverSteps; j++) {
        for (Object *obj : objects)
            obj->updateConstraints(adjustedBaumgarteBias, slopP, slopR);
        for (auto& entry : contactConstraints) {
            if (entry.second.points.size() != 0) {
                entry.second.apply(adjustedBaumgarteBias, slopP, slopR);
            }
        }
    }

    for (Object *obj : objects) {
        obj->update(stepSize);
        if (obj->getInvMass() != 0) {
            obj->vel += gravity * stepSize;
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

    std::pair<Vec2d, Vec2d> bounds = obj->getBounds();
    Node *node = tree.add(AABB(bounds.second, bounds.first));
    nodeMap.insert({node, obj});
}

void World::removeObject(Object *obj) {
    objects.erase(std::remove(objects.begin(), objects.end(), obj),
                  objects.end());
    /*for (auto it = contactConstraints.begin();
         it != contactConstraints.end();) {
        ContactConstraint &contact = *it;
        if (contact.objA == obj || contact.objB == obj) {
            it = contactConstraints.erase(it);
        } else {
            it++;
        }
    }*/
    
    /*for (ContactConstraint &contact : contactConstraints) {
        if (contact.objA == obj || contact.objB == obj) {
            contact.points.clear();
        }
    }*/


    for (auto iter = contactConstraints.begin(); iter != contactConstraints.end();) {
        ContactConstraint &contact = (*iter).second;
        if (contact.objA == obj || contact.objB == obj) {
            iter = contactConstraints.erase(iter);
        } else {
            iter++;
        }
    }

    Node *node = (*std::find_if(nodeMap.begin(), nodeMap.end(),
                                [obj](std::pair<Node *, Object *> pair) {
                                    return pair.second == obj;
                                }))
                     .first;
    nodeMap.erase(node);
    tree.removeNode(node);
    delete node;
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

    // double values[6];
    // for (int i = 0; i<6; i++) {
    //     values[i] = std::stod(argv[i+1]);
    // }

    std::vector<Vec2d> square = {Vec2d(-1, -1), Vec2d(+1, -1), Vec2d(+1, +1),
                                 Vec2d(-1, +1)};
    if (!checkWinding(square)) std::reverse(square.begin(), square.end());

    Object *objA = new Object(1.0, 1.0, 1.0, 1.0, nullptr);
    // BaseCollider *colliderA = new PolyCollider(objA, square);
    BaseCollider *colliderA = new CircleCollider(objA, 1.0);

    Object *objB = new Object(1.0, 1.0, 1.0, 1.0, nullptr);
    // BaseCollider *colliderB = new PolyCollider(objB, square);
    BaseCollider *colliderB = new CircleCollider(objB, 1.0);

    for (uint i = 0; i < 10; i++) {
        objA->pos = Vec2d(0, 0);
        objA->rot = 0;
        objA->updateRotMat();

        objB->pos = Vec2d(1.999, 0).rotate(M_PI * i / 20);
        objB->rot = 0;
        objB->updateRotMat();

        Vec2d initialDir = Vec2d(0.7, 0.4);  // objA->pos - objB->pos;

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

   std::vector<Vec2d> pointsA;
   pointsA.push_back(Vec2d(-10,-10));
   pointsA.push_back(Vec2d(-10,10));
   pointsA.push_back(Vec2d(10,10));
   pointsA.push_back(Vec2d(10,-10));
   std::vector<BaseCollider*> collidersA;
   collidersA.push_back(new PolyCollider(pointsA));
   Object *objA = new Object(collidersA, -1, -1, 0, 0.5);

   std::vector<BaseCollider*> collidersB;
   collidersB.push_back(new CircleCollider(10));
   Object *objB = new Object(collidersB, 157.07963267948966, 7853.981633974483,
0, 0.5); objB->pos = Vec2d(15,15);

   collision result = evaluateCollision(collidersA[0], collidersB[0], objA->pos
- objB->pos); std::cout << result.normal << result.penetration << result.localA
<< result.localB << "\n";

}*/