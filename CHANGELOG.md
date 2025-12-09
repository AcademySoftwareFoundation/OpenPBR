
# Change Log

This file gives a high level overview of the changes introduced between versions, relative to version 1.0.

## [1.1.1] - April 17, 2026

- #216 Updates the OpenPBR default example, matching its values to the latest default values of the shading model.

## [1.1] - Jun 28, 2024

 - #211: This won't make much difference to the look in implementations that ignore the adjacent IORs of the film, but for those that take it into account, this will make the film visible rather than invisible by default (since `specular_ior` is 1.5 by default, and `coat_ior` 1.6).

 - #217: This change enables Zeltner sheen in the reference implementation of OpenPBR, leveraging the new functionality in MaterialX.

## [1.0] - Jun 4, 2024

 - _First release._


