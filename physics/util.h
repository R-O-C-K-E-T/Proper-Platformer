#pragma once

#include <vector>

#include "vector.h"
#include "objects.h"

#include <cmath>

inline bool checkWinding(const std::vector<Vec2>& polygon) {
    float_type total = 0;
    Vec2 a = polygon[polygon.size() - 1];
    for (uint i = 0; i < polygon.size(); i++) {
        Vec2 b = polygon[i];
        total += (b.x - a.x) * (a.y + b.y);
        a = b;
    }
    return total > 0;
}

inline bool checkWinding(const Vec2& a, const Vec2& b, const Vec2& c) { // Checks that we're in clockwise winding
    float_type total = (a.x - c.x) * (c.y + a.y) + (b.x - a.x) * (a.y + b.y) +
                   (c.x - b.x) * (b.y + c.y);
    return total > 0;
}

inline float_type lineDistance(const Vec2& a, const Vec2& b, const Vec2& p) {
    Vec2 d = b - a;
    float_type l = d.length();
    if (l == 0) return (a - p).length();
    return (d.y * p.x - d.x * p.y + b.x * a.y - b.y * a.x) / l;
}

inline float_type originLineDistance(const Vec2& a, const Vec2& b) {
    Vec2 d = b - a;
    float_type l = d.length2();
    if (l == 0) return a.length();
    return (b.x*a.y - b.y*a.x) / sqrt(l);
}

inline void addVelocity(Object *a, Object *b, const Vec6& vec) {
    a->vel.x += vec.a;
    a->vel.y += vec.b;
    a->rotV += vec.c;
    b->vel.x += vec.d;
    b->vel.y += vec.e;
    b->rotV += vec.f;
}

inline Vec6 getVelocityVector(const Object *a, const Object *b) {
    return Vec6(a->vel.x, a->vel.y, a->rotV, b->vel.x, b->vel.y, b->rotV);
}

inline Vec6 getMassMatrix(const Object *a, const Object *b) {
    return Vec6(a->getInvMass(), a->getInvMass(), a->getInvMoment(),
                 b->getInvMass(), b->getInvMass(),
                 b->getInvMoment());  // Diagonal inverse mass matrix
}