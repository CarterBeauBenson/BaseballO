# Competency questions

## World processes and identity

1. Which existing BaseballO Processes constitute the physical history from a
   Pitch Act through pitch-ball motion, Swing Act, possible bat-ball contact,
   and possible batted-ball motion?
2. Which world entities are reused from the MLB-game graph, and which
   Statcast evidence entities remain source-specific?
3. Can the Statcast module be disconnected without deleting the Game,
   Plate Appearance, Persons, Baseball, Baseball Bat, or existing Processes?

## Process profiles and evaluation scope

4. Does one changing Speed or Velocity Process Profile span a whole Motion,
   with measurements scoped to portions of it, or does each supported local
   evaluation identify a distinct Process Profile?
5. What world-side entity identifies an out-of-hand, plate-crossing, contact,
   or path-crossing evaluation: a Process Boundary, a short Process part, a
   Temporal Region, or only a provider-defined information-layer evaluation?
6. When does a reported scalar measure actual Speed, and when is it an
   Estimate produced by a fitted or adjusted method?
7. What axes, origin, sign conventions, frame, and temporal scope are required
   before CCO Velocity or Acceleration may be asserted?

## Release and bat geometry

8. Which Bodily Component and Fiat Point supply the throwing-shoulder
   landmark, and which Fiat Point supplies the tracked Baseball location?
9. Through which shared Fiat Point is a ground-parallel Fiat Line constructed
   for arm-angle geometry?
10. Which actual ground or field geometry and reviewed Reference System ICE ground
    that line's direction?
11. Which Fiat Point of the Baseball Bat is selected as its tracked sweet spot,
    and which versioned Reference System supports that designation?
12. What accepted construction connects the sweet-spot Motion and its Velocity
    Process Profile to an actual tangent Fiat Line at an evaluation scope?
13. What vertical projection grounds attack angle, and what horizontal
    projection plus home-to-center-field geometry grounds attack direction?
14. For a swing-and-miss, what real evaluation entity corresponds to the
    provider's bat/ball path crossing without inventing a Bat-Ball Contact
    Process?
15. Is swing-path tilt an Angle Quality between two Fiat Lines, an orientation
    of a fitted Fiat Surface, or another world-side structure?

## Evidence and failure behavior

16. Which tracking method, model, and version evidence is required to preserve
    changes in provider semantics across seasons?
17. What happens when a value is null, not tracked, estimated, or not
    applicable?
18. Which equivalence tests must pass before any currently unresolved overlap
    with MLB-game becomes eligible for Statcast mapping?

## Negative tests

- No source field, source row, or Measurement ICE is a Speed, Velocity, Angle,
  Distance, Fiat Line, Process, Baseball, Baseball Bat, or Person.
- No scalar mph value is asserted directly on a Pitch Act, Motion Process, or
  Baseball.
- No Velocity is asserted without direction and reference-frame semantics.
- No temporal or spatial scope is established only by `release`, `plate`,
  `contact`, or another word in an IRI or label.
- No shoulder, sweet spot, tangent, reference line, plane, path crossing, or
  contact is invented from a numeric field alone.
- A swing-and-miss does not instantiate Bat-Ball Contact Process or
  Batted-Ball Motion Process.
- Statcast does not remap MLB-owned launch, trajectory, event, player, team, or
  game facts.
- Missing and estimated values are never silently treated as observed zeroes.
