
# OpenPBR Change Log
This file gives a high level overview of the changes introduced between versions, relative to version 1.0.

OpenPBR follows [semantic versioning](https://semver.org): patch versions (e.g. 1.1.2) only contain implementation fixes, wording and cosmetic changes, while new features and look-changing changes are reserved for minor and major versions.

How to read this document : ✨ new feature &nbsp;|&nbsp; 🎨 look-changing &nbsp;|&nbsp; 🐛 implementation fix &nbsp;|&nbsp; 📝 wording &nbsp;|&nbsp; 🧹 cosmetic

- ✨ **New feature**: new functionality in the model.
- 🎨 **Look-changing**: a change to the model that alters the appearance of existing materials.
- 🐛 **Implementation fix**: a change to the reference MaterialX implementation, for example bringing it in line with the specification.
- 📝 **Wording**: a clarification, rewording or correction of the specification text that does not change the intended model.
- 🧹 **Cosmetic**: a presentation-only change (typos, notation, capitalization, links, images) with no effect on meaning, or a change to the project resources (example materials, changelog, front page).

## [[1.2]](https://github.com/AcademySoftwareFoundation/OpenPBR/tree/v1.2) - Unreleased
- ✨ [Specular haze](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/254) **#254**: Adds `specular_haze` and `specular_haze_spread`, which blend the dielectric and metallic base BSDFs with a rougher copy of themselves to produce a "hazy gloss" highlight. Implemented in the reference MaterialX graph in **#298**.
- ✨ [Retroreflectivity](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/255) **#255**: Adds `specular_retroreflectivity`, which blends the base specular BRDF with a retroreflective variant of the microfacet model. For the dielectric base only the BRDF is affected, so refraction is unchanged.
- ✨ [Emission weight](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/231) **#231**: Adds `emission_weight`, a $[0, 1]$ multiplier of `emission_luminance`.
- 🎨 [Decoupled specular weight](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/247) **#247**: `specular_weight` now modulates only the reflectivity of the dielectric base, while the refraction direction is computed from the unmodified `specular_ior`. This decouples the highlight from the refraction in an unphysical but artistically convenient way.
- 🎨 [Specular weight above 1](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/238) **#238**: Allows `specular_weight` to exceed 1 for metals too (as it already could for the dielectric), boosting the metallic Fresnel factor with a clamp to keep it at most 1. **#316** has since replaced this clamp.
- 🎨 [Metal Fresnel boost](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/316) **#316**: For metals, a `specular_weight` above 1 now boosts the F0 and F82 colors (`base_weight` * `base_color` and `specular_color`), each clamped to $[0, 1]$, rather than clamping the scaled Fresnel curve. This always gives a valid F82-tint curve, and can be expressed in the MaterialX graph. At `specular_weight` of 1 or below the look is unchanged.
- 🎨 [Input clamping](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/277) **#277**: Clamps every input to the valid range given in the parameter reference before use, for defined and portable behavior across renderers.
- 🎨 [Transmission scatter as volume albedo](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/286) **#286**: `transmission_scatter` now sets the single-scattering albedo of the transmission volume directly, so its $[0, 1]$ range is the fraction of light scattered rather than absorbed.
- 🎨 [Coat darkening color shift](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/253) **#253**: Fixes an unwanted color shift when coat darkening is combined with a strongly colored coat, by including the coat absorption in the darkening factor.
- 🎨 [Non-negative metal Fresnel](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/256) **#256**: Clamps the F82-tint metallic Fresnel factor to be non-negative, which it could otherwise fail to be for extreme parameter combinations.
- 🐛 [Thin-walled subsurface specular color](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/251) **#251**: Fixes the MaterialX implementation of thin-walled subsurface, where `specular_color` was applied twice.
- 🐛 [Thin-walled attribute name](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/292) **#292**: Fixes the attribute name used for `geometry_thin_walled` in the surface node of the MaterialX graph.
- 🐛 [Mix node type](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/293) **#293**: Fixes a BSDF mix node in the MaterialX graph whose output was not typed as BSDF, which stopped the graph from compiling.
- 🐛 [Coat color on coated base](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/317) **#317**: Fixes a dangling `coat_color` connection in the MaterialX graph (introduced in **#253**), which MaterialX replaced with white, so `coat_color` did not tint the coated base.
- 📝 [Version update](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/283) **#283**: Updates the MaterialX node definition to 1.2.

## [[1.1.2]](https://github.com/AcademySoftwareFoundation/OpenPBR/tree/v1.1.2) - Unreleased
- 🐛 [Thin-walled subsurface color](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/321) **#321**: Fixes the MaterialX implementation in thin-walled mode, where `subsurface_color` was applied twice, squaring the total albedo (ported from **AcademySoftwareFoundation/MaterialX#3066**).
- 🐛 [Scatter anisotropy UI names](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/284) **#284**: Renames the UI names of `transmission_scatter_anisotropy` and `subsurface_scatter_anisotropy` to Scatter Anisotropy, in the MaterialX implementation and the parameter table, to make clear they control the phase function anisotropy.
- 📝 [Coat transmittance notation](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/304) **#304**: Uses the bold RGB notation for the coat transmittance consistently, and corrects the BRDF layering formulas in the reference implementation section to use the squared coat transmittance.
- 📝 [Version update](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/332) **#332**: Updates the specification and MaterialX node definition to 1.1.2.
- 🧹 [Invalid example parameterizations](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/313) **#313**: Fixes color values above 1 in some of the MaterialX example materials.
- 🧹 [Oren-Nayar normal symbol](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/322) **#322**: Fixes the symbol used for the normal in the Oren-Nayar equation.
- 🧹 [Missing section links](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/309) **#309**: Adds missing links to sections of the specification.
- 🧹 [Equation reference capitalization](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/315) **#315**: Makes the capitalization of equation references consistent.
- 🧹 [Subsurface color range](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/325) **#325**: Fixes the range of `subsurface_color` in the parameter table to indicate it is 3-dimensional.

## [[1.1.1]](https://github.com/AcademySoftwareFoundation/OpenPBR/tree/v1.1.1) - April 17, 2026
- 🐛 [Metal edge tint and ignored thin-walled](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/300) **#300**: Fixes two issues in the MaterialX implementation, the edge tint was incorrectly multiplied by the specular weight (backported from **#240**) and `geometry_thin_walled` was not connected to the shader (backported from **AcademySoftwareFoundation/MaterialX#2759**).
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
