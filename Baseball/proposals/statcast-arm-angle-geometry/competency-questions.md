# Competency questions

1. Which Bodily Component of the pitcher supplies the provider's shoulder
   landmark, and how is the selected Fiat Point identified?
2. Which Fiat Point of the Baseball represents the tracked ball position at
   release?
3. Does the shoulder-to-ball Fiat Line share the shoulder point or ball point
   with the ground-parallel reference Fiat Line?
4. Which actual ground/field structure and Baseball Field Coordinate Reference
   System ICE determine the reference line's direction?
5. What Process or Process Boundary is the provider's release event, and is it
   supported as an instant, a short interval, a plane crossing, or a fitted
   evaluation?
6. How does that evaluation relate to the Pitch-Ball Motion Process and its
   Velocity Process Profile using accepted relations?
7. Does `arm_angle` measure the Angle Quality between the two Fiat Lines rather
   than the pitcher, arm, Pitch Act, or Velocity profile?
8. Which method/version evidence distinguishes changes in tracking or
   anatomical landmark selection?
9. Can missing/not-tracked values be represented without creating a zero-degree
   angle or placeholder shoulder?
10. Can the Statcast geometry be removed while preserving MLB-game Pitch Act,
    pitcher, Baseball, and Pitch-Ball Motion facts?

## Negative tests

- `arm_angle` is not a class or object property.
- A Measurement ICE is not the Angle Quality or either Fiat Line.
- The shoulder landmark is not inferred from a free-text label alone.
- The entire Pitch-Ball Motion Process is not assigned one angle or velocity.
- A scalar speed measurement does not establish the release direction or
  shoulder geometry.
- `release` in an IRI does not establish a Process Boundary or Temporal
  Instant.
- A generic Bodily Component is not silently reclassified as a shoulder
  universal.
