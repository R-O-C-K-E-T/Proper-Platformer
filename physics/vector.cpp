
#include "vector.h"

#include <cmath>

bool Vec2d::operator==(const Vec2d& other) const {
   return x == other.x && y == other.y;
}

Vec2d Vec2d::operator-() const {
   return Vec2d(-x,-y);
}

Vec2d Vec2d::operator+(const Vec2d& other) const {
   return Vec2d(x+other.x, y+other.y);
}

Vec2d Vec2d::operator-(const Vec2d& other) const {
   return Vec2d(x-other.x, y-other.y);
}

Vec2d Vec2d::operator*(const double factor) const {
   return Vec2d(x*factor, y*factor);
}

Vec2d Vec2d::operator/(const double factor) const {
   return Vec2d(x/factor, y/factor);
}

void Vec2d::operator+=(const Vec2d& other) {
   x += other.x;
   y += other.y;
}

void Vec2d::operator-=(const Vec2d& other) {
   x -= other.x;
   y -= other.y;
}

void Vec2d::operator*=(const double factor) {
   x *= factor;
   y *= factor;
}

void Vec2d::operator/=(const double factor) {
   x /= factor;
   y /= factor;
}

double Vec2d::dot(const Vec2d& other) const {
   return x*other.x + y*other.y;
}

double Vec2d::dot(const double other_x, const double other_y) const {
   return x*other_x + y*other_y;
} 

double Vec2d::cross(const Vec2d& other) const {
   return x*other.y - y*other.x;
}

double Vec2d::length2() const {
   return x*x + y*y;
}

double Vec2d::length() const {
   return sqrt(x*x + y*y);
}

Vec2d Vec2d::rotate(const double angle) const {
   double s = sin(angle);
   double c = cos(angle);
   return Vec2d(x*c - y*s, x*s + y*c);
}

Vec2d Vec2d::normalise() const {
   return (*this) / this->length();
}

std::ostream & operator<<(std::ostream & Str, const Vec2d& v) { 
  return Str << "[" << v.x << "," << v.y << "]";
}

mat2x2 mat2x2::invert() const {
   const double det = a*d - b*c;
   return mat2x2 {d/det,-b/det,-c/det,a/det};
}

Vec2d mat2x2::solve(const Vec2d& vec) const {
   return Vec2d(d*vec.x - b*vec.y, a*vec.y - c*vec.x) / (a*d - b*c);
}

Vec2d mat2x2::solve(const double x, const double y) const {
   return Vec2d(d*x - b*y, a*y - c*x) / (a*d - b*c);
}

mat3x3 mat3x3::invert() const {
   double A = +(e*i - f*h);
   double B = -(d*i - f*g);
   double C = +(d*h - e*g);
   double D = -(b*i - c*h);
   double E = +(a*i - c*g);
   double F = -(a*h - b*g);
   double G = +(b*f - c*e);
   double H = -(a*f - c*d);
   double I = +(a*e - b*d);

   double det = a*A + b*B + c*C;

   return mat3x3 {A/det, D/det, G/det, B/det, E/det, H/det, C/det, F/det, I/det};
}

Vec3d mat3x3::apply(const Vec3d& vec) const {
   return Vec3d(a*vec.x + b*vec.y + c*vec.z,
                d*vec.x + e*vec.y + f*vec.z,
                g*vec.x + h*vec.y + i*vec.z);
}
Vec3d mat3x3::apply(const double x, const double y, const double z) const {
   return Vec3d(a*x + b*y + c*z,
                d*x + e*y + f*z,
                g*x + h*y + i*z);
}

Vec2d mat2x2::apply(const Vec2d& vec) const {
   return Vec2d(a*vec.x + b * vec.y, c*vec.x + d*vec.y);
}
Vec2d mat2x2::apply(const double x, const double y) const {
   return Vec2d(a*x + b*y, c*x + d*y);
}

Vec2d mat2x2::applyT(const Vec2d& vec) const {
   return Vec2d(a*vec.x + c * vec.y, b*vec.x + d*vec.y);
}
Vec2d mat2x2::applyT(const double x, const double y) const {
   return Vec2d(a*x + c*y, b*x + d*y);
}

double Vec3d::dot(const Vec3d& other) const {
   return x*other.x + y*other.y + z*other.z;
}

double Vec6d::dot(const Vec6d& other) const {
   return a*other.a + b*other.b + c*other.c + d*other.d + e*other.e + f*other.f;
}

Vec6d Vec6d::componentMultiply(const Vec6d& other) const {
   return Vec6d(a*other.a,b*other.b,c*other.c,d*other.d,e*other.e,f*other.f);
}

Vec6d Vec6d::operator +(const Vec6d& other) const {
   return Vec6d(a+other.a,b+other.b,c+other.c,d+other.d,e+other.e,f+other.f);
}
Vec6d Vec6d::operator -(const Vec6d& other) const {
   return Vec6d(a-other.a,b-other.b,c-other.c,d-other.d,e-other.e,f-other.f);
}
Vec6d Vec6d::operator *(const double factor) const {
   return Vec6d(a*factor,b*factor,c*factor,d*factor,e*factor,f*factor);
}
Vec6d Vec6d::operator /(const double factor) const {
   return Vec6d(a/factor,b/factor,c/factor,d/factor,e/factor,f/factor);
}

mat2x2 const genRotationMat(const double angle) {
   mat2x2 mat;
   mat.a = mat.d = cos(angle);
   mat.c = sin(angle);
   mat.b = -mat.c;
   return mat;
}