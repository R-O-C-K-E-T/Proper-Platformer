#pragma once

#include <iostream>
#include <cmath>

typedef unsigned int uint;
typedef float float_type;

struct Vec2 {
   float_type x,y;
   constexpr Vec2(float_type x, float_type y) : x(x), y(y) {}
   constexpr Vec2(float_type v): Vec2(v,v) {}
   constexpr Vec2(): Vec2((float_type)0) {}

   #define SIMPLE_OP(OP) Vec2 constexpr operator OP (const Vec2& other) const {\
      return Vec2(x OP other.x, y OP other.y);\
   }\
   Vec2 constexpr operator OP (const float_type factor) const {\
      return Vec2(x OP factor, y OP factor);\
   }\
   friend Vec2 constexpr operator OP (const float_type factor, const Vec2& val) {\
      return Vec2(factor OP val.x, factor OP val.y);\
   }\
   void constexpr operator OP##= (const Vec2& val) {\
      x OP##= val.x;\
      y OP##= val.y;\
   }\
   void constexpr operator OP##= (const float factor) {\
      x OP##= factor;\
      y OP##= factor;\
   }

   SIMPLE_OP(+)
   SIMPLE_OP(-)
   SIMPLE_OP(*)
   SIMPLE_OP(/)

   #undef SIMPLE_OP

   constexpr bool operator==(const Vec2& val) {
      return x == val.x && y == val.y;
   }

   constexpr bool operator!=(const Vec2& val) {
      return !(*this == val);
   }

   constexpr Vec2 operator-() const {
      return Vec2(-x,-y);
   }

   constexpr float_type length2() const {
      return x*x + y*y;
   }

   float_type length() const {
      return std::sqrt(length2());
   }

   Vec2 normalised() const {
      return *this * (((float_type)1) / length());
   }

   constexpr float_type dot(float_type other_x, float_type other_y) const {
      return x * other_x + y * other_y;
   }

   constexpr float_type dot(const Vec2& other) const {
      return x*other.x + y*other.y;
   }
      
   constexpr float_type cross(const Vec2& other) const {
      return x*other.y - y*other.x;
   }

   constexpr float_type operator[](size_t i) const {
      switch (i) {
      case 0:
         return x;
      case 1:
         return y;
      default:
         std::abort();
         return (float_type)0;
      }
   }

   constexpr float_type&  operator[](size_t i) {
      switch (i) {
      case 0:
         return x;
      case 1:
         return y;
      default:
         std::abort();
         return x;
      }
   }
};

struct Vec3 {
   float_type x,y,z;
   constexpr Vec3(float_type x, float_type y, float_type z) : x(x), y(y), z(z) {}
   constexpr Vec3(float_type v): Vec3(v,v,v) {}
   constexpr Vec3(): Vec3((float_type)0) {}

   #define SIMPLE_OP(OP) Vec3 constexpr operator OP (const Vec3& other) const {\
      return Vec3(x OP other.x, y OP other.y, z OP other.z);\
   }\
   Vec3 constexpr operator OP (const float_type factor) const {\
      return Vec3(x OP factor, y OP factor, z OP factor);\
   }\
   friend Vec3 constexpr operator OP (const float_type factor, const Vec3& val) {\
      return Vec3(factor OP val.x, factor OP val.y, factor OP val.z);\
   }\
   void constexpr operator OP##= (const Vec3& val) {\
      x OP##= val.x;\
      y OP##= val.y;\
      z OP##= val.z;\
   }\
   void constexpr operator OP##= (const float factor) {\
      x OP##= factor;\
      y OP##= factor;\
      z OP##= factor;\
   }

   SIMPLE_OP(+)
   SIMPLE_OP(-)
   SIMPLE_OP(*)
   SIMPLE_OP(/)

   #undef SIMPLE_OP

   constexpr bool operator==(const Vec3& val) {
      return x == val.x && y == val.y && z == val.z;
   }

   constexpr bool operator!=(const Vec3& val) {
      return !(*this == val);
   }

   Vec3 constexpr operator-() const {
      return Vec3(-x,-y,-z);
   }

   float_type constexpr length2() const {
      return x*x + y*y + z*z;
   }

   float_type length() const {
      return std::sqrt(length2());
   }

   Vec3 normalised() const {
      return *this * (((float_type)1) / length());
   }

   float_type constexpr dot(const Vec3& other) const {
      return x*other.x + y*other.y + z*other.z;
   }

   constexpr float_type operator[](size_t i) const {
      switch (i) {
      case 0:
         return x;
      case 1:
         return y;
      case 2:
         return z;
      default:
         std::abort();
         return (float_type)0;
      }
   }

   constexpr float_type&  operator[](size_t i) {
      switch (i) {
      case 0:
         return x;
      case 1:
         return y;
      case 2:
         return z;
      default:
         std::abort();
         return x;
      }
   }
};

struct Vec6 {
   float_type a, b, c, d, e, f;

   explicit constexpr Vec6() : Vec6((float_type)0) {}
   explicit constexpr Vec6(float_type v): Vec6(v,v,v,v,v,v) {}
   explicit constexpr Vec6(float_type a, float_type b, float_type c, float_type d, float_type e, float_type f) : a(a), b(b), c(c), d(d), e(e), f(f) {}

