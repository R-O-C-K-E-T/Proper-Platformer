#include "sph.h"

#include <algorithm>

float_type kernel(const Vec2& vec) {
    return kernel(vec.length());   
}

const constexpr float_type kernelGradLookup[] = {
    -21.826963296626904, -21.699071259046804, -21.571178894062243, -21.44328652907768, -21.315394164093124, -21.187501799108567, -21.059609434124006, -20.93171706913945, -20.80382470415489, -20.67593233917033, -20.548039974185777, -20.420147609201216, -20.292255244216655, -20.164362879232097, -20.036470514247537, -19.908578149262983, -19.780685784278422, -19.65279341929386, -19.5249010543093, -19.397008689324746, -19.269116324340185, -19.141223959355628, -19.013331594371067, -18.88543922938651, -18.75754686440195, -18.62965449941739, -18.50176213443283, -18.373869769448277, -18.24597740446372, -18.11808503947916, -17.9901926744946, -17.86230030951004, -17.73440794452548, -17.606515579540922, -17.47862321455636, -17.350730849571804, -17.222838484587246, -17.094946119602685, -16.96705375461813, -16.83916138963357, -16.71126902464901, -16.583376659664452, -16.455484294679895, -16.327591929695334, -16.199699564710777, -16.071807199726216, -15.943914834741658, -15.8160224697571, -15.68813010477254, -15.56023773978798, -15.432345374803422, -15.304453009818863, -15.176560644834305, -15.048668279849744, -14.92077591486519, -14.792883549880631, -14.66499118489607, -14.537098819911513, -14.409206454926954, -14.281314089942397, -14.153421724957836, -14.025529359973277, -13.897636994988718, -13.76974463000416, -13.641852265019601, -13.513959900035042, -13.386067535050483, -13.258175170065924, -13.130282805081364, -13.002390440096805, -12.874498075112248, -12.746605710127689, -12.61871334514313, -12.49082098015857, -12.362928615174013, -12.235036250189456, -12.107143885204897, -11.979251520220338, -11.851359155235778, -11.72346679025122, -11.59557442526666, -11.467682060282103, -11.339789695297544, -11.211897330312985, -11.084004965328425, -10.956112600343866, -10.828220235359309, -10.700327870374748, -10.57243550539019, -10.444543140405631, -10.316650775421072, -10.188758410436513, -10.060866045451956, -9.932973680467397, -9.805081315482838, -9.67718895049828, -9.549296585513721, -9.421404220529162, -9.293511855544601, -9.165619490560044, -9.037727125575485, -8.909834760590927, -8.781942395606368, -8.654050030621809, -8.52615766563725, -8.398265300652692, -8.270372935668131, -8.142480570683574, -8.014588205699015, -7.886695840714456, -7.7588034757298985, -7.630911110745339, -7.503018745760781, -7.375126380776221, -7.247234015791663, -7.119341650807104, -6.991449285822546, -6.863556920837986, -6.735664555853428, -6.607772190868869, -6.479879825884311, -6.351987460899751, -6.224095095915193, -6.096202730930634, -5.968310365946076, -5.840418000961516, -5.712525635976958, -5.5846332709923985, -5.45674090600784, -5.330170425932683, -5.2062030422945, -5.084779142197788, -4.965840919198422, -4.849332305391953, -4.735198906542718, -4.62338794009611, -4.513848175925603, -4.4065298796747845, -4.301384758562793, -4.198365909529077, -4.097427769600531, -3.9985260683706607, -3.9016177824866793, -3.8066610920462254, -3.7136153388108912, -3.6224409861488467, -3.5330995806236554, -3.44555371515089, -3.359766993648408, -3.2757039971100967, -3.1933302510366715, -3.1126121941606186, -3.033517148405674, -2.9560132900243654, -2.880069621860063, -2.805655946682761, -2.732742841550401, -2.661301633150022, -2.5913043740753214, -2.522723819999399, -2.455533407703528, -2.3897072339247263, -2.3252200349867516, -2.2620471671808766, -2.2001645878644416, -2.1395488372467293, -2.0801770208331845, -2.022026792500379, -1.9650763381754424, -1.9093043600949213, -1.854690061619209, -1.801213132579799, -1.7488537351376872, -1.697592490132226, -1.6474104639007146, -1.5982891555498857, -1.550210484661318, -1.5031567794136182, -1.4571107651049728, -1.4120555530604262, -1.36797462990891, -1.324851847215733, -1.2826714114568567, -1.2414178743218827, -1.2010761233332474, -1.161631372769659, -1.123069154882326, -1.08537531139302, -1.0485359852634746, -1.0125376127260746, -0.9773669155662069, -0.9430108936470518, -0.9094568176679734, -0.8766922221480374, -0.8447048986265357, -0.8134828890727233, -0.7830144794972985, -0.7532881937584586, -0.7242927875556493, -0.6960172426044077, -0.6684507609859603, -0.6415827596654897, -0.6154028651732233, -0.5899009084427349, -0.5650669198010569, -0.5408911241054265, -0.5173639360216779, -0.4944759554394937, -0.4722179630199092, -0.4505809158706385, -0.4295559433449624, -0.4091343429600813, -0.38930757643098385, -0.3700672658160394, -0.35140518977065677, -0.3333132799054934, -0.31578361724582404, -0.29880842878880776, -0.2823800841555089, -0.26649109233464374, -0.2511340985151336, -0.23630188100465233, -0.22198734823145636, -0.20818353582688265, -0.19488360378599429, -0.18208083370394215, -0.16976862608569745, -0.1579404977268927, -0.1465900791635878, -0.13571111218885493, -0.12529744743414742, -0.11534304201349095, -0.10584195722860035, -0.09678835633309239, -0.08817650235402626, -0.08000075596906442, -0.07225557343760382, -0.0649355045842837, -0.058035190833329184, -0.051549363292241954, -0.04547284088339867, -0.03980052852216559, -0.03452741534018391, -0.029648572952524592, -0.02515915376745418, -0.021054389337594025, -0.017329588751295224, -0.01398013706308942, -0.01100149376211258, -0.008389191277434241, -0.00613883351925882, -0.0042460944549986305, -0.0027067167192499205, -0.0015165102567338982, -0.0006713509972942717, -0.00016717956207131863
};

