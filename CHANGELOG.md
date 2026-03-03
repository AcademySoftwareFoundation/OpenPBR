
# OpenPBR Change Log

This file gives a high level overview of the changes introduced between versions, relative to version 1.0.

✨ new feature &nbsp;|&nbsp; 🎨 look-changing &nbsp;|&nbsp; 🐛 bug fix

## [[1.2]](https://github.com/AcademySoftwareFoundation/OpenPBR/tree/dev_1.2) - Unreleased

- ✨ [Add specular_retroreflectivity parameter](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/255) **#255**: Introduces `specular_retroreflectivity` to support retroreflective materials. Blend the standard microfacet BSDF with a retroreflective variant: `f(wi, wo) = (1 - w) * f_microfacet(wi, wo) + w * f_microfacet(reflect(wi, N), wo)`, where `w = specular_retroreflectivity`. For dielectrics, the retroreflective modification applies to the BRDF only, leaving the BTDF unchanged.
- 🎨 [Add emission_weight](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/231) **#231**: Introduces `emission_weight`, a [0, 1] scale factor applied to `emission_luminance`: `emission = emission_weight * emission_luminance * emission_color`.
- 🎨 [Add clamp of metal Fresnel to allow for specular_weight > 1](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/238) **#238**: In the modulated IOR formula, clamp `specular_weight * F0` to [0, 1] before the square root: `ε = sgn(η - 1) * sqrt(min(specular_weight * F0, 1))`. This prevents unphysical Fresnel factors > 1 while still allowing `specular_weight > 1` to increase reflectivity above the `specular_ior` baseline.
- 🎨 [specular_weight reinterpretation (as decoupled IOR)](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/247) **#247**: The refraction direction is computed using the original `specular_ior`, while Fresnel reflectance uses an IOR modulated by `specular_weight`. This decouples the reflection highlight from the refraction direction in an unphysical but artistically convenient way.
- 🎨 [MaterialX: Connect `geometry_thin_walled` flag to \<surface\>](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/250) **#250**: Ensures that the `geometry_thin_walled` property is correctly connected to and represented within the `<surface>` node of MaterialX.
- 🎨 [clamp all inputs according to the parameter reference (section 4 of the spec) (#276)](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/277) **#277**: This will ensure defined and portable behavior across renderers. Clamp each input to its valid range from the parameter reference table before use in any computation.
- 🎨 [`transmission_scatter` sets volume albedo directly](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/286) **#286**: Sets the volume single-scattering albedo directly to `transmission_scatter` (per channel), rather than deriving it from separate scatter and absorption coefficients. The [0, 1] range is now directly meaningful as the fraction of scattered vs. absorbed light.
- 🐛 [MaterialX: metal edge tint should not be multiplied by specular_weight](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/240) **#240**: Fixes a bug in the MaterialX graph, where the edge-tint color for the `generalized_schlick_bsdf` was multiplied by `specular_weight`, but the whole lobe was already multiplied by `specular_weight` as well.
- 🐛 [MaterialX: fix bug in thin-walled subsurface](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/251) **#251**: Fixes a bug in the MaterialX implementation of thin-walled subsurface, where `specular_color` was accounted for in both the BSDF weights and as an explicit multiplier.
- 🐛 [Fix the coat darkening color shift](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/253) **#253**: Fixes an unwanted chromaticity shift during coat darkening with strong coat colors. The base BSDF is multiplied by `lerp(1, Δ, coat_darkening) * T²_coat`, where the darkening factor `Δ = (1-K) / (1 - K * E_b * T²_coat)` now correctly incorporates the coat absorption color `T²_coat` in the denominator.
- 🐛 [Add clamp to prevent negative metallic Fresnel](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/256) **#256**: The F82-tint Fresnel model can yield negative values for extreme parameter combinations. Clamp the per-channel result to 0 after evaluation: `F = max(0, F_F82)`.
- 🐛 [fix wrong attribute name for `geometry_thin_walled`](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/292) **#292**: Corrects an incorrect attribute name used in the surface construction node for the `geometry_thin_walled` parameter in the reference MaterialX graph.
- 🐛 [Fix typo in reference MaterialX graph](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/293) **#293**: Fixes a type error where the return value of a BSDF mix node was not typed as BSDF, preventing the graph from compiling.

## [[1.1]](https://github.com/AcademySoftwareFoundation/OpenPBR/tree/v1.1) - Jun 28, 2024

- ✨ [Enable Zeltner sheen](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/217) **#217**: This change enables Zeltner sheen in the reference implementation of OpenPBR, leveraging the new functionality in MaterialX.
- 🎨 [Change thin film IOR default](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/211) **#211**: This won't make much difference to the look in implementations that ignore the adjacent IORs of the film, but for those that take it into account, this will make the film visible rather than invisible by default (since `specular_ior` is 1.5 by default, and `coat_ior` 1.6).
- 🎨 [Update subsurface color types](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/220) **#220**: Changes `subsurface_radius_scale` from `vector3` to `color3`, aligning the type with its per-channel usage.

## [[1.0]](https://github.com/AcademySoftwareFoundation/OpenPBR/tree/v1.0) - Jun 4, 2024

- _First release._


