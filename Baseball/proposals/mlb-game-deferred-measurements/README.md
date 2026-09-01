# MLB-game deferred measurements

Status: **under review**

This package reviews every currently unmapped physical or provider-score value
under `feed/live` `pitchData` and `hitData`. It addresses semantic blocker
`MLB-GAME-008`. It proposes no executable RML, SHACL, ontology change, or
backfill yet.

The umbrella measurement patterns remain here. Exact ontology review has been
split into three focused packages:

- [`baseball-pitch-and-batted-ball-classifications`](../../archive/design-records/baseball-pitch-and-batted-ball-classifications/)
- [`baseball-season-and-transaction-periods`](../../archive/design-records/baseball-season-and-transaction-periods/)
- [`baseball-strike-zone-geometry`](../../archive/design-records/baseball-strike-zone-geometry/)

Those packages do not authorize executable RML until the ontologist accepts
their named classes, definitions, and axioms.
