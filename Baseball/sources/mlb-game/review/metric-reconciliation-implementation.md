# Metric source reconciliation — 2026-09-14

This is a historical record of the initial September 14 mechanical checker.
E1 and C1 source operation were subsequently explicitly accepted in
[the archived decision](../../../archive/design-records/metric-source-c1-operation-2026-09-14/review.json).
The personal-history mapping, counted-foul additions and defensive-act mapping
are implemented. The barriers and rejected approval attempt below describe the
earlier stage, not current acceptance or authorization. Use
[metric readiness](../../../serving/METRIC-READINESS.md) for remaining work.

At that initial stage the checker was implemented within the existing NiFi
source lane, without changing RML, ontology, semantic fingerprints or metric
admission. The user requested
progress conditional on not requiring an RML mapping or ontology class.
Formal acceptance of E1 had not yet been recorded at that point.

The mechanical checker now retains revision-bound source membership before
mapping and transient cleanup. It checks play/inning/scoring membership,
movement-event joins and run totals while preserving unknown observations.
The actual immutable 824315 fixture passes these checks with 77 plays, 413
events and 114 movements. Nine focused tests verify missing/duplicate event
and play detection, inconsistent totals, missing views/revisions, retry
determinism, raw-byte preservation and the stage integration. The PowerShell
stage parses successfully.

This is implementation of a necessary source-evidence component, **not full
operation of the metrics**. No new live metric has been released by it.

## Historical barriers under the initial mapping constraint

- The accepted C1 runner whole is an existing BFO Process, but the current
  `mapping/mlb-game.rml.ttl` has no personal `runner-trajectory` mapping.
  Its accepted graph pattern is described in
  [the source contract](runner-continuity-source-contract.md). SHACL and a
  query can recognize that pattern; they cannot make its missing evidence
  appear. Producing these assertions requires supported source histories and
  a mapping implementation using the already accepted terms.
- Exact pitch/non-pitch observations and count values are present in the raw
  source, but the existing RML does not expose an exact count-state sequence
  for Recovery Quality. Counting `pitchIndex` would be wrong: PA 43 contains
  three indexed entries, including one pickoff, and only two actual pitches.
  The missing graph contract/mapping cannot be replaced by raw-JSON scoring.
- Complete defensive act sequences and the all-review-eligible decision
  census still need the evidence identified in
  [the full-operation review](../../../proposals/graph-native-metric-suite-batch-review/full-operation-source-admission.md).

Automatic approval review rejected an attempt to record conditional wording
as formal E1 acceptance. That draft record was removed; no approval status
was committed. The implementation here does not depend on accepting E1 and
does not infer complete history from a consistent source inventory.
