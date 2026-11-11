
# OpenPBR Change Log
This file gives a high level overview of the changes introduced between versions, relative to version 1.0.

OpenPBR follows [semantic versioning](https://semver.org): patch versions (e.g. 1.1.2) only contain implementation fixes, wording and cosmetic changes, while new features and look-changing changes are reserved for minor and major versions.

How to read this document : ✨ new feature &nbsp;|&nbsp; 🎨 look-changing &nbsp;|&nbsp; 🐛 implementation fix &nbsp;|&nbsp; 📝 wording &nbsp;|&nbsp; 🧹 cosmetic

- ✨ **New feature**: new functionality in the model.
- 🎨 **Look-changing**: a change to the model that alters the appearance of existing materials.
- 🐛 **Implementation fix**: a change to the reference MaterialX implementation, for example bringing it in line with the specification.
- 📝 **Wording**: a clarification, rewording or correction of the specification text that does not change the intended model.
- 🧹 **Cosmetic**: a presentation-only change (typos, notation, capitalization, links, images) with no effect on meaning, or a change to the project resources (example materials, changelog, front page).

## [1.2] - Unreleased
- ✨ [Specular haze](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/254) **#254**: Adds `specular_haze` and `specular_haze_spread`, which blend the dielectric and metallic base BSDFs with a rougher copy of themselves to produce a "hazy gloss" highlight. Implemented in the reference MaterialX graph in **#298**.
- ✨ [Retroreflectivity](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/255) **#255**: Adds `specular_retroreflectivity`, which blends the base specular BRDF with a retroreflective variant of the microfacet model. For the dielectric base only the BRDF is affected, so refraction is unchanged.
- ✨ [Metal specular weight above 1](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/316) **#316**: Extends the range of `specular_weight` for metals above 1 (as it already was for the dielectric). Values above 1 boost the F0 and F82 colors (`base_weight` * `base_color` and `specular_color`), each clamped to $[0, 1]$, which always gives a valid F82-tint curve that can be expressed in the MaterialX graph. Supersedes the Fresnel clamp of **#238**.
- 🎨 [Emission weight](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/231) **#231**: Adds `emission_weight`, a $[0, 1]$ multiplier of `emission_luminance`, with a default of 0, and changes the default of `emission_luminance` from 0 to 1000.
  - **Impact of the change:** Every material with a non-zero `emission_luminance` that does not set `emission_weight` stops emitting.
  - **Matching previous version look:** Set `emission_weight` to 1, which matches exactly.
- 🎨 [Decoupled specular weight](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/247) **#247**: `specular_weight` now modulates only the reflectivity of the dielectric base, while the refraction direction is computed from the unmodified `specular_ior`. This decouples the highlight from the refraction in an unphysical but artistically convenient way.
  - **Impact of the change:** Only materials with `specular_weight` different from 1, mostly visible through refraction and total internal reflection in transmissive and subsurface materials. With `specular_ior` of 1.5 and light incident at 60°, a `specular_weight` of 0.5 bends the refracted ray 5.4° more (40.6° to 35.3°) and moves the critical angle from 48.8° to 41.8°. A `specular_weight` of 0 previously meant no refraction at all, and now refracts by 25°, while a `specular_weight` of 2 bends 6.3° less.
  - **Matching previous version look:** Set `specular_weight` to 1, and `specular_ior` to the modulated IOR, i.e. the modulated IOR ratio $\eta^\prime$ of the Dielectric base section times the exterior IOR (taking the coat into account), which matches exactly. A textured `specular_weight` requires a correspondingly textured `specular_ior`.
- 🎨 [Input clamping](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/277) **#277**: Clamps every input to the valid range given in the parameter reference before use, for defined and portable behavior across renderers.
  - **Impact of the change:** Only inputs outside the range given in the parameter reference, such as colors above 1, whose behavior was previously undefined. The difference can be large for those inputs.
  - **Matching previous version look:** There is no in-range equivalent, the out-of-range values need to be brought into range manually.
- 🎨 [Transmission scatter as volume albedo](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/286) **#286**: `transmission_scatter` now sets the single-scattering albedo of the transmission volume directly, so its $[0, 1]$ range is the fraction of light scattered rather than absorbed.
  - **Impact of the change:** Only materials with a non-zero `transmission_scatter`. For example with `transmission_color` 0.5 and `transmission_scatter` 0.5, the single-scattering albedo goes from 0.72 to 0.5, and with `transmission_color` 0.8 it goes from 1 (with an increased extinction) to 0.5.
  - **Matching previous version look:** Set `transmission_scatter` to $\mu_s / \mu_t$ and `transmission_color` to $\exp(-\mu_t \lambda)$, where $\mu_s$ and $\mu_t$ are the previous scattering and extinction coefficients (after the absorption shift) and $\lambda$ is `transmission_depth`, which matches exactly.
- 🎨 [Coat darkening color shift](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/253) **#253**: Fixes an unwanted color shift when coat darkening is combined with a strongly colored coat, by including the coat absorption in the darkening factor. The MaterialX implementation was fixed up in **#293** and **#317**.
  - **Impact of the change:** Every coated material with a non-white `coat_color`, including at the default `coat_darkening` of 1, as the additional absorption along the internal reflections darkens the base more in the tinted channels. The effect grows with the base roughness. For a rough base with albedo 0.8 under a coat with IOR 1.6, the darkening factor of a tinted channel goes from 0.73 to 0.47 for a `coat_color` of 0.5 (35% darker), and to 0.37 for a `coat_color` of 0.1 (49% darker). For a base albedo of 0.3 the difference is 11% to 18%, and for a smooth base around 2%. In the MaterialX implementation, a partial `coat_weight` is now also a linear mix of the coated and uncoated base, which is around 5% brighter at a `coat_weight` of 0.5.
  - **Matching previous version look:** Lower `coat_darkening` to $(1 - \Delta_\mathrm{old}) / (1 - \Delta_\mathrm{new})$, where $\Delta$ is the darkening factor of the Coat darkening section, which matches exactly for a gray coat and approximately for a colored one.
- 🎨 [Non-negative metal Fresnel](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/256) **#256**: Clamps the F82-tint metallic Fresnel factor to be non-negative, which it could otherwise fail to be for extreme parameter combinations, and adds the formula for the average albedo of the F82-tint model.
  - **Impact of the change:** Only metals with a dark `specular_color` and a low F0, in renderers that did not already clamp. The Fresnel factor reaches -0.127 at worst (for F0 and `specular_color` of 0, at around 75°), between -0.04 and -0.11 for F0 up to 0.05 and `specular_color` up to 0.2, and is never negative for F0 of at least 0.05 and `specular_color` of at least 0.5. The reference MaterialX implementation is unaffected.
  - **Matching previous version look:** Not possible, and not desirable, since a negative reflectance is not physical.
- 📝 [Version update](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/283) **#283**: Updates the MaterialX node definition to 1.2.

## [[1.1.2]](https://github.com/AcademySoftwareFoundation/OpenPBR/tree/v1.1.2) - November 5th, 2026
- 🐛 [Thin-walled subsurface color](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/321) **#321**: Fixes the MaterialX implementation in thin-walled mode, where `subsurface_color` was applied twice, squaring the total albedo (ported from **AcademySoftwareFoundation/MaterialX#3066**).
- 🐛 [Scatter anisotropy UI names](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/284) **#284**: Renames the UI names of `transmission_scatter_anisotropy` and `subsurface_scatter_anisotropy` to Scatter Anisotropy, in the MaterialX implementation and the parameter table, to make clear they control the phase function anisotropy.
- 📝 [Coat transmittance notation](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/304) **#304**: Uses the bold RGB notation for the coat transmittance consistently, and corrects the BRDF layering formulas in the reference implementation section to use the squared coat transmittance.
- 📝 [Version update](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/332) **#332**: Updates the specification and MaterialX node definition to 1.1.2.
- 🧹 [Invalid example parameterizations](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/313) **#313**: Fixes color values above 1 in some of the MaterialX example materials.
- 🧹 [Oren-Nayar normal symbol](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/322) **#322**: Fixes the symbol used for the normal in the Oren-Nayar equation.
- 🧹 [Missing section links](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/309) **#309**: Adds missing links to sections of the specification.
- 🧹 [Equation reference capitalization](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/315) **#315**: Makes the capitalization of equation references consistent.
- 🧹 [Subsurface color range](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/325) **#325**: Fixes the range of `subsurface_color` in the parameter table to indicate it is 3-dimensional.
- 📝 [Length parameter default unit](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/331) **#331**: Defining the default unit of the `transmission_depth` and `subsurface_radius` length parameters to be in centimeters, if not defined otherwise by the metadata.

## [[1.1.1]](https://github.com/AcademySoftwareFoundation/OpenPBR/tree/v1.1.1) - April 17, 2026
- 🐛 [Metal edge tint and ignored thin-walled](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/300) **#300**: Fixes two issues in the MaterialX implementation, the edge tint was incorrectly multiplied by the specular weight (backported from **#240**) and `geometry_thin_walled` was not connected to the shader (backported from **#250** and **AcademySoftwareFoundation/MaterialX#2759**).
- 🐛 [MaterialX hints](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/265) **#265**: Adds MaterialX code generation hints.
- 📝 [Implementation flexibility](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/248) **#248**: Adds a new section to the specification formally stating that implementers of the specification are free to use approximations, for example for low-power constraints.
- 📝 [Thin-walled subsurface](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/258) **#258**: Clarifies the interaction of `geometry_thin_walled` and subsurface and how it affects `subsurface_radius` and `subsurface_scale`.
- 📝 [HDR emission color](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/260) **#260**: Allows values above 1 for `emission_color`.
- 📝 [Improved wording](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/218) **#218**: Adds various clarifications and rewordings to the specification.
- 📝 [Revised thin-film section](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/262) **#262**: Expands the thin-film specification and revises it to make it clearer.
- 🧹 [More examples](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/257) **#257**: Adds more material examples.
- 🧹 [Added Changelog](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/289) **#289**: Adds a changelog to the project.
- 🧹 [New logo](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/235) **#235**: Uses the new logo in the specification.
- 🧹 [Broken links](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/230) **#230**: Fixes broken links in the specification.
- 🧹 [New images](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/236) **#236**: Updates images for the model schematic illustration, glossy diffuse wood, fuzz roughness and new images for anisotropy.

## [[1.1]](https://github.com/AcademySoftwareFoundation/OpenPBR/tree/v1.1) - Jun 28, 2024
- 🎨 [Change thin film IOR default](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/211) **#211**: This won't make much difference to the look in implementations that ignore the adjacent IORs of the film, but for those that take it into account, this will make the film visible rather than invisible by default (since `specular_ior` is 1.5 by default, and `coat_ior` 1.6).
- 🎨 [Update subsurface color types](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/220) **#220**: Changes `subsurface_radius_scale` from `vector3` to `color3`, aligning the type with its per-channel usage.
- 🐛 [Enable Zeltner sheen](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/217) **#217**: This change enables Zeltner sheen in the reference implementation of OpenPBR, leveraging the new functionality in MaterialX.
- 📝 [Allow darkening in fuzz](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/207) **#207**: Allows fuzz to darken as well as lighten the reflection.
- 📝 [Clearer emission color formula](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/209) **#209**: Clarifies the formula for the emission color.
- 📝 [Version update](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/221) **#221**: Updates the specification and MaterialX node definition to 1.1.
- 🧹 [Updated OpenPBR default example](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/216) **#216**: Updates the OpenPBR default example, matching its values to the latest default values of the shading model.
- 🧹 [Resource section](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/215) **#215**: Adds a resource section to the front page of the project.

## [[1.0]](https://github.com/AcademySoftwareFoundation/OpenPBR/tree/v1.0) - Jun 4, 2024

- _First release._
