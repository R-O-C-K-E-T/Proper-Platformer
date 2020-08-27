#include "util.h"
#include <cmath>

bool checkWinding(const std::vector<Vec2d>& polygon) {
    double total = 0;
    Vec2d a = polygon[polygon.size() - 1];
    for (uint i = 0; i < polygon.size(); i++) {
        Vec2d b = polygon[i];
        total += (b.x - a.x) * (a.y + b.y);
        a = b;
    }
    return total > 0;
}
bool checkWinding(const Vec2d& a, const Vec2d& b, const Vec2d& c) { // Checks that we're in clockwise winding
    double total = (a.x - c.x) * (c.y + a.y) + (b.x - a.x) * (a.y + b.y) +
                   (c.x - b.x) * (b.y + c.y);
    return total > 0;
}

double lineDistance(const Vec2d& a, const Vec2d& b, const Vec2d& p) {
    Vec2d d = b - a;
    double l = d.length();
    if (l == 0) return (a - p).length();
    return (d.y * p.x - d.x * p.y + b.x * a.y - b.y * a.x) / l;
}

double originLineDistance(const Vec2d& a, const Vec2d& b) {
    Vec2d d = b - a;
    double l = d.length2();
    if (l == 0) return a.length();
    return (b.x*a.y - b.y*a.x) / sqrt(l);
}

void addVelocity(Object *a, Object *b, const Vec6d& vec) {
    a->vel.x += vec.a;
    a->vel.y += vec.b;
    a->rotV += vec.c;
    b->vel.x += vec.d;
    b->vel.y += vec.e;
    b->rotV += vec.f;
}

Vec6d getVelocityVector(const Object *a, const Object *b) {
    return Vec6d(a->vel.x, a->vel.y, a->rotV, b->vel.x, b->vel.y, b->rotV);
}

Vec6d getMassMatrix(const Object *a, const Object *b) {
    return Vec6d(a->getInvMass(), a->getInvMass(), a->getInvMoment(),
                 b->getInvMass(), b->getInvMass(),
                 b->getInvMoment());  // Diagonal inverse mass matrix
}