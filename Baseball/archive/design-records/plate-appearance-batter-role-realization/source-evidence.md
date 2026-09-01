# Source and ontology evidence

## Authoritative semantic relations

The pinned BFO/CCO dependencies distinguish the relevant categories and
relations:

- `BFO_0000015` Process is an occurrent.
- `BFO_0000023` Role is a realizable entity and specifically dependent
  continuant.
- `BFO_0000197` `inheres in` relates a specifically dependent continuant to
  its bearer.
- `BFO_0000055` `realizes` relates a Process to a Realizable Entity.
- `BFO_0000054` `has realization` is the inverse direction.
- CCO Stasis is a Process in which some independent continuants endure without
  the relevant change.
- CCO Stasis of Role represents unchanged role-bearing during a Temporal
  Interval. It is not the realization of the Role.

Consequently, persistence and realization are different assertions. A Stasis
may be useful when the evidence supports an interval of unchanged
role-bearing, but it cannot substitute for the baseball Process that realizes
the Role.

## Accepted BaseballO entities

BaseballO already contains the required classes and relations:

- `PlateAppearance` is a Process and is an occurrent part of a `HalfInning`.
- `BatterRole` is a Role borne by a Person.
- `BatterAct` is a `PlayerAct`; accepted subclasses include `SwingAct` and
  `BuntAct`.

No new BaseballO class or object property is required.

## MLB game evidence and identity

Each accepted MLB game play supplies one plate-appearance record with an
`about.atBatIndex`, a batter identifier, a pitcher identifier, and an
institutional resolution. The record supports:

- one game-scoped Plate Appearance Process;
- the batter Person as a participant in that Process;
- one stable Batter Role IRI, `data/player/{playerId}/role/batter`, inhering in
  that Person; and
- one game-scoped Batter Act that is an occurrent part of the Plate Appearance,
  has the batter as participant, and realizes that same role.

The generic Batter Act represents the batter's intentional activity throughout
the turn and provides the common counting grain even when no swing or bunt is
recorded. Pitch-event details separately support more specific Swing Acts and
Bunt Acts. Those Acts may realize the same Batter Role and be parts of both the
generic Batter Act and the Plate Appearance.

The MLB game source does not establish the exact beginning and ending of a
player's career. The stable role identity expresses reuse across available
games. A Batter-Role Stasis may express unchanged role-bearing, but neither it
nor the Plate Appearance substitutes for the Batter Act's realization of the
Role.

## Validation evidence boundary

These accepted graph invariants belong in the MLB-game authoritative SHACL
profile. The existing NiFi RDF lane has a distinct post-RML validation stage
that invokes that profile and refuses to load a nonconforming graph. Structural
source checks and RDF serialization checks may remain in supporting scripts;
the semantic answers above are owned by SHACL so that local, NiFi, and packaged
validation use the same version-controlled contract.
