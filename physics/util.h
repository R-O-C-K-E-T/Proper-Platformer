#ifndef __UTIL_H_INCLUDED__ 
#define __UTIL_H_INCLUDED__ 

#include <vector>
#include "vector.h"
#include "objects.h"

bool checkWinding(const std::vector<Vec2d>& polygon);
bool checkWinding(const Vec2d& a, const Vec2d& b, const Vec2d& c);

double originLineDistance(const Vec2d& a, const Vec2d& b);
double lineDistance(const Vec2d& a, const Vec2d& b, const Vec2d& p);

void addVelocity(Object *a, Object *b, const Vec6d& V);
Vec6d getVelocityVector(const Object *a, const Object *b);
Vec6d getMassMatrix(const Object *a, const Object *b);

#endif