# Source evidence

No new Statcast payload is downloaded or retained by this proposal. The
evidence comes from the archived field-level investigation, the current MLB
game source inventory, the pinned ontology, and the ontologist's stated
process-profile direction.

## Provider documentation already recorded

The archived Statcast investigation cites MLB Baseball Savant CSV documentation
at <https://baseballsavant.mlb.com/csv-docs>. That documentation describes
`release_speed` as a release-velocity value and records a method change:
2008-2016 values are PitchFX-derived and adjusted, while 2017+ values are
Statcast out-of-hand values. This supports preserving method-era provenance and
blocks silent identity across the change.

The same investigation records that `effective_speed` is normalized using
actual speed, release extension, and an average Major League extension. It is
therefore a derived provider metric, not evidence for a second directly
observed physical Speed.

## MLB-game overlap

The current MLB game feed inventory already supplies pitch `startSpeed`,
`endSpeed`, initial velocity components `vX0`, `vY0`, and `vZ0`, acceleration
components, extension, and other trajectory facts. The accepted Statcast
field-selection record consequently classifies:

- `release_speed` as unresolved against MLB `startSpeed`;
- `vx0`, `vy0`, and `vz0` as already supplied by MLB-game;
- `effective_speed` as unresolved pending its exact algorithm/reference; and
- pitch identity, player identity, and game keys as duplicate or join-only.

Those classifications remain in force. Wider Statcast history or missing MLB
mapping coverage does not make the same assertion type genuinely additional.

## Ontology evidence

The pinned vocabulary supplies:

- Pitch-Ball Motion Process (`base:PitchBallMotionProcess`), a Baseball
  Physical Process in which a Baseball moves following a Pitch Act;
- Baseball (`base:Baseball`);
- BFO Process Profile (`obo:BFO_0000144`), an occurrent part of a Process by
  virtue of a rate or pattern of change in an attribute of participants;
- CCO Speed (`cco:ont00000830`), a Process Profile characterized by the
  magnitude of an object's motion with respect to a frame during a time period;
- CCO Velocity (`cco:ont00000763`), a Process Profile characterized by Speed
  and direction with respect to a frame of reference;
- Measurement Information Content Entity (`cco:ont00001163`);
- Miles Per Hour Measurement Unit (`cco:ont00001602`);
- Cartesian Coordinate System (`cco:ont00001351`);
- `has occurrent part` (`obo:BFO_0000117`);
- `has participant` (`obo:BFO_0000057`);
- `is a measurement of` (`cco:ont00001966`);
- `uses measurement unit` (`cco:ont00001863`);
- `uses reference system` (`cco:ont00001912`); and
- `has decimal value` (`cco:ont00001769`).

The minimum scalar Speed pattern therefore requires no new class or property.
The exact structure for a time-local sample and a fully represented direction
may still expose a gap; this package asks that question rather than embezzling
the missing structure into a field-specific ICE.

## Ontologist direction captured by the draft

Speed is not constant throughout a ball-motion Process. The profile is the
occurrent "time shot" or pattern of changing motion that is measured; the
Pitch-Ball Motion Process itself is not 90 mph. BaseballO should use CCO
Process Profiles to keep that world-side target distinct from the measurement
ICE.

"Time shot" is intentionally not treated as a formal Temporal Instant in this
draft. Provider method evidence must determine whether the value refers to an
instant, a plane crossing, a short interval, or a fitted model evaluation.
