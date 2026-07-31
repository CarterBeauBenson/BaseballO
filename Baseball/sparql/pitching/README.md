# Pitching and contact queries

This family counts `PitchAct` individuals that precede a
`PitchBallMotionProcess`, mapped ball/strike/foul-tip processes associated to a
pitch through their shared event record, plate appearances faced, swings, and
batted-ball motion processes. Contact queries preserve the sequence from a
swing or bunt act to contact and then batted-ball motion. Pitch speed, spin,
break, and launch measurements remain excluded because those measurement
properties are not yet approved in the ontology mapping.

## Execution coverage

The execution harness supplies ancestor context to nested pitch records in an
isolated derived JSON copy because the selected RML processor cannot expand
the parent-side `playEvents[*].playId` reference. The authoritative JSON is
unchanged. Fixture validation requires complete plate-appearance, person, and
role context on all 282 pitches, all 134 swing/bunt acts, and all 112 contacts.
The queries do not infer people from IRI text or source strings.
