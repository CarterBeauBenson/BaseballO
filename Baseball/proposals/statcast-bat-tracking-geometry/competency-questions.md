# Competency questions

1. Which particular Fiat Point of a Baseball Bat is selected by the provider
   as the tracked sweet spot, and which versioned Reference System supports
   that designation?
2. Can a generic Motion, occurrent part of the Swing Act, be identified as the
   motion in which that Fiat Point participates without introducing a
   field-specific Motion class?
3. Does a CCO Velocity Process Profile of that Motion provide the changing
   direction needed for attack geometry?
4. What accepted relation or construction connects that Velocity profile to
   an actual tangent Fiat Line at the evaluation period?
5. For `attack_angle`, what vertical projection and ground-parallel Fiat Line
   share a Fiat Point with the tangent line?
6. For `attack_direction`, what horizontal projection and home-to-center-field
   Fiat Line constitute the reference geometry?
7. At contact, which Process/Temporal Region supplies the evaluation scope?
8. For a swing-and-miss, how is the provider's bat/ball path-intersection
   evaluation represented without inventing a Bat-Ball Contact Process?
9. Does `swing_path_tilt` measure an Angle Quality between two Fiat Lines, an
   orientation of a fitted Fiat Surface, or another structure not yet covered
   by the accepted Angle Quality?
10. What versioned Algorithm and computation Process construct the final-40-ms
    fitted path, what input observations do they use, and what evidence would
    justify classifying that Process as an Act of Data Transformation with an
    Agent at its own grain?
11. Can missing/not-tracked values be distinguished from not-applicable values
    without minting placeholder geometry?
12. Can this Statcast graph be removed without deleting Swing, Bat, contact,
    or game facts owned by MLB-game?

## Negative tests

- The source row and Measurement ICE are not the Velocity, tangent line, Angle
  Quality, or fitted path.
- `attack_angle`, `attack_direction`, and `swing_path_tilt` are not ontology
  classes.
- A Velocity profile label does not establish a tangent or projection.
- A swing-and-miss does not create a Bat-Ball Contact Process.
- The last 40 milliseconds in prose or an IRI do not supply temporal scope.
- A fitted plane is not forced into a two-Fiat-Line Angle Quality without a
  reviewed construction.
- A model-computation Process is not typed as an Act until a causally active
  Agent at that Process grain is evidenced.
- Duplicate MLB launch-speed/launch-angle fields are not remapped here.
