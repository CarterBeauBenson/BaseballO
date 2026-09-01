# MLB venue azimuth geometry

Status: **under review — design only**

This package binds MLB azimuth evidence to the accepted realist Angle Quality
pattern. An Angle Quality inheres in two Fiat Lines that intersect at a shared
Fiat Point; an angular Measurement ICE measures that Quality. The source field
cannot replace the lines, origin, reference frame, direction convention, or
unit.

The field already occurs in the MLB game payload. No mapping may assume a line
from Home Plate to center field, local true north, clockwise rotation, or
degrees without reviewed source evidence.
