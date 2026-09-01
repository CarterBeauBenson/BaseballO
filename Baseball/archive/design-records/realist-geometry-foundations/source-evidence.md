# Source and ontology evidence

## Ontologist-provided precedent

The ontologist directed BaseballO to reuse the realist pattern already stated
in the Provisional Football Ontology:

- angle is a Relational Quality involving two Fiat Lines that intersect at a
  shared Fiat Point;
- distance is a Relational Quality involving two nonidentical Fiat Points.

Reference:
<https://github.com/CarterBeauBenson/ProvisionalFootballOntology-Soccer-/blob/main/FootballOntology.ttl>

The proposal preserves that world-side structure and does not copy a CSV
column into a class label.

## Authoritative BFO/CCO coverage

The pinned dependencies already provide all required parents and relations:

| Need | Existing term |
| --- | --- |
| relational quality genus | BFO `Relational Quality` (`BFO_0000145`) |
| line relatum | BFO `Fiat Line` (`BFO_0000142`) |
| shared endpoint/intersection | BFO `Fiat Point` (`BFO_0000147`) |
| dependent-continuant bearer relation | BFO `inheres in` (`BFO_0000197`) |
| line-to-point parthood | BFO `has continuant part` (`BFO_0000178`) |
| measurement content | CCO `Measurement Information Content Entity` |
| measurement target | CCO `is a measurement of` |
| measurement unit | CCO `uses measurement unit` |
| reference system | CCO `uses reference system` |

No new object property is needed for the accepted core pattern.

## MLB venue evidence

The official venue response can expose `fieldInfo.leftLine`, `leftCenter`,
`center`, `rightCenter`, and `rightLine`. Those strings are useful only after
their endpoints, units, and field configuration are established. The generic
Distance Quality supplies the world-side target; a source-specific review must
still establish which Fiat Points each label denotes.

## Statcast evidence

The official Statcast CSV documentation defines several angular fields by
reference to ground-parallel, shoulder-to-ball, bat-travel, home-to-center,
and swing-plane geometry. That evidence supports the need for Angle Quality,
but not a field-specific ICE masquerading as the angle.

The intercept fields are described as X- and Y-direction distances between an
intercept point and the batter's center of mass. Their names include a
subtraction order, so sign and axis orientation matter. The generic Distance
Quality does not by itself establish a directed component. They are recorded
as an unresolved nearby case, not forced into this proposal.

Official source documentation:
<https://baseballsavant.mlb.com/csv-docs>
