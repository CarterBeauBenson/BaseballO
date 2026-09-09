# Minimal-change implementation boundary

Prepared 2026-09-08. Engineering assessment for the existing MLB-game lane;
not an accepted semantic decision or evidence of completed reprocessing.

Subsequent disposition: the user explicitly approved implementing the fix.
The concrete A1 parthood slice is
[accepted and implemented separately](../../archive/design-records/mlb-game-batted-runner-resolution-containment/README.md).
The plan below records the full remaining boundary; its unspecified patterns
are not made concrete by that approval.

## Use the existing per-game replacement path

The smallest supported deployment is a targeted extension of the current
mapping followed by bounded replacement of affected game graph pairs. Keep
the existing game, PA, runner-record and persistent-role identities wherever
their accepted identity contracts apply. The size of the mapping edit and
the number of historical games needing its new evidence are separate issues.

The current pipeline evaluates the complete mapping for each submitted game.
It does not implement a validated delta-RML merge. Thus a small RML edit can
require full reprocessing of each selected game, without resetting the
database or reacquiring unrelated source modules. Historical games can be
updated in batches after the proof succeeds.

Do not add a supplemental graph or direct `INSERT DATA` patch as a shortcut.
That would need a contract for joint validation, corrected-source deletion,
provenance, graph completeness and downstream invalidation. Existing
destination artifacts, IRI strings and PA containment do not recover the
missing assertions with accepted meaning.

## Existing machinery to reuse

| Component | Verified behavior | Implication |
| --- | --- | --- |
| [run-rml.ps1](../../scripts/pipeline/run-rml.ps1) | Uses the current MLB-game mapping and context builder, checks runtime semantic admission, hashes input/output and records mapping/context/shape provenance | Extend the owning mapping after acceptance; do not create another ingester or alter frozen admission preemptively. |
| [stage.ps1](../../sources/mlb-game/pipeline/stage.ps1), `shacl` | Validates generated per-game RDF before promotion | Add only constraints implementing the accepted new assertions. |
| [stage.ps1](../../sources/mlb-game/pipeline/stage.ps1), `promote` | Prepares graph backups, loads authoritative RDF, builds the query index, verifies the pair, records promotion evidence, then commits; invokes restoration on failure | Reuse this per-game replacement lifecycle. |
| [graph-pair-transaction.py](../../scripts/pipeline/graph-pair-transaction.py) | Snapshots both existing graphs; verifies backup hashes and restored graph isomorphism; supports recovery of prepared transactions | Previous graphs are recoverable during replacement. Backups are removed on commit, so they are not permanent historical versions. |
| [build-query-index.ps1](../../scripts/pipeline/build-query-index.ps1) | Builds from validated per-game RDF and runs authoritative/index equivalence before recording the current build | Preserve existing query semantics while extending authoritative evidence. A new metric index would require its own reviewed contract and equivalence. |
| [game_promotion_inventory.py](../../scripts/pipeline/game_promotion_inventory.py) | Recognizes a retained, hash-verified staged RML replacement over an existing promotion | Staged work does not by itself mean the old promoted graph is gone or has new metric coverage. |
| [check-source-proof-release.py](../../scripts/pipeline/check-source-proof-release.py) | Requires completed proof evidence matching current mapping and source-SHACL hashes | Prove the changed source before releasing a historical batch. |

Graph-pair replacement is recoverable, not a single atomic two-graph write:
the authoritative and index graphs are written sequentially. Live RDF readers
can encounter an intermediate pair. Existing immutable SQL builds remain
independent of those writes. Do not claim zero interruption for all Explorer
routes or advertise a partially rebuilt metric population as complete.

## Bound the future edit

1. Resolve A2's contribution meaning first, then complete the concrete A1 and
   A3-A6 world-side patterns. Proposed A2 wording: **attribute institutional
   consequences of the batter's result, without asserting that the batter
   physically caused every consequence**. This includes reviewing award paths
   for walks/HBP and explicitly excluding independent runner events. It does
   not decide error treatment, simultaneous-event ordering or state identity.
2. Add only accepted joins and state evidence in the existing context/RML
   components. Reuse existing acts, records, resolutions and decisions. Any
   additional state identity must be explicitly reviewed; do not mint a new
   Role per event or broaden the PA-start stasis definition implicitly.
3. Add the corresponding source-SHACL constraints and focused fixtures. Retain
   the accepted positive evidence and reject unknown attribution as unknown,
   rather than manufacturing zero progress or unchanged runners.
4. Prove one game, then a bounded diverse set including 566279 / PA 23,
   822693 / PA 36 and 823826 / PA 78. The latter two are negative cases for
   simplistic event-index and event-label attribution, not automatically
   complete metric fixtures.
5. Once semantic acceptance and proofs permit it, submit affected historical
   games through the existing NiFi lane in bounded batches. Checked-in inputs
   remain immutable; reacquired payloads follow the existing transient-input
   and quarantine policy. Preserve graph pairs until replacement validation
   and preserve recovery evidence throughout promotion.
6. Keep PAQ-1 and the current serving pointer available. Admit PAQ-2 only when
   the approved reference population has complete required evidence and its
   canonical SPARQL/SQL equivalence passes. A mixed-version corpus is not a
   complete league reference population merely because all graphs exist.

This assessment itself did not grant semantic approval. The subsequent A1
acceptance and [three-relation acceptance](../../archive/design-records/mlb-game-resolution-award-links/README.md)
authorize their bounded ontology, RML, SHACL and runtime-admission engineering.
The immediate-before state and metric-completeness decisions remain with the
ontologist. Neither acceptance changes the existing pipeline topology.
