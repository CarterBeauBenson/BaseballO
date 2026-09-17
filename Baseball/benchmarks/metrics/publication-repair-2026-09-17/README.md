# Publication repair evidence — September 17, 2026

The failed season refresh exposed two implementation omissions in already
accepted patterns. The repairs do not add ontology vocabulary or object
properties.

* Existing PA-start occupancy now emits the same persistent Baserunner Role,
  Stasis of Role and open Temporal Interval as runner movement evidence.
  A pinch runner stranded without another movement no longer loses its role
  declaration. No new movement, realization or role transition is inferred.
  The previously published C3 decision preserves the incoming person's
  persistent role; the freeze change covers only this RML repair and its
  generated Mermaid manifest. Ontology and context-builder pins are unchanged.
* Query-index v3 preserves the accepted separate actual Batter Acts inside one
  PA. Existing index predicates retain per-act actor support. SHACL requires
  exact PA/act participant agreement and the same participant set on result/hit
  projections. Each act still has exactly one actor. Statistical credit and
  official PA qualification remain separate. Valid v1/v2 products stay usable
  through the explicit compatibility bridge without changing their manifests.
* Replay plans retain, list and defer unchanged reversed-clock failures when
  source and reconciler hashes match the failed evidence. They remain in
  quarantine, never count as resolved, and do not occupy the proof slots needed
  to release other repaired inputs. A source/reconciler change permits retry.
* Terminating PowerShell errors are now appended to the stage log before being
  rethrown. Previously the log could end at successful preflight output.

## Focused checks

`proof.json` records exact inputs and outputs. The 69 unit tests cover role
serialization, participant support and rejection cases, index consumers,
SQL compatibility, and replay behavior. A separate focused PowerShell check
confirmed that a terminating stage exception is both retained and rethrown.

Game 823682 (the pinch runner stranded at first) passed production RML and Jena
authoritative SHACL on its exact retained input. Game 823523, whose earlier RML
log did not retain a cause, also passed the same isolated proof; its original
failure was not reproduced. Its context additionally passed with the existing
prior-manifest identity checks. These are conformance proofs, not declarations
that every metric population is complete.

All four previously failed substitution games—822800, 822854, 822918 and
823048—passed the final Jena index profile. For 822800, Jena also returned exact
source/index equivalence for outcomes by player, outcomes by season, and PA
participation by player/season. A trial using rdflib's query engine stalled on
the source join and was stopped; production Jena supplied the recorded proof.

## Remaining source decision

The live MLB endpoint still returned reversed clock pairs for games 822753,
823302, 823532 and 823631. During this repair the running batch recorded another
case in 823740. The existing source gate correctly rejects these responses.
[T1](../../../proposals/mlb-game-clock-conflict-isolation/README.md) proposes a
bounded way to preserve independently valid evidence without inventing timing.
It remains under review; no timing selection or source-admission rule changed.

NiFi owns the subsequent replay, promotion and SQL/dashboard publication.
These developer results do not claim that replay or publication is complete.