   #define SIMPLE_OP(OP) Vec6 constexpr operator OP (const Vec6& other) const {\
      auto result = Vec6();\
      for (size_t i=0; i<6; i++) result[i] = (*this)[i] OP other[i];\
      return result;\
   }\
   constexpr Vec6 operator OP (const float factor) const {\
      auto result = Vec6();\
      for (size_t i=0; i<6; i++) result[i] = (*this)[i] OP factor;\
      return result;\
   }\
   friend constexpr Vec6 operator OP (const float factor, const Vec6& val) {\
      auto result = Vec6();\
      for (size_t i=0; i<6; i++) result[i] = factor OP val[i];\
      return result;\
   }\
   constexpr void operator OP##= (const Vec6& val) {\
      for (size_t i=0; i<6; i++) (*this)[i] OP##= val[i];\
   }\
   constexpr void operator OP##= (const float factor) {\
      for (size_t i=0; i<6; i++) (*this)[i] OP##= factor;\
   }

   SIMPLE_OP(+)
   SIMPLE_OP(-)
   SIMPLE_OP(*)
   SIMPLE_OP(/)

   #undef SIMPLE_OP

   constexpr Vec6 component_multiply(const Vec6& other) const {
      Vec6 result;
      for (size_t i=0; i<6; i++) {
         result[i] = (*this)[i] + other[i];
      }
      return result;
   }

   constexpr bool operator==(const Vec6& val) {
      for (size_t i=0; i<6; i++) {
         if ((*this)[i] != val[i]) return false;
      }
      return true;
   }

   constexpr bool operator!=(const Vec6& val) {
      return !(*this == val);
   }

   constexpr Vec6 operator-() const {
      auto result = Vec6();
      for (size_t i=0; i<6; i++) result[i] = -(*this)[i];
      return result;
   }

   constexpr float_type length2() const {
      float result = (float_type)0;
      for (size_t i = 0; i<6; i++) result += (*this)[i] * (*this)[i];
      return result;
   }

   float_type length() const {
      return std::sqrt(length2());
   }

   Vec6 normalised() const {
      return *this * (((float_type)1) / length());
   }

   constexpr float_type dot(const Vec6& other) const {
      float_type result = (float_type)0;
      for (size_t i=0; i<6; i++) result += (*this)[i] * other[i];
      return result;
   }

   constexpr float_type operator[](size_t i) const {
      switch (i) {
      case 0:
         return a;
      case 1:
         return b;
      case 2:
         return c;
      case 3:
         return d;
      case 4:
         return e;
      case 5:
         return f;
      default:
         std::abort();
         return (float_type)0;
      }
   }

   constexpr float_type&  operator[](size_t i) {
      switch (i) {
      case 0:
         return a;
      case 1:
         return b;
      case 2:
         return c;
      case 3:
         return d;
      case 4:
         return e;
      case 5:
         return f;
      default:
         std::abort();
         return a;
      }
   }
};

struct mat2x2 {
   public:
      float_type a,b,c,d;

      float_type constexpr det() const {
         return a*d - b*c;
         // return (a - c)*b - c*(d - b);
      }

      mat2x2 constexpr invert() const {
         float_type m_det = det();
         return mat2x2 {d/m_det,-b/m_det,-c/m_det,a/m_det};
      }

      // Vec2 constexpr precise_solve(const Vec2& b) const {
      //    Vec2 x = solve(b);

      //    Vec2 db = apply(x) - b;
      //    Vec2 dx = solve(db);

      //    return x - dx;
      // }

      Vec2 constexpr solve(const float_type x, const float_type y) const {
         if (std::abs(a) < std::abs(c)) {
            mat2x2 temp = {c, d, a, b};
            return temp.solve(y, x);
         }

         float_type alpha = c / a;
         float_type beta = d - b * alpha;
         if (beta == (float_type)0) {
            return Vec2(); // FAILED
         }
         float_type gamma = y - x * alpha;
         float_type res_y = gamma / beta;
         return Vec2((x - b * res_y) / a, res_y);   
      }

      Vec2 constexpr solve(const Vec2& vec) const {
         return solve(vec.x, vec.y);
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

inline constexpr Vec2 operator*(const mat2x2& mat, const Vec2& vec) {
   return mat.apply(vec);
}

inline constexpr Vec2 operator*(const Vec2& vec, const mat2x2& mat) {
   return mat.applyT(vec);
}

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

inline constexpr Vec3 operator*(const mat3x3& mat, const Vec3& vec) {
   return mat.apply(vec);
}

inline std::ostream& operator<<(std::ostream & str, const Vec2& v) { 
  return str << "[" << v.x << "," << v.y << "]";
}

inline std::ostream& operator<<(std::ostream & str, const Vec3& v) { 
  return str << "[" << v.x << "," << v.y << "," << v.z << "]";
}

inline std::ostream& operator<<(std::ostream & str, const Vec6& v) { 
  return str << "[" << v.a << "," << v.b << "," << v.c << "," << v.d << "," << v.e << "," << v.f << "]";
}


inline std::ostream& operator<<(std::ostream & str, const mat2x2& m) { 
  return str << "[[" << m.a << "," << m.b << "],[" << m.c << "," << m.d << "]]";
}

inline mat2x2 const genRotationMat(const float_type angle) {
   mat2x2 mat;
   mat.a = mat.d = cos(angle);
   mat.c = sin(angle);
   mat.b = -mat.c;
   return mat;
}

const Vec2 ORIGIN = Vec2(0, 0);