# MLB game source module

This module owns the MLB Stats API `feed/live` game response boundary.
Ownership does not establish that every API field or case is mapped; coverage
is recorded separately in the source contract and mapping documentation.

The accepted [K1 repair](../../archive/design-records/mlb-game-strikeout-double-play/README.md)
uses `nifi/provision-compound-addition.ps1` to run the existing additive
transaction for five named games. Its worker acquires only a needed named
response, retains separate source provenance, selects the compound result and
its two existing outs, and adds only absent triples. The first game must pass
before the other four are selected. The ordinary admission owner then checks
the affected promoted graph against the retained witness; SQL remains RDF-fed.
No whole-game RML replay or corpus replacement is part of this repair.

- [`schema/`](schema/) records the observed source contract.
- [`mapping/`](mapping/) contains the only executable RML and source-field IRI
  policy for this source.
- [`shacl/`](shacl/) validates only authoritative RDF emitted by this source.
- [`review/`](review/) owns the reviewed pattern manifest used to generate the
  post-implementation Mermaid regression catalog and the machine-readable
  semantic-status record.
- [`SEMANTIC-AUDIT.md`](SEMANTIC-AUDIT.md) preserves the original anti-flattening
  review, its accepted resolution and the gates for extending coverage.

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

Schedule requests go directly from `Prepare Schedule Batch` to
`Acquire MLB Schedule`. The user removed the prior completed-sample prerequisite
on [October 1](../../archive/design-records/mlb-game-acquisition-gate-removal-2026-10-01/README.md).
Each acquired game still passes through its existing RML, source SHACL and
promotion stages. HTTP failures retain their bounded retry and quarantine
routes. The daily trigger remains 05:00 America/New_York.

For an existing installation, run `nifi/remove-acquisition-gate.py` to migrate
only these acquisition connections. It preserves queued schedule requests by
redirecting their existing queues to acquisition. Run it once more after any
recovered queue drains to remove the remaining stopped gate processors. It
does not stop source mapping, SHACL, promotion, SQL or repair workers.

The module is operationally active and its current pinned contract is
semantically `approved`. NiFi runs it asynchronously and applies the
source-owned SHACL profile before promotion.
[`review/semantic-status.json`](review/semantic-status.json) is the machine
gate; [`SEMANTIC-AUDIT.md`](SEMANTIC-AUDIT.md) preserves the original audit and
records how the accepted 2026-08-31 migrations resolved it.

Future MLB-game fields still require reviewed proposals. Other MLB APIs and
Statcast remain detachable source modules with their own Mermaid, RML, SHACL,
and NiFi lanes; no later source may broaden this module implicitly.

The source-owned 05:00 Eastern trigger is enabled.
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

The existing `Quarantine Replay Request` and `Quarantine Remainder Retry Request`
accept an optional JSON
payload with `gamePks` (an explicit array of game ID strings) and
`afterServingBuild` (one existing SQL build ID). NiFi checks that the selected
games belong to the retained replay plan and that their input hashes still
match. The plan request creates a bounded proof/remainder plan for its selected
games; the remainder request reuses an existing plan. NiFi retains the request
in a penalized queue until the named SQL build finishes reading RDF. Each
readiness check returns immediately; up to 720 checks at 30-second penalties
provide a bounded wait of approximately six hours or longer under load.
Missing progress, an unknown state or exhausted retries fail the request
without releasing inputs. The ordinary two-attempt stage
limits, SHACL checks, atomic graph-pair promotion and quarantine retention still
apply. An empty request preserves the existing remainder-selection behavior.

Current, selected repair and historical inputs carry separate queue priorities
through RML, SHACL and promotion. They share the existing bounded worker pool.
SHACL loads a game's RDF once into Jena and evaluates each existing profile
separately, preserving its report and admission outcome. The stage records load
and profile durations in `shacl-execution.json`.

The source-owned `Refresh Admission Evidence` worker diagnoses missing, stale
and previously withheld admission evidence independently of serving builds.
The original producer refresh requires exact retained input and local RDF
bytes. When a retained quarantined response is available, the worker instead
can run the six existing admission profiles against the promoted Fuseki graph,
independently of whether the batting check already finished. The existing
profile producer retains the validation response's hash separately from the
promotion input, and commits receipts only after a final promotion check.
Completed checks, including withheld outcomes, are reused for their exact
promotion and producer. Independent player checks and the single-batter B1 repair use
hash-bound retained censuses and read the existing promoted graph. The latter
also supports the known pre-T1 context: its reconciled census and exact
single-batter membership must still pass the unchanged B1 SHACL. Completed
repairs keep their original fingerprints and statuses. Retired temporary files
are not evidence that the authoritative Fuseki graph is missing. The worker
never reacquires, maps or promotes RDF, and never relabels an old fingerprint
as current.

