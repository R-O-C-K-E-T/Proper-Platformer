#ifndef __VECTOR_H_INCLUDED__ 
#define __VECTOR_H_INCLUDED__ 

#include <iostream>

#define uint unsigned int

class Vec2d {
   public: 
      double x,y;

      Vec2d() : x(0.0), y(0.0) {}
      Vec2d(double x,double y) : x(x), y(y) {}

      bool operator==(const Vec2d& other) const;

      Vec2d operator -() const;

      Vec2d operator +(const Vec2d& other) const;
      Vec2d operator -(const Vec2d& other) const;
      Vec2d operator *(const double factor) const;
      Vec2d operator /(const double factor) const;

      void operator +=(const Vec2d& other);
      void operator -=(const Vec2d& other);
      void operator *=(const double factor);
      void operator /=(const double factor);

      Vec2d rotate(const double angle) const;
      Vec2d normalise() const;

      double dot(const Vec2d& other) const;
      double dot(const double other_x, const double other_y) const;
      
      double cross(const Vec2d& other) const;
      double length2() const;
      double length() const;
};

class Vec3d {
   public:
      double x,y,z;

      Vec3d(double x, double y, double z) : x(x), y(y), z(z) {}

      double dot(const Vec3d& other) const;
};

class Vec6d {
   public:
      double a,b,c,d,e,f;

      Vec6d() : a(0), b(0), c(0), d(0), e(0), f(0) {}
      Vec6d(double a, double b, double c, double d, double e, double f) : a(a), b(b), c(c), d(d), e(e), f(f) {}

      Vec6d operator +(const Vec6d& other) const;
      Vec6d operator -(const Vec6d& other) const;
      Vec6d operator *(const double factor) const;
      Vec6d operator /(const double factor) const;

      double dot(const Vec6d& other) const;
      Vec6d componentMultiply(const Vec6d& other) const;
};

std::ostream & operator<<(std::ostream & Str, const Vec2d& v);

struct mat2x2 {
   public:
      double a,b,c,d;

      mat2x2 invert() const;
      Vec2d solve(const Vec2d& input) const;
      Vec2d solve(const double x, const double y) const;

      Vec2d apply(const Vec2d& input) const;
      Vec2d apply(double x, double y) const;
      Vec2d applyT(const Vec2d& input) const;
      Vec2d applyT(const double x, const double y) const;
};

class mat3x3 {
   public:
      double a,b,c,d,e,f,g,h,i;

      mat3x3 invert() const;
      Vec3d apply(const Vec3d& input) const;
      Vec3d apply(const double x, const double y, const double z) const;
};

mat2x2 const genRotationMat(double angle);

const Vec2d ORIGIN = Vec2d(0, 0);
#endif