#pragma once

#include <iostream>
#include <cmath>

typedef unsigned int uint;
typedef float float_type;

class Vec2 {
   public: 
      union {
         struct {float_type x, y; };
         float_type v[2];
      };

      constexpr Vec2() : x(0.0), y(0.0) {}
      constexpr Vec2(float_type x, float_type y) : x(x), y(y) {}

      bool constexpr operator==(const Vec2& other) const {
         return x == other.x && y == other.y;
      }

      bool constexpr operator!=(const Vec2& other) const {
         return x != other.x || y != other.y;
      }

      Vec2 constexpr operator-() const {
         return Vec2(-x,-y);
      }

      Vec2 constexpr operator+(const Vec2& other) const {
         return Vec2(x+other.x, y+other.y);
      }

      Vec2 constexpr operator-(const Vec2& other) const {
         return Vec2(x-other.x, y-other.y);
      }

      Vec2 constexpr operator*(const float_type factor) const {
         return Vec2(x*factor, y*factor);
      }

      Vec2 constexpr operator/(const float_type factor) const {
         return Vec2(x/factor, y/factor);
      }

      void constexpr operator+=(const Vec2& other) {
         x += other.x;
         y += other.y;
      }
      void constexpr operator-=(const Vec2& other) {
         x -= other.x;
         y -= other.y;
      }
      void constexpr operator*=(const float_type factor) {
         x *= factor;
         y *= factor;
      }

      void constexpr operator/=(const float_type factor) {
         x /= factor;
         y /= factor;
      }

      Vec2 constexpr rotate(const float_type angle) const {
         float_type s = sin(angle);
         float_type c = cos(angle);
         return Vec2(x*c - y*s, x*s + y*c);
      }

      Vec2 constexpr normalise() const {
         return (*this) / this->length();
      }

      float_type constexpr dot(const Vec2& other) const {
         return x*other.x + y*other.y;
      }

      float_type constexpr dot(const float_type other_x, const float_type other_y) const {
         return x*other_x + y*other_y;
      }
      
      float_type constexpr cross(const Vec2& other) const {
         return x*other.y - y*other.x;
      }

      float_type constexpr length2() const {
         return x*x + y*y;
      }

      float_type constexpr length() const {
         return sqrt(x*x + y*y);
      }
};

class Vec3 {
   public:
      union {
         struct { float_type x,y,z; };
         float_type v[3];
      };

      constexpr Vec3(float_type x, float_type y, float_type z) : x(x), y(y), z(z) {}

      float_type constexpr dot(const Vec3& other) const {
         return x*other.x + y*other.y + z*other.z;
      }
};

class Vec6 {
   public:
      union {
         struct { float_type a,b,c,d,e,f; };
         float_type v[6];
      };
      

      constexpr Vec6() : a(0), b(0), c(0), d(0), e(0), f(0) {}
      constexpr Vec6(float_type a, float_type b, float_type c, float_type d, float_type e, float_type f) : a(a), b(b), c(c), d(d), e(e), f(f) {}

      Vec6 constexpr operator +(const Vec6& other) const {
         return Vec6(a+other.a,b+other.b,c+other.c,d+other.d,e+other.e,f+other.f);
      }
      Vec6 constexpr operator -(const Vec6& other) const {
         return Vec6(a-other.a,b-other.b,c-other.c,d-other.d,e-other.e,f-other.f);
      }
      Vec6 constexpr operator *(const float_type factor) const {
         return Vec6(a*factor,b*factor,c*factor,d*factor,e*factor,f*factor);
      }
      Vec6 constexpr operator /(const float_type factor) const {
         return Vec6(a/factor,b/factor,c/factor,d/factor,e/factor,f/factor);
      }

      float_type constexpr dot(const Vec6& other) const {
         return a*other.a + b*other.b + c*other.c + d*other.d + e*other.e + f*other.f;
      }

      Vec6 constexpr componentMultiply(const Vec6& other) const {
         return Vec6(a*other.a,b*other.b,c*other.c,d*other.d,e*other.e,f*other.f);
      }
};

struct mat2x2 {
   public:
      float_type a,b,c,d;

      mat2x2 constexpr invert() const {
         const float_type det = a*d - b*c;
         return mat2x2 {d/det,-b/det,-c/det,a/det};
      }

      Vec2 constexpr solve(const Vec2& vec) const {
         return Vec2(d*vec.x - b*vec.y, a*vec.y - c*vec.x) / (a*d - b*c);
      }

      Vec2 constexpr solve(const float_type x, const float_type y) const {
         return Vec2(d*x - b*y, a*y - c*x) / (a*d - b*c);
      }

      Vec2 constexpr apply(const Vec2& vec) const {
         return Vec2(a*vec.x + b * vec.y, c*vec.x + d*vec.y);
      }
      Vec2 constexpr apply(const float_type x, const float_type y) const {
         return Vec2(a*x + b*y, c*x + d*y);
      }

      Vec2 constexpr applyT(const Vec2& vec) const {
         return Vec2(a*vec.x + c * vec.y, b*vec.x + d*vec.y);
      }
      Vec2 constexpr applyT(const float_type x, const float_type y) const {
         return Vec2(a*x + c*y, b*x + d*y);
      }
};

class mat3x3 {
   public:
      float_type a,b,c,d,e,f,g,h,i;

      mat3x3 constexpr invert() const {
         float_type A = +(e*i - f*h);
         float_type B = -(d*i - f*g);
         float_type C = +(d*h - e*g);
         float_type D = -(b*i - c*h);
         float_type E = +(a*i - c*g);
         float_type F = -(a*h - b*g);
         float_type G = +(b*f - c*e);
         float_type H = -(a*f - c*d);
         float_type I = +(a*e - b*d);

         float_type det = a*A + b*B + c*C;

         return mat3x3 {A/det, D/det, G/det, B/det, E/det, H/det, C/det, F/det, I/det};
      }

      Vec3 constexpr apply(const Vec3& vec) const {
         return Vec3(a*vec.x + b*vec.y + c*vec.z,
                     d*vec.x + e*vec.y + f*vec.z,
                     g*vec.x + h*vec.y + i*vec.z);
      }
      Vec3 constexpr apply(const float_type x, const float_type y, const float_type z) const {
         return Vec3(a*x + b*y + c*z,
                     d*x + e*y + f*z,
                     g*x + h*y + i*z);
      }
};

inline std::ostream & operator<<(std::ostream & Str, const Vec2& v) { 
  return Str << "[" << v.x << "," << v.y << "]";
}

inline std::ostream & operator<<(std::ostream & Str, const Vec3& v) { 
  return Str << "[" << v.x << "," << v.y << "," << v.z << "]";
}

inline mat2x2 const genRotationMat(const float_type angle) {
   mat2x2 mat;
   mat.a = mat.d = cos(angle);
   mat.c = sin(angle);
   mat.b = -mat.c;
   return mat;
}

const Vec2 ORIGIN = Vec2(0, 0);