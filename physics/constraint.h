#pragma once

#include "vector.h"
#include "objects.h"

inline void set_velocity(Object& a, Object& b, const Vec6& vec) {
    a.vel.x = vec[0];
    a.vel.y = vec[1];
    a.rotV  = vec[2];
    b.vel.x = vec[3];
    b.vel.y = vec[4];
    b.rotV  = vec[5];
}

inline Vec6 get_velocity_vector(const Object& a, const Object& b) {
    return Vec6(
        a.vel.x, 
        a.vel.y, 
        a.rotV, 
        b.vel.x, 
        b.vel.y, 
        b.rotV
    );
}

inline Vec6 get_inverse_mass_matrix(const Object& a, const Object& b) {
    return Vec6(
        a.getInvMass(), 
        a.getInvMass(), 
        a.getInvMoment(),
        b.getInvMass(), 
        b.getInvMass(),
        b.getInvMoment()
    );
}

inline float_type compute_inverse_effective_mass(const Vec6& J, const Vec6& M) {
    return ((float_type)1) / J.dot(M * J);
}

inline mat2x2 compute_inverse_effective_mass(const std::array<Vec6, 2>& J, const Vec6& M) {
    std::array<Vec6, 2> MJ = {
        M * J[0],
        M * J[1],
    }; // List of columns
    
    mat2x2 JMJ = {
        J[0].dot(MJ[0]),  
        J[0].dot(MJ[1]),  
        J[1].dot(MJ[0]),  
        J[1].dot(MJ[1]),  
    };
    return JMJ.invert();
}

inline mat3x3 compute_inverse_effective_mass(const std::array<Vec6, 3>& J, const Vec6& M) {
    std::array<Vec6, 3> MJ = {
        M * J[0],
        M * J[1],
        M * J[2],
    }; // List of columns
    
    mat3x3 JMJ = {
        J[0].dot(MJ[0]),  
        J[0].dot(MJ[1]),  
        J[0].dot(MJ[2]),   
        J[1].dot(MJ[0]),  
        J[1].dot(MJ[1]),  
        J[1].dot(MJ[2]), 
        J[2].dot(MJ[0]),  
        J[2].dot(MJ[1]),  
        J[2].dot(MJ[2]), 
    };
    return JMJ.invert();
}

inline float_type resolve_constraint(const Vec6& J, const Vec6& M, const Vec6& V, const float_type bias) {
    return compute_inverse_effective_mass(J, M) * -(bias + J.dot(V));
}

inline Vec2 resolve_constraint(const std::array<Vec6, 2>& J, const Vec6& M, const Vec6& V, const Vec2& bias) {
    return compute_inverse_effective_mass(J, M) * -(bias + Vec2(J[0].dot(V), J[1].dot(V)));
}

inline Vec3 resolve_constraint(const std::array<Vec6, 3>& J, const Vec6& M, const Vec6& V, const Vec3& bias) {
    return compute_inverse_effective_mass(J, M) * -(bias + Vec3(J[0].dot(V), J[1].dot(V), J[2].dot(V)));
}

inline Vec6 apply_constraint(const Vec6& J, const Vec6& M, float_type lambda) {
    return M * (J * lambda);
}

inline Vec6 apply_constraint(const std::array<Vec6, 2>& J, const Vec6& M, const Vec2& lambda) {
    return M * (J[0]*lambda.x + J[1]*lambda.y);
}

inline Vec6 apply_constraint(const std::array<Vec6, 3>& J, const Vec6& M, const Vec3& lambda) {
    return M * (J[0]*lambda.x + J[1]*lambda.y + J[2]*lambda.z);
}
