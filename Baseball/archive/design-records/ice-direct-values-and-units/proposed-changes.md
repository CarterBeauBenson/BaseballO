# Proposed final relation axioms and annotations

This is a reviewable change set, not an executable ontology patch. Deletion of
an existing OWL axiom cannot be represented by loading an additive Turtle
file, so the intended removals and replacements are stated explicitly here.

## Generic literal properties

For each of the following properties, replace
`rdfs:domain cco:ont00000253` (Information Bearing Entity) with
`rdfs:domain cco:ont00000958` (Information Content Entity):

- `cco:ont00001765` has text value;
- `cco:ont00001767` has datetime value;
- `cco:ont00001768` has URI value;
- `cco:ont00001769` has decimal value;
- `cco:ont00001770` has double value;
- `cco:ont00001771` has date value;
- `cco:ont00001772` has boolean value; and
- `cco:ont00001773` has integer value.

Revise each definition from the generic phrase "a data property that has as
its range" to the form:

> A data property that relates an Information Content Entity to a [datatype]
> literal that is part of the content expressed by that Information Content
> Entity.

Retain the current datatype ranges. This proposal does not change lexical
canonicalization or missing-value behavior.

## Geographic literal properties

For `cco:ont00001763`, `cco:ont00001764`, and `cco:ont00001766`:

- declare Information Content Entity as the domain;
- retain existing datatype ranges where present;
- replace references to connecting coordinate data to a single Information
  Bearing Entity with Information Content Entity; and
- require use with an explicit accepted coordinate reference system when the
  literal alone would be ambiguous.

The proposal does not assert that a field-relative coordinate is latitude or
longitude.

## Measurement Unit relation pair

For `cco:ont00001863` (uses measurement unit):

- remove `rdfs:subPropertyOf obo:BFO_0000101` (`is carrier of`);
- replace the domain with `cco:ont00000958` (Information Content Entity);
- retain range `cco:ont00000120` (Measurement Unit);
- retain inverse `cco:ont00001961`; and
- define it as: "x uses measurement unit y iff x is an Information Content
  Entity, y is a Measurement Unit, and y supplies the conventional unit needed
  to interpret a measurement value expressed by x."

For `cco:ont00001961` (is measurement unit of):

- remove its BFO concretization/carrier inverse subproperty axiom;
- retain domain Measurement Unit;
- replace the range with Information Content Entity;
- retain inverse `cco:ont00001863`; and
- define it as the exact inverse of `uses measurement unit`.

## Reference System relation pairs

For `cco:ont00001912` (uses reference system):

- remove `rdfs:subPropertyOf obo:BFO_0000101` (`is carrier of`);
- replace the domain with Information Content Entity;
- retain range `cco:ont00000398` (Reference System);
- retain inverse `cco:ont00001997`; and
- define it as: "x uses reference system y iff x is an Information Content
  Entity, y is a Reference System, and y supplies the standards needed to
  interpret information expressed by x."

For `cco:ont00001997` (is reference system of):

- remove its BFO concretization/carrier inverse subproperty axiom;
- retain domain Reference System;
- replace the range with Information Content Entity;
- retain inverse `cco:ont00001912`; and
- define it as the exact inverse of `uses reference system`.

For the geospatial specializations:

- change the domain of `cco:ont00001913` (uses geospatial coordinate reference
  system) to Information Content Entity;
- change the range of `cco:ont00001900` (is geospatial coordinate reference
  system of) to Information Content Entity;
- retain their inverse relation;
- retain their subproperty placement under the repaired reference-system
  relations; and
- update both definitions to name Information Content Entity rather than IBE.

## Consistency requirements for implementation

An accepted implementation must make the same logical changes in the merged
CCO and MRO snapshots in one commit. It must then run a reasoner-level negative
test proving that a Measurement ICE with a value, unit, and reference system is
not inferred to be an IBE. The test must separately prove that a real IBE may
still carry the Measurement ICE via the BFO carrier relation.