inline constexpr float_type kernelGradSize(const float_type dist) {
    if (dist < 0.5) {
        return coefficient * 6*dist*(3*dist - 2);
    } else if (dist < 1) {
        return coefficient * -6*(1-dist)*(1-dist);
    } else {
        return 0;
    }
}

/*inline constexpr Vec2 kernelGrad(const Vec2& vec) {
    float_type dist = vec.length();
    if (dist == 0) return ORIGIN;

    float_type dw = kernelGradSize(dist); // dw/dr
    return vec * (dw / dist); // (dr/dx, dr/dy)*(dw/dr)
}*/

inline Vec2 unsafeKernelGrad(const Vec2& vec) {
    int dist = vec.length() * 256;
    return vec * kernelGradLookup[dist];
}

inline Vec2 kernelGrad(const Vec2& vec) {
    int dist = vec.length() * 256;
    if (dist >= 256) return ORIGIN;

    return vec * kernelGradLookup[dist];
}

uint16_t mapToZCurve(uint8_t x, uint8_t y) {
    return (lookup[y] << 1) | lookup[x];
}

template<class T>
void NeighbourhoodSolver<T>::addParticle(T particle) {
    particles.push_back(particle);
    handles.push_back({0, (uint32_t)(particles.size() - 1)});
}

template<class T>
void NeighbourhoodSolver<T>::update() {
    for (auto& handle : handles) {
        T& particle = particles[handle.particle];

        particle.neighbours.clear();

        Vec2 pos = particle.pos;
        handle.cell = mapToZCurve(pos.x, pos.y);
    }


    // Orders the handles based on Z-curve order
    std::sort(handles.begin(), handles.end(), [](const handlePair& a, const handlePair& b) {
        return a.cell < b.cell;
    });


    // Update block such that each block cell contains a reference to the first particle
    if (handles.size()) {
        uint16_t prevCell = handles[0].cell;
        block[prevCell] = 0;

        for (size_t i = 1; i<handles.size(); i++) {
            uint16_t cell = handles[i].cell;

            if (cell != prevCell) {
                block[cell] = i;
                prevCell = cell;
            }
        }
    }


    //size_t size = 0;
    for (auto& handle : handles) {
        const uint16_t cell = handle.cell;
        T& particle = particles[handle.particle];

        for (uint8_t i = -1; i!=2; i++) {
            for (uint8_t j = -1; j!=2; j++) {
                uint16_t otherCell = (((cell | 0xAAAA) + (lookup[i] << 0)) & 0x5555) | 
                                        (((cell | 0x5555) + (lookup[j] << 1)) & 0xAAAA);

                uint32_t reference = block[otherCell];
                while (reference < handles.size() && handles[reference].cell == otherCell) {
                    T& other = particles[handles[reference].particle];
                    
                    if (&particle > &other) {
                        float_type dist2 = (particle.pos - other.pos).length2();
                        if (dist2 != 0 && dist2 < 1) {
                            particle.neighbours.push_back(&other);
                            
                            //size++;
                        }
                    }
                    reference++;
                };
            }
        }
    }
}