When a whole-game runner-resolution check fails, the same worker can apply its
existing membership, participant and endpoint constraints to individual PAs.
`pa-resolution-admission.py` reuses the retained source census and the existing
promoted graph. A retained later response can use the existing graph-validation
census; its validation source hash stays distinct from the original promotion
input. The registered `pa-resolution-admission.ttl` changes the target
scope only. Unknown source-wide issues still block every PA; a bad PA cannot
admit its own progress. These receipts supplement the unchanged whole-game
proof and do not assert completeness of attribution, history order or TFS.
The SQL player projection can use an admitted PA's existing batting-progress
result and a certain positive contribution for Empty Game classification.
Unchanged game calculations and player partitions remain reusable.

The dashboard defaults to the full latest loaded season. Admission Evidence
prioritizes that season's missing game rosters, then games whose withheld batting
admission has no current individual-player check and failed runner-resolution
populations, before other season and older
work. This changes scheduling only; the existing source and SHACL checks still
decide which records can be used. Already checked players remain distinct from
unchecked players even when their whole-game admission is withheld.

The Q5 edit changed only `batter_participation_context` in the shared context
file. Runner-resolution, pitch-count and defensive proof code does not call
that definition, directly or transitively. Their exact pre/post implementation
pairs are recorded in `pipeline/context-proof-compatibility.json`. The focused
regression compares both context revisions, all remaining module code and
constants, each family's referenced context definitions and transitive calls,
and its complete producer/SHACL/validator fingerprint.

`admission-evidence.py` can therefore reuse those exact original proofs after
checking their promotion, graph/source identities and every retained validation
artifact. The original implementation fingerprint, status and issues remain
intact, with separate `implementationReuse` provenance. A previously withheld
proof stays withheld. Unknown code versions are ineligible for this reuse;
runner-boundary is excluded because it calls the changed definition. This
decouples an unrelated code edit without renewing evidence or changing source
semantics. NiFi maintenance reports `implementation-compatible` separately from
current, stale and missing evidence.

The same record identifies three exact pre-T1 positive-proof implementations:
batting, scoring-run and runner-resolution. T1 preserved their SHACL contracts
and replaced the source's all-issues prerequisite with its structural-issues
subset. A prior admitted proof with a hash-bound reconciled census and no
issues already passed the stricter prerequisite. Its source checks and graph
conformance remain usable. The regression verifies the original issue
predicates, T1's exact clock partition, unchanged census logic otherwise,
unchanged shapes/validator and (for runner resolution) unchanged context
function. These entries require an original admitted result and empty census
issues. They cannot upgrade prior withholding or introduce replacement times.

The September 23 quarantine diagnosis found 30 games eligible for a retry
under existing fixes. The remaining 13 are covered by the accepted
[Q5/Q6 source-contract decision](../../archive/design-records/mlb-game-quarantine-boundaries/README.md).
Q5 now selects the incoming batter only for an explicit event-zero, 0–0 pinch
hitter matching the final matchup and having subsequent batting evidence.
It supplies no outgoing identity, role transition or official statistical
credit. Q6 keeps the original source census inconsistent when it reports an
incomplete play or absent inning total. Clock and runner-history SHACL can
still check independently selected RDF. A numeric run-total disagreement or
other membership/identity failure remains blocking. The runner-history proof
can report `promotionAllowed: true` with `status: withheld`,
`sourceReconciled: false`, and `populationComplete: false`; that permits graph
promotion while keeping dependent metric populations withheld. All graph
conformance checks still run before promotion.

### W1/W2 targeted intentional-walk awards

The accepted [W1 decision](../../archive/design-records/mlb-game-zero-pitch-walk-prefix/README.md)
permits only the existing award selection after verified count-neutral PR or
mound-visit prefixes before four no-pitch VB records. `pipeline/targeted-award-addition.py`
slices seven existing award maps plus the four existing dependency maps accepted
in [W2](../../archive/design-records/mlb-game-w1-award-dependencies/README.md).
Dependencies must match the selected PA, runner row, runner and resolution.
It validates the selected award and its referents and posts only missing triples. The existing graph-pair transaction
owns rollback; only the affected query index is replaced. The original promotion
input and later retained selection witness keep separate hashes.

