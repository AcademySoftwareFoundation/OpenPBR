
# Change Log

This file gives a high level overview of the changes introduced between versions, relative to version 1.0.

## [1.2] - Unreleased

### Look changing enhancements
- #277: This will ensure defined and portable behavior across renderers.
- #256: This PR adds a safety clamp to the result of metallic F82-tint model Fresnel calculations, preventing any negative reflectance values and therefore improving physical correctness and rendering quality for metallic surfaces.
- #247: This alters the behavior of `specular_weight` when applied to the dielectric base, so that the refraction direction is *not* modified by `specular_weight`,
as this control is designed to vary only the reflectivity without disturbing the refraction appearance. Thus the reflection highlight and the refraction direction are
effectively decoupled, in an unphysical but artistically convenient way.
- #240: Fixes a bug in the MaterialX graph, where the edge-tint color for the generalized_schlick_bsdf was multiplied by `specular_weight`, but the whole lobe was multiplied by `specular_weight` as well.
- #251: Fixes a bug in the MaterialX implementation of thin-walled subsurface, where `specular_color` was accounted for in both the BSDF weights and as an explicit multiplier.
- #250: This PR ensures that the `geometry_thin_walled` property, which indicates if a material's geometry should be treated as "thin-walled" (i.e., like a sheet or membrane without interior volume), is correctly connected to and represented within the <surface> node of MaterialX.
- #231: Introduces a new parameter called `emission_weight`, providing a simple $[0,1]$ dimensionless scale facto r for the `emission_luminance`.
- #238: Prior to this change, if `specular_weight` was set to a value greater than 1, it could lead to unphysical metallic Fresnel factors > 1. By introducing the clamp, the code ensures that, regardless of the value given to specular_weight, the resulting metal Fresnel reflectance remains within a physical range.

### Additive enhancements

### Bug fixes

## [1.1] - Jun 28, 2024

 - #211: This won't make much difference to the look in implementations that ignore the adjacent IORs of the film, but for those that take it into account, this will make the film visible rather than invisible by default (since `specular_ior` is 1.5 by default, and `coat_ior` 1.6).

 - #217: This change enables Zeltner sheen in the reference implementation of OpenPBR, leveraging the new functionality in MaterialX.

## [1.0] - Jun 4, 2024

 - _First release._


