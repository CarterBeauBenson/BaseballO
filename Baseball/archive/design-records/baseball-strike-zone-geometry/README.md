# Baseball strike-zone geometry

Status: **accepted 2026-08-31**

This package proposes a three-dimensional Baseball Strike Zone Site and the
distinct two-dimensional ABS Evaluation Fiat Surface. It uses Sites, Fiat
Surfaces, Home Plate, rules, and measurement geometry. It introduces no Spatial
Region, Coordinate System Axis, or new object property.

These classes are defined by their real geometry and rule relations rather
than by a nominal-classification shortcut.

The identity-bearing batter and Home Plate anchors for the six Strike Zone
Fiat Surfaces remain unresolved. `BaseballStrikeZoneSite` therefore has only
necessary subclass restrictions; it has no `owl:equivalentClass` axiom yet.

The package is archived as an accepted design record. Bounded ontology and
pipeline implementation is authorized separately; unresolved field semantics
still do not license RML or ABS inference.