`nifi/provision-award-addition.ps1` installs the source-owned one-minute worker.
It runs the reviewed game 822864 first, then scans retained inputs in bounded
batches, with at most one game mutation per tick and two attempts per implementation.
Evidence is under `pipeline/control/mlb-game/award-addition/` and the ordinary
per-game evidence/promotion directories. The worker never acquires API inputs
or rewrites retained raw bytes. Positive proof compatibility and unchanged
independent/player proofs preserve their exact producer versions; new promotions
cannot inherit an old graph's receipts. This does not resolve unrelated runner,
defensive or review populations.

The first W1/W2 addition completed September 29 at 14:23 Eastern: game 822864,
PA 54, runner row 0 received 15 award triples and eight dependency triples.
The 27,823 existing triples were preserved; the resulting graph has 27,846.
Both the selected-award and scoped authoritative SHACL reports conform. This
is one repaired award pattern, not admission of the game's other unresolved PAs.

The separately accepted [R1 addition](../../archive/design-records/mlb-game-runner-pattern-completion/README.md)
completes existing runner patterns in its exact 26-game retained-input inventory.
`nifi/provision-runner-addition.ps1` installs `Add Approved R1 Runner Patterns`
under this source. The worker slices 27 unchanged maps for selected episodes,
endpoints, supported personal histories, placement and attribution dependencies.
It shares W1's additive graph transaction, preserves all base triples, and uses
the unchanged source-owned PA, history and affected authoritative constraints.
It checks the existing act, participant and resolution referents as well.
Game 823200 must complete before the remaining candidates run, one game per
tick with two attempts per implementation. Terminal evidence is under
`pipeline/control/mlb-game/runner-addition/`; promotion events refresh affected
query indexes and SQL. Submission and component tests do not establish metric
population. Unsupported timing, attribution, defense and review remain separate.

### Automatic repair observations

The existing `Add Approved Q7 Histories` NiFi worker publishes
`pipeline/control/mlb-game/repair-status.json` under the runtime state root
after each one-minute tick, including ticks deferred for memory. Its compact
summary is also recorded by the existing NiFi logger. `checkedAtUtc` identifies
the observation time; a stopped worker leaves an old report, not a current
health claim.

The report reads the six targeted repair queues, admission-maintenance
checkpoints, history-discovery inventory and game RML quarantines. It counts
uninspected promoted games and inspections bound to an older promotion or
implementation separately. Selected history jobs must match the worker's own
request/source/selection completion rule. Partial repairs, unavailable evidence,
unresolved sources, pending work and unreadable checkpoints keep
`recordedWorkClear` false even when the failed-execution count is zero. This is
a report of recorded work over promoted games, not certification of every API
field or proof of metric completeness.

History discovery now retains the same context census that failed its existing
identity guard, along with both input hashes, affected history identities,
the context's original issues and up to five relevant source plays. Partial
foul repairs include their unresolved PA IDs and hash-checked event/count
excerpts. These diagnostics preserve the original error and explain it;
they do not choose between contradictory source assertions.

Before draining repairs, the same worker now inspects up to 100 retained
promotion receipts, prioritizing games it has never inspected. This metadata
pass only writes named repair requests; source preparation and additive mapping
remain separate bounded steps. `awaitingSource` is pending work, not completion.
Inspection fingerprints cover the selector and accepted context, so reporting
or execution-queue edits do not invalidate the inspection census. An identical
selected request is retained even after its successful input cleanup.

When a retained response fails the existing history-identity check, discovery
may make one separately recorded acquisition for that named game under the
accepted September 30 scope. It keeps the conflicting input and diagnosis,
records the recovery request before acquisition, and applies the unchanged
identity check to the new bytes. A still-conflicting fresh response remains
blocked; it is not overwritten or fetched every tick.

An ambiguous roster still blocks player-participation admission. Its exact
producer, promotion and source witness are recorded under `familyFailures` in
the existing admission checkpoint; independent admission families continue.
The observer includes those failures even if other families are current.

The pending-batch SQL owner also applies its existing three-build retention
policy before launching another build. Retention therefore continues when
publication fails. It protects current report SQL and the newest candidates,
and leaves the dashboard's separate storage and all source/RDF evidence alone.

Existing source owners continue bounded discovery and retries. The observer
only writes its report: it does not acquire inputs, execute RML, query RDF,
change another checkpoint, or gate promotion/SQL. It runs after releasing the
repair lease and cannot hold a mapping slot. Reporting-code changes are outside
the history execution fingerprint. No new NiFi lane, schedule or validation
gate was introduced. Identity/source conflicts still require aligned evidence
or an accepted correction; an unchanged failed input is not refetched every
minute. Deployment uses the existing `nifi/provision-history-addition.ps1`.