template<class T>
template<class U>
void NeighbourhoodSolver<T>::crossNeighbours(NeighbourhoodSolver<U>& other) {
    for (auto& handle : handles) {
        const uint16_t cell = handle.cell;
        T& particle = particles[handle.particle];

        particle.neighbours.clear();

        for (uint8_t i = -1; i!=2; i++) {
            for (uint8_t j = -1; j!=2; j++) {
                uint16_t otherCell = (((cell | 0xAAAA) + (lookup[i] << 0)) & 0x5555) | 
                                        (((cell | 0x5555) + (lookup[j] << 1)) & 0xAAAA);

                uint32_t reference = other.block[otherCell];
                while (reference < other.handles.size() && other.handles[reference].cell == otherCell) {
                    U& otherParticle = other.particles[other.handles[reference].particle];

                    float_type dist2 = (particle.pos - otherParticle.pos).length2();
                    if (dist2 != 0 && dist2 < 1) {
                        particle.neighbours.push_back(&otherParticle);
                    }
                    reference++;
                };
            }
        }
    }
}

void SPHSolver::updateRigidParticleVelocities() {
    for (auto& particle : rigid.getParticles()) {
        Vec2 offset = particle.object.localToGlobalVec(particle.localPosition);
        particle.vel = (Vec2(-offset.y, offset.x) * particle.object.rotV + particle.object.vel) * scaleFactor;
    }
}

/*template<class T>
void NeighbourhoodSolver<T>::reorder() {
    for (uint32_t i = 0; i<particles.size(); i++) {
        uint32_t location = handles[i].particle;

        std::swap(particles[i], particles[location]);
        handles[i].particle = i;
        handles[location].particle = location;
    }


    // Add neighbours to fluid particles
    size_t size = 0;
    size_t count = 0;
    for (auto& handle : handles) {
        const uint16_t cell = handle.cell;
        Particle& particle = particles[handle.particle];
        particle.neighbours.clear();

        count++;

        for (uint8_t i = -1; i!=2; i++) {
            for (uint8_t j = -1; j!=2; j++) {
                uint16_t otherCell = (((cell | 0xAAAA) + (lookup[i] << 0)) & 0x5555) | 
                                        (((cell | 0x5555) + (lookup[j] << 1)) & 0xAAAA);

                uint32_t reference = block[otherCell];
                while (reference < handle.particle && handles[reference].cell == otherCell) {
                    Particle& other = particles[handles[reference].particle];
                    
                    float_type dist2 = (particle.pos - other.pos).length2();
                    if (dist2 != 0 && dist2 < 1) {
                        particle.neighbours.push_back(&other);
                            
                        size++;
                    }

                    reference++;
                };
            }
        }
    }
}*/

