# Competency questions and accepted answers

1. What unit interprets the numeric values in the five MLB venue field
   dimension fields?
   **Accepted:** feet.
2. Does BaseballO require a new unit individual?
   **Accepted:** no; reuse CCO `cco:ont00001714`, Foot Measurement Unit.
3. Does the numeric literal itself become a Distance Quality?
   **Accepted:** no. A Distance Measurement Information Content Entity carries
   the literal, uses the Foot Measurement Unit, and is a measurement of a
   world-side Distance Quality.
4. Does accepting feet determine the distance's Fiat Point relata?
   **Accepted:** no.
5. Does accepting feet determine the measured path, wall or boundary choice,
   method, venue configuration, or effective interval?
   **Accepted:** no; each remains a source-specific design requirement.
6. Does this decision also resolve elevation, coordinates, azimuth, or
   capacity?
   **Accepted:** no. The scope is limited to the five field-dimension values.
