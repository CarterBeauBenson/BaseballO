# Source and ontology evidence

This is a TBox-curation proposal. Source evidence therefore includes the active
BaseballO declarations, existing accepted design records, the pinned BFO/CCO
snapshots, and the current MLB-game semantic audit. Existing mappings are
evidence of current operational assumptions, not evidence that those
assumptions are ontologically correct.

## Frozen debt scope

`Baseball/governance/ontology-curation-debt.json` records 31 unique classes
across dangling-parent, multiple-direct-parent, missing-annotation, and missing
BFO/CCO-grounding findings. Its status is `frozen-unreviewed-not-accepted`;
this proposal does not change that status.

The current declarations occur at:

- `Baseball/ontology/BaseballO.ttl:358-377` for challenge acts;
- `Baseball/ontology/BaseballO.ttl:405-441` for ball-motion processes;
- `Baseball/ontology/BaseballO.ttl:747-815` for replay leaves; and
- `Baseball/ontology/BaseballO.ttl:1405-1530` for the other 18 classes.

Related restrictions occur at:

- `Baseball/ontology/BaseballO-axioms-overlay.ttl:235-243` for challenges;
- `Baseball/ontology/BaseballO-axioms-overlay.ttl:259-280` for motion;
- `Baseball/ontology/BaseballO-axioms-overlay.ttl:769-845` for teams, time,
  coordinates, double plays, and foul tips; and
- `Baseball/ontology/BaseballO-axioms-overlay.ttl:900-983` for replay.

## Pinned BFO and CCO parent evidence

| IRI | Label | Evidence in `CommonCoreOntologiesMerged.ttl` |
| --- | --- | --- |
| `cco:ont00001180` | Organization | lines 15142-15149 |
| `cco:ont00000192` | Facility | lines 5496-5505 |
| `obo:BFO_0000023` | role | Pinned BFO class already used by BaseballO |
| `obo:BFO_0000202` | temporal interval | lines 3648-3655 |
| `obo:BFO_0000203` | temporal instant | lines 3658-3664 |
| `cco:ont00000540` | Temporal Instant Identifier | lines 8845-8859 |
| `cco:ont00000275` | Spatial Reference System | lines 6275-6285 |
| `cco:ont00000686` | Designative Information Content Entity | lines 10325-10341 |
| `obo:BFO_0000029` | site | lines 3411-3428 |
| `cco:ont00001133` | Motion | lines 14694-14699 |

The current temporal parents are broader than the definitions. BFO
`BFO_0000038` is a one-dimensional temporal region, whereas `BFO_0000202` is a
continuous Temporal Interval (lines 3493-3512 and 3648-3655). BFO
`BFO_0000148` may consist of multiple separated instants, whereas
`BFO_0000203` is one Temporal Instant (lines 3626-3636 and 3658-3664).

## Direct ICE value and reference-system dependency

The timestamp and coordinate candidates keep information content distinct from
both its world-side referent and any material carrier. They follow the user's
required direct-content pattern, but only if the separate
`ice-direct-values-and-units` proposal is accepted first.

- CCO Information Content Entity `ont00000958` is a BFO generically dependent
  continuant (lines 12960-12974).
- CCO Information Bearing Entity `ont00000253` is a distinct Object that may
  carry an ICE (lines 6064-6079).
- Independent continuant and generically dependent continuant are disjoint
  (lines 20433-20438).
- The pinned CCO snapshot currently puts text, datetime, URI, decimal, double,
  date, boolean, and integer value-property domains on Information Bearing
  Entity (lines 3071-3145).
- The pinned snapshot also puts `uses measurement unit` `cco:ont00001863` and
  `uses reference system` `cco:ont00001912` on an Information Bearing Entity
  (lines 1736-1744 and 2222-2230). The pinned vocabulary has no property named
  "uses reference unit."

Those pinned domains would infer that an ICE using the properties is an IBE.
The shared proposal removes that category error by making the properties apply
to Information Content Entity directly. On that dependency, a Baseball
Timestamp ICE directly has its datetime value and a Baseball Field Coordinate
ICE directly uses its reference system. A physical carrier can still carry the
ICE, but no carrier is required merely to attach the value or reference system.

The dependency is fail-closed: this package's direct datetime and reference-
system restrictions may be accepted and implemented only after, or atomically
with, an accepted `ice-direct-values-and-units` decision. If that foundation is
not accepted, those restrictions remain withheld rather than inferring that an
ICE is an Information Bearing Entity.

## Coordinate evidence limitation

The MLB-game schema inventory observes `hitData.coordinates.coordX` and
`coordY`, but the active mapping emits coordinate, reference-system, and Site
individuals without the values. The current semantic audit says to disable the
partial pattern or complete an ontologist-approved geometry model:
`Baseball/sources/mlb-game/SEMANTIC-AUDIT.md:55-58`.

This draft gives the three existing coordinate-related classes coherent
candidate meanings while marking executable use unresolved. It does not claim
that MLB values are distances, pixels, actual ball locations, or measurements
in any particular coordinate system.

## Double-play and foul-tip limitations

The mapping selects `double_play` and `grounded_into_double_play` result codes
at `Baseball/sources/mlb-game/mapping/mlb-game.rml.ttl:390-403` and types result
individuals at lines 1204-1214. A source classification may support an
institutional result, but it does not by itself establish either the official
classification criterion or a physical ground-ball profile.

An earlier candidate added Grounded Into Double Play Rule, Judgment Act, and
Decision ICE classes. That did not solve the gap: the Process, Rule, Judgment,
and Decision received their meaning only by referring around a closed cycle,
while ordinary preceding Batted-Ball Motion did not distinguish the result
from other Double Plays. Those support terms and axioms are removed. The
existing `GroundedIntoDoublePlayProcess` remains frozen rather than receiving
a cosmetically complete but semantically empty repair.

The mapping already types one foul-tip individual both `StrikeProcess` and
`FoulTipProcess` at lines 1750-1752 and 2198-2200. It maps the foul-tip
information individual under a `/decision/` IRI as output of
`FoulTipJudgmentAct` at lines 2957-2967. That supports the candidate foul-tip
genera while still requiring a later one-game semantic proof.

## Accepted replay design evidence

The archived replay record defines Manager and Player Challenge Acts as
intersections with `ChallengeAct` at
`Baseball/archive/design-records/replay-review/README.md:130-142`. It defines
the eight transition leaves using their final judgment kind as genus and the
affirming/overturning groups as unions at lines 147-213. The proposed taxonomy
follows that record; it does not resolve the separate MLB-game blocker about
synthesized opposite original decisions.
