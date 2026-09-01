# Source evidence

The archived accepted Statcast investigation records official MLB evidence:

- `attack_angle` is the vertical direction of bat sweet-spot motion at contact
  or at the bat/ball path-intersection point for a swing-and-miss;
- `attack_direction` is the corresponding horizontal direction relative to
  the home-to-center-field direction; and
- `swing_path_tilt` concerns a fitted path from the final 40 milliseconds of
  tracked bat motion.

Bat-tracking availability begins around the 2023 All-Star break according to
the reviewed source evidence. Missingness before or outside tracking coverage
must not be treated as a zero angle.

The accepted inventory marks all three fields genuinely additional. This
package does not reopen that decision and does not select any duplicate
launch-speed, launch-angle, person, game, or pitch field.

Existing vocabulary supplies Swing Act, Baseball Bat, generic Motion,
Velocity, Process Profile, Fiat Point, Fiat Line, Temporal Region, Angle
Quality, Measurement ICE, Degree, Baseball Field Coordinate Reference System
ICE, `has occurrent
part`, `has participant`, `has continuant part`, `exists at`, `inheres in`,
`is a measurement of`, `uses measurement unit`, `uses reference system`, and
`designates`.

The unresolved evidence is the provider's exact sweet-spot selection rule,
projection/tangent construction, coordinate frame, contact/intersection
evaluation scope, and fitted-path algorithm/version. No current accepted
object property explicitly says that a Fiat Line is the tangent determined by
a Velocity profile; that gap remains visible in the Mermaid.

The existence of a fitted output supports some computation, but the source
evidence reviewed here does not identify a causally active Agent at that
Process grain. The diagram therefore uses a generic Process and leaves an Act
of Data Transformation classification unresolved.
