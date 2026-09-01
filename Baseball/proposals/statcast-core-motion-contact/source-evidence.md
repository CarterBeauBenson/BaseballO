# Source evidence

Evidence was inspected transiently on 2026-08-30. No API or CSV payload was
saved in the repository.

## Official MLB evidence

- Baseball Savant CSV documentation:
  <https://baseballsavant.mlb.com/csv-docs>
- Statcast attack angle glossary:
  <https://www.mlb.com/glossary/statcast/attack-angle>
- Statcast attack direction glossary:
  <https://www.mlb.com/glossary/statcast/attack-direction>

The CSV documentation currently exposes 115 documentation-card identifiers.
After normalizing its repeated pitcher, catcher, and velocity-component
headings, these are the same 113 field semantics covered by the accepted
inventory.

Relevant evidence:

- release speed mixes adjusted 2008–2016 PitchFX values with 2017+ Statcast
  out-of-hand values while claiming a common scale;
- release positions are expressed in feet from the catcher's perspective but
  the page does not fully identify origin, axes, release plane, or temporal
  evaluation;
- plate X/Z change from a front-of-plate convention through 2025 to a
  middle-of-plate convention beginning in 2026;
- spin axis is an angular value in a specified two-dimensional X–Z convention;
- arm angle refers to a ground-parallel line and a shoulder-to-ball line but
  does not identify the shared point or precise temporal evaluation;
- attack angle and attack direction concern motion of the bat's sweet spot;
- the official glossaries evaluate those attack metrics at contact, or at a
  provider-defined bat/ball path crossing for a swing-and-miss;
- swing-path tilt concerns fitted geometry from the bat path during the final
  40 milliseconds before contact;
- the intercept component descriptions call the values distances, while their
  field names imply signed subtraction along X and Y axes.

These descriptions support the review questions but do not independently
supply every world-side point, line, frame, Process Boundary, Temporal Region,
or Algorithm required for executable RDF.

## Existing BaseballO and MLB-game evidence

The following accepted classes already provide the world-process backbone:

- `BaseballGame`, `PlateAppearance`, `PitchAct`, `SwingAct`;
- `PitchBallMotionProcess`, `BatBallContactProcess`,
  `BattedBallMotionProcess`;
- `Baseball`, `BaseballBat`, `HomePlate`, `BaseballFieldSite`;
- `AngleQuality`, `DistanceQuality`;
- BFO Process Profile and CCO Speed, Velocity, Acceleration, Measurement ICE,
  and Measurement Unit classes, plus BaseballO's generic-CCO-grounded
  Baseball Field Coordinate Reference System ICE.

The MLB-game source inventory already supplies the identity, event structure,
trajectory components, pitch movement, release/plate observations, launch
measurements, batted-ball type, projected distance, and display coordinates
listed as duplicates or unresolved overlaps here. Current mapping debt in that
source does not transfer ownership to Statcast.

The accepted `statcast-nonduplicate` review approved the intensional class
`BaseballBatSweetSpotFiatPoint`, but that class is not currently declared in
the authoritative ontology files. This draft therefore uses a generic Fiat
Point selected by a Designative ICE and makes implementation of the accepted
specialization an explicit pre-RML question rather than assuming it exists.
