# Pitching and contact queries

This family counts `PitchAct` individuals that precede a
`PitchBallMotionProcess`, mapped ball/strike/foul-tip processes associated to a
pitch through their shared event record, plate appearances faced, swings, and
batted-ball motion processes. Contact queries preserve the sequence from a
swing or bunt act to contact and then batted-ball motion. Pitch speed, spin,
break, and launch measurements remain excluded because those measurement
properties are not yet approved in the ontology mapping.

## Current execution boundary

The query shapes are aligned to the intended full pattern, but the selected
RML processor does not currently expand the parent-side
`playEvents[*].playId` join across every nested pitch. On the checked-in
fixture, pitcher, batter, role, and plate-appearance links therefore cover
terminal matching pitch events rather than all 282 pitches. Pitching and
contact totals must not be published until that mapping/execution issue is
corrected and coverage assertions are added. The queries do not infer missing
people from IRI text or source strings.