void SPHSolver::fixParticles() {
    for (auto& particle : rigid.getParticles()) {
        Vec2 offset = particle.object.localToGlobalVec(particle.localPosition);

        particle.pos = (offset + particle.object.pos) * scaleFactor;
        particle.vel = (Vec2(-offset.y, offset.x) * particle.object.rotV + particle.object.vel) * scaleFactor;
    }

    fluid.update();
    rigid.update();
    

    // Compute rigid masses based on the volume
    for (auto& particle : rigid.getParticles()) {
        particle.volume = kernel(0.0);

        for (BaseParticle* other : particle.neighbours) {
            float_type influence = kernel(other->pos - particle.pos);
            particle.volume += influence;
            other->volume += influence;
        }
    }
    rigid.crossNeighbours(fluid);

    for (auto& particle : fluid.getParticles()) {
        // Particle normal and alpha are being used as scratch variables

        particle.volume = kernel(0); // Self volume

        particle.alpha = 0;
        particle.normal = ORIGIN;


        for (BaseParticle* other : particle.neighbours) {
            Vec2 delta = other->pos - particle.pos;

            float_type influence = kernel(delta);
            particle.volume += influence;
            other->volume += influence;

            Vec2 grad = unsafeKernelGrad(delta);

            particle.normal += grad;
            other->normal -= grad;

            float_type length2 = grad.length2(); 
            particle.alpha += length2;
            other->alpha += length2;
        }
    }

    for (auto& particle : rigid.getParticles()) {
        particle.alpha = targetNeighbourhoodVolume / particle.volume;

        for (BaseParticle* other : particle.neighbours) {
            // Reverse is used
            Vec2 delta = particle.pos - other->pos;

            other->volume += kernel(delta) * particle.alpha;

            Vec2 grad = unsafeKernelGrad(delta);
            other->normal += grad;
            other->alpha += grad.length2();
        }
    }

    for (auto& particle : fluid.getParticles()) {
        // Real value set
        particle.alpha = particle.volume / std::max(particle.normal.length2() + particle.alpha, (float_type)1e-6);
    }
}

void SPHSolver::applySeparationImpulse(RigidParticle& rigid, Particle& fluid, float_type separationFactor) {
    Vec2 grad = unsafeKernelGrad(fluid.pos - rigid.pos);

    Vec2 normal = grad.normalised();
    Vec2 offset = rigid.object.localToGlobalVec(rigid.localPosition);

    Vec2 impulse = grad * (separationFactor / 
        ((rigid.object.getInvMass() + rigid.object.getInvMoment()*scaleFactor2 * normal.cross(offset) * normal.cross(offset)) * invMassConversionFactor + fluid.invMass));
    
    rigid.object.applyImpulse(impulse * massConversionFactor, rigid.pos * invScaleFactor);
    fluid.vel -= impulse * fluid.invMass;
}

void SPHSolver::applySeparationImpulse(Particle& fluidA, Particle& fluidB, float_type separationFactor) {
    Vec2 impulse = unsafeKernelGrad(fluidA.pos - fluidB.pos) * (separationFactor / (fluidA.invMass + fluidB.invMass));

    fluidA.vel -= impulse * fluidA.invMass;
    fluidB.vel += impulse * fluidB.invMass;
}


void SPHSolver::updateVolumeDerivative() {
    for (auto& particle : fluid.getParticles()) {
        particle.volumeDerivative = 0;

        for (BaseParticle* other : particle.neighbours) {
            float_type derivative = (particle.vel - other->vel).dot(unsafeKernelGrad(particle.pos - other->pos));

            particle.volumeDerivative += derivative;
            other->volumeDerivative += derivative;
        }
    }

    for (auto& particle : rigid.getParticles()) {
        for (BaseParticle* other : particle.neighbours) {
            other->volumeDerivative += (other->vel - particle.vel).dot(unsafeKernelGrad(other->pos - particle.pos));
        }
    }
}

