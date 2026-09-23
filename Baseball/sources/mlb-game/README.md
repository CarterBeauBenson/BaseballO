# MLB game source module

This module is the complete source-owned boundary for the MLB Stats API
`feed/live` game response.

- [`schema/`](schema/) records the observed source contract.
- [`mapping/`](mapping/) contains the only executable RML and source-field IRI
  policy for this source.
- [`shacl/`](shacl/) validates only authoritative RDF emitted by this source.
- [`review/`](review/) owns the reviewed pattern manifest used to generate the
  post-implementation Mermaid regression catalog and the machine-readable
  semantic-status record.
- [`SEMANTIC-AUDIT.md`](SEMANTIC-AUDIT.md) records the current anti-flattening
  review and the gates for extending coverage.

NiFi owns acquisition, dependency ordering, isolated execution, validation,
promotion, retry, and provenance for this module. Integration with other source
families happens only after promotion, through dependency-declared SPARQL over
the triple store. This module must never import another source's RML or SHACL.
Its registered source-owned NiFi process group is `MLB Game`. That group owns
proof requests, schedule discovery, completed-game fanout, per-game semantic
promotion, deferred corpus materialization, cleanup, and source-local failure
handling. There is no active NiFi manual inbox.

Schedule discovery deduplicates by stable MLB `gamePk`. When the same game has
an official postponed occurrence and a later completed occurrence, the lane
persists compact schedule evidence and maps one game plus the postponement
declaration, its old and revised Schedule Plans, their canonical Days, and any
provider reason as nominal evidence. It does not assert that the provider
reason is a world-side weather cause. Parser failures preserve the original
response bytes for bounded retry or quarantine.

A schedule request that arrives while the current mapping and SHACL still need
a bounded proof remains inside the NiFi lane. NiFi retries the proof-release
readiness check every 30 seconds for up to 30 minutes, releases the request as
soon as the proof completes, and uses source-local schedule quarantine only if
that readiness window is exhausted.

The module is operationally active and its current pinned contract is
semantically `approved`. NiFi runs it asynchronously and applies the
source-owned SHACL profile before promotion.
[`review/semantic-status.json`](review/semantic-status.json) is the machine
gate; [`SEMANTIC-AUDIT.md`](SEMANTIC-AUDIT.md) preserves the original audit and
records how the accepted 2026-08-31 migrations resolved it.

Future MLB-game fields still require reviewed proposals. Other MLB APIs and
Statcast remain detachable source modules with their own Mermaid, RML, SHACL,
and NiFi lanes; no later source may broaden this module implicitly.

The bounded proof passed and the source-owned 05:00 Eastern trigger is enabled.
Schedule runs materialize SQL once per completed batch rather than once per
discovered game. A run's submission, promotion, quarantine, cleanup, and
materialization status must be read from terminal NiFi evidence; this README
does not track a live batch.

For an explicitly authorized source recovery whose proof must wait for a
serving rebuild, the existing periodic batch worker can own the sequence through
[deferred proof and refresh recovery](pipeline/DEFERRED-RECOVERY.md). It submits
the normal proof and bounded backfill only after their prerequisites complete.
This is not the entry point for metric/SQL changes or targeted RDF additions:
it replaces complete game graphs. Those tasks must follow the
[incremental-work policy](../../../AGENTS.md#incremental-work-and-minimal-manual-validation).

Contradictory source clocks follow the accepted [T1 decision](../../archive/design-records/mlb-game-clock-conflict-isolation/README.md).
When an event or PA has an end earlier than its start, neither boundary clock
measurement is emitted. The source bytes, conflict values and source paths stay
in the retained reconciliation evidence. Existing acts, intervals, participants,
results and independently supported automatic count awards remain available.
Unsupported automatic-award precedence is omitted. A disputed final PA header
also cannot supply the game's end measurement.

Reconciliation version 2 retains all diagnostics in `issues`, separates
`blockingIssues` from `clockConflicts`, and uses `status` for structural source
consistency. It does not certify complete timing or metric populations. The
registered `clock-admission` SHACL gate checks both omission and preservation
before promotion. Runner-history and count admissions retain their own temporal
dependencies and completeness census; T1 does not admit incomplete leaderboards.
The quarantine planner retries a retained clock failure when the reconciler
fingerprint changes. It does not need a new source response or rewritten JSON.

The existing `Quarantine Remainder Retry Request` accepts an optional JSON
payload with `gamePks` (an explicit array of game ID strings) and
`afterServingBuild` (one existing SQL build ID). NiFi checks that the selected
games belong to the retained replay plan and that their input hashes still
match. It waits for that SQL build to finish reading RDF before emitting the
selected retries. A six-hour timeout, missing progress, or an unknown state
fails the request without releasing inputs. The ordinary two-attempt stage
limits, SHACL checks, atomic graph-pair promotion and quarantine retention still
apply. An empty request preserves the existing remainder-selection behavior.

The September 23 quarantine diagnosis found 30 games eligible for a retry
under existing fixes. The remaining 13 are documented in the draft
[Q5/Q6 source-contract review](../../proposals/mlb-game-quarantine-boundaries/README.md).
Those source-selection and admission changes are not implemented by the retry.
