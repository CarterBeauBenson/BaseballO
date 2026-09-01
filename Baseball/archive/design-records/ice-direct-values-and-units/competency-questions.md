# Competency questions

The proposed foundation pattern must support the following questions without
creating an IBE solely to hold a literal.

1. Which entity is a Measurement ICE about?
2. What literal value does that Measurement ICE have?
3. Which Measurement Unit does that Measurement ICE use?
4. Which Reference System, including a Geospatial Coordinate Reference
   System, does an ICE use?
5. Can a reasoner use any of those assertions without inferring that the ICE
   is also an Information Bearing Entity?
6. Can the inverse unit and reference-system relations return the same ICE?
7. Can date, datetime, text, URI, decimal, double, boolean, and integer values
   be asserted directly on the relevant ICE?
8. Can latitude, longitude, and altitude values be asserted on a coordinate
   ICE while the corresponding Reference System remains explicit?
9. Does the model preserve the distinction between the measured world-side
   entity, the Measurement ICE about it, and any material bearer that may
   concretize that ICE?
10. Can an IBE still be related to an ICE through the BFO carrier relation
    independently of the ICE's value, unit, and reference-system assertions?

Negative test: a Measurement ICE with a decimal value and a Measurement Unit
must not be classified as an IBE merely because those two assertions exist.