void SPHSolver::applyNonPressureForces(float_type timeStep) {
    // Compute particle normals
    for (auto& particle : fluid.getParticles()) {
        // Given that neighbours come before the given particle in memory 
        // then we can merge resetting particle.normal and calculating particle.normal into one loop.
        particle.normal = ORIGIN;

        for (BaseParticle* other : particle.neighbours) {
            Vec2 grad = unsafeKernelGrad(particle.pos - other->pos);
            particle.normal += grad / particle.volume;
            other->normal -= grad / other->volume;
        }
    }

    
    for (auto& particle : fluid.getParticles()) {
        // Add viscous and surface tension forces

        //particle.vel += gravity * timeStep;

        for (BaseParticle* other : particle.neighbours) {
            Vec2 delta = particle.pos - other->pos;
            float_type dist = delta.length();

            // Viscosity
            Vec2 force = (particle.vel - other->vel) * ((2 * viscosity * kernelGradSize(dist)) / (other->volume * dist));


            // Surface tension
            Vec2 surfaceTensionForce = (other->normal - particle.normal);
            
            float_type inverse = 1 - dist;
            float_type cohesion;
            if (dist < 0.5) {
                cohesion = (2*inverse*inverse*inverse * dist*dist*dist - 1.0/64.0) / dist;
            } else if (dist < 1) {
                cohesion = inverse*inverse*inverse * dist*dist;
            } else {
                cohesion = 0;
            }
            cohesion *= 32.0/M_PI;

            surfaceTensionForce -= delta * cohesion;


            const float_type deficiency = (2 * targetNeighbourhoodVolume) / (particle.volume + other->volume);
            force += surfaceTensionForce * (surfaceTension * deficiency);

            force *= timeStep;

            particle.vel += force * particle.invMass;
            other->vel   -= force * static_cast<Particle*>(other)->invMass;
        }
    }

    for (auto& particle : rigid.getParticles()) {
        for (BaseParticle* other : particle.neighbours) {
            Vec2 delta = particle.pos - other->pos;
            float_type dist = delta.length();

            Vec2 force = (particle.vel - other->vel) * ((6 * particle.alpha * viscosity * particle.object.friction * kernelGradSize(dist)) / (other->volume * dist));
            force *= timeStep;

            particle.object.applyImpulse(force * massConversionFactor, particle.pos * invScaleFactor);
            other->vel -= force * static_cast<Particle*>(other)->invMass;
        }
    }
    updateRigidParticleVelocities();
}

void SPHSolver::correctDensity(float_type timeStep) {
    // Fix position divergence
    float_type total;
    float_type error;
    size_t densitySteps = 0;
    do {
        total = 0;
        updateVolumeDerivative();

        for (auto& particle : fluid.getParticles()) {
            float_type forwardVolume = particle.volumeDerivative * timeStep + particle.volume;

            forwardVolume = std::max(forwardVolume, targetNeighbourhoodVolume);

            total += forwardVolume;

            particle.outward = particle.alpha * (forwardVolume - targetNeighbourhoodVolume) / (timeStep * particle.volume);


            for (BaseParticle* other : particle.neighbours) {
                applySeparationImpulse(particle, static_cast<Particle&>(*other), 2 * (particle.outward + other->outward));
            }
        }

        for (auto& particle : rigid.getParticles()) {
            for (BaseParticle* other : particle.neighbours) {
                applySeparationImpulse(particle, static_cast<Particle&>(*other), particle.alpha * other->outward);
            }
        }

        densitySteps++;

        error = total / (fluid.getParticles().size() * targetNeighbourhoodVolume);

        //std::cout << "iter:" << error << std::endl;
    } while (error > 1.001 && densitySteps < 20);
}

void SPHSolver::correctDivergence() {
    // Fix velocity divergence
    float_type total;
    float_type error;
    size_t divergenceSteps = 0;
    do {
        total = 0;
        updateVolumeDerivative();

        for (auto& particle : fluid.getParticles()) {
            particle.volumeDerivative = std::max(particle.volumeDerivative, (float_type)0.0);

            total += particle.volumeDerivative;
            particle.outward = 0.5 * particle.alpha * particle.volumeDerivative / particle.volume;


            for (BaseParticle* other : particle.neighbours) {
                applySeparationImpulse(particle, static_cast<Particle&>(*other), 2 * (particle.outward + other->outward));
            }
        }

        for (auto& particle : rigid.getParticles()) {
            for (BaseParticle* other : particle.neighbours) {
                applySeparationImpulse(particle, static_cast<Particle&>(*other), particle.alpha * other->outward);
            }
        }

        divergenceSteps++;

        error = total / (fluid.getParticles().size() * targetNeighbourhoodVolume);

        //std::cout << "a" << error << std::endl;

    } while (error > 0.0005 && divergenceSteps < 20);
}

void SPHSolver::singleStep(float_type timeStep) {
    fixParticles();
    correctDivergence();
    applyNonPressureForces(timeStep);
    correctDensity(timeStep);
    for (auto& particle : fluid.getParticles()) {
        particle.pos += particle.vel * timeStep;
    }
}

void SPHSolver::update(float_type totalStep) {
    float_type maximumStep = 0.5;

    //reorder();
    
    float_type currentStep = 0;
    while (currentStep + maximumStep < totalStep) {
        singleStep(maximumStep);

        currentStep += maximumStep;
    }
    singleStep(totalStep - currentStep);
}


template class NeighbourhoodSolver<Particle>;
template class NeighbourhoodSolver<RigidParticle>;