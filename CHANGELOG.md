
# OpenPBR Change Log
This file gives a high level overview of the changes introduced between versions, relative to version 1.0.

OpenPBR follows [semantic versioning](https://semver.org): patch versions (e.g. 1.1.2) only contain implementation fixes, wording and cosmetic changes, while new features and look-changing changes are reserved for minor and major versions.

How to read this document : ✨ new feature &nbsp;|&nbsp; 🎨 look-changing &nbsp;|&nbsp; 🐛 implementation fix &nbsp;|&nbsp; 📝 wording &nbsp;|&nbsp; 🧹 cosmetic

- ✨ **New feature**: new functionality in the model.
- 🎨 **Look-changing**: a change to the model that alters the appearance of existing materials.
- 🐛 **Implementation fix**: a change to the reference MaterialX implementation, for example bringing it in line with the specification.
- 📝 **Wording**: a clarification, rewording or correction of the specification text that does not change the intended model.
- 🧹 **Cosmetic**: a presentation-only change (typos, notation, capitalization, links, images) with no effect on meaning, or a change to the project resources (example materials, changelog, front page).

## [[1.1.2]](https://github.com/AcademySoftwareFoundation/OpenPBR/tree/v1.1.2) - Unreleased
- 🐛 [Thin-walled subsurface color](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/321) **#321**: Fixes the MaterialX implementation in thin-walled mode, where `subsurface_color` was applied twice, squaring the total albedo (ported from **AcademySoftwareFoundation/MaterialX#3066**).
- 🐛 [Scatter anisotropy UI names](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/284) **#284**: Renames the UI names of `transmission_scatter_anisotropy` and `subsurface_scatter_anisotropy` to Scatter Anisotropy, in the MaterialX implementation and the parameter table, to make clear they control the phase function anisotropy.
- 📝 [Coat transmittance notation](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/304) **#304**: Uses the bold RGB notation for the coat transmittance consistently, and corrects the BRDF layering formulas in the reference implementation section to use the squared coat transmittance.
- 🧹 [Invalid example parameterizations](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/313) **#313**: Fixes color values above 1 in some of the MaterialX example materials.
- 🧹 [Oren-Nayar normal symbol](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/322) **#322**: Fixes the symbol used for the normal in the Oren-Nayar equation.
- 🧹 [Missing section links](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/309) **#309**: Adds missing links to sections of the specification.
- 🧹 [Equation reference capitalization](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/315) **#315**: Makes the capitalization of equation references consistent.
- 🧹 [Subsurface color range](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/325) **#325**: Fixes the range of `subsurface_color` in the parameter table to indicate it is 3-dimensional.
- 🎨 [length parameter default unit](https://github.com/AcademySoftwareFoundation/OpenPBR/pull/331) **#331**: Defining the default unit of the `transmission_depth` and `subsurface_radius` length parameters to be in centimeters, if not defined otherwise by the material's metadata.

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
