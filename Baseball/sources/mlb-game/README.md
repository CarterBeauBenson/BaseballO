# MLB game source module

This module owns the MLB Stats API `feed/live` game response boundary.
Ownership does not establish that every API field or case is mapped; coverage
is recorded separately in the source contract and mapping documentation.

On October 4, 2026, the user retired spring training and the World Baseball
Classic from active work. [`pipeline/work_scope.py`](pipeline/work_scope.py)
excludes spring-training games (`S`), exhibitions (`E`, including preseason
and WBC warmups), and WBC/qualifier leagues 160/159. `W` remains World Series.
The daily MLB schedule, repair selectors, quarantine replay, admission
maintenance, and new SQL builds use this scope. Existing RDF, raw evidence,
and historical repair results remain intact; exclusion never means a failed
case was repaired. Repair status separates retained games from active games.
No RML mappings, ontology terms, or graph rebuilds change with this policy.

The user's October 4 recovery order is API → RML → SHACL → Fuseki → SQL → UI.
Queued dashboard builds have no resource priority over source repairs. During
this recovery, `pipeline/control/mlb-game/repair-priority.json` in runtime state
holds new dashboard/report builds. NiFi releases that temporary hold once its
existing repair-status observer records the active backlog clear. This does
not create a permanent all-games prerequisite for later serving builds.
The shared heavy-worker lock and memory reserve remain in effect, and the UI
continues reading its last published SQL snapshot throughout the repair phase.
Within that temporary phase, unfinished history discovery and repairs take the
slot before recurring defense, foul and admission rechecks. Those workers resume
as soon as the history queue clears, then SQL resumes when the observer clears
the remaining upstream backlog. This prevents fixed one-minute timers from
continually starving history work without starting parallel JVMs.

Start with the [current RML repair plan](review/rml-audit-2026-10-03.md#current-repair-plan-and-scope)
and its [October 4 closure](review/rml-audit-2026-10-03.md#six-item-repair-implementation-october-4)
for diagnosed failures, implemented generic fixes and targeted historical
corrections. This README describes the module contract. Submission and repair
counts do not establish complete dashboard populations; those belong in
[metric readiness](../../serving/METRIC-READINESS.md).

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

New MLB-game semantic assertions still require review. Missed cases within an
accepted field are coverage debt in this lane. The other active MLB APIs have
[separate source modules](../README.md); future sources such as Statcast require
their own accepted boundary. No other source may broaden this module implicitly.

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

Independent admission proofs can be reused only through the exact recorded
implementation-compatibility chain in `pipeline/context-proof-compatibility.json`.
Reuse checks promotion, source/graph identity and retained validation artifacts;
the original fingerprint, issues and status remain intact, with separate
`implementationReuse` provenance. Unknown implementations are not compatible,
and a withheld proof never becomes admitted merely because code changed.

The accepted [Q5/Q6 decision](../../archive/design-records/mlb-game-quarantine-boundaries/README.md)
separates source completeness from independently checkable graph facts. Q5
selects an incoming batter only with the accepted replacement and actual
participation evidence; it does not invent the outgoing identity or statistical
credit. Under Q6's two named incomplete-source cases, clock, runner-history and
supported defensive-act SHACL can still check selected RDF. Missing source
totals keep complete metric populations withheld. Conflicting numeric totals,
identity failures and unsupported acts remain blocking. A graph-conforming
partial repair is not a complete population certificate.

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

`nifi/provision-award-addition.ps1` installs the source-owned worker with its
completed-scope timer stopped. Use `-Start` when submitting new authorized work.
It runs the reviewed game 822864 first, then scans retained inputs in bounded
batches, with at most one game mutation per tick and two attempts per implementation.
Evidence is under `pipeline/control/mlb-game/award-addition/` and the ordinary
per-game evidence/promotion directories. Ordinary repairs use retained inputs;
the separately bounded one-game recovery inventory handles the recorded input
retirement race described in the [pipeline guide](pipeline/README.md). Raw
source bytes remain unchanged. Positive proof compatibility and unchanged
independent/player proofs preserve their exact producer versions; new promotions
cannot inherit an old graph's receipts. This does not resolve unrelated runner,
defensive or review populations.

The separately accepted [R1 addition](../../archive/design-records/mlb-game-runner-pattern-completion/README.md)
completes existing runner patterns in its exact 26-game retained-input inventory.
`nifi/provision-runner-addition.ps1` installs `Add Approved R1 Runner Patterns`
under this source, with its completed-scope timer stopped unless `-Start` is
specified. K1's compound-repair provisioner uses the same on-demand default.
The worker slices 27 unchanged maps for selected episodes,
endpoints, supported personal histories, placement and attribution dependencies.
It shares W1's additive graph transaction, preserves all base triples, and uses
the unchanged source-owned PA, history and affected authoritative constraints.
It checks the existing act, participant and resolution referents as well.
Game 823200 must complete before the remaining candidates run, one game per
tick with two attempts per implementation. Terminal evidence is under
`pipeline/control/mlb-game/runner-addition/`; promotion events refresh affected
query indexes and SQL. Submission and component tests do not establish metric
population. Unsupported timing, attribution, defense and review remain separate.

The same worker now prioritizes accepted EG1 Empty Games completion, including
BK1 separately recorded balks. Its bounded inventory contains 455 games;
`pipeline/targeted-empty-game-addition.py` rechecks current published exclusions
and skips reader-resolved cases before acquiring or mapping anything. Retained
inputs come first; missing inputs may be acquired only for the approved games.
It adds missing selected PA/runner facts and their complete existing dependencies,
uses source SHACL, and emits the existing graph-promotion event. Terminal results
and unresolved selections live in `pipeline/control/mlb-game/empty-game-addition/`
and appear in the existing repair observer. A successful addition does not itself
mean that the corresponding full-season player total has reached SQL or the UI.
Its timer checks every 20 seconds so it can use the short gap between SQL
builds. The existing shared lease and memory check still allow only one heavy
worker. EG1 holds that lease for up to twenty serial attempts or ten minutes,
finishing the current game before yielding. A failed game retains the same
two-attempt limit and does not stop independent candidates. The admission
resume queue similarly processes at most ten checks or five minutes before
yielding, so stale eligibility checks can progress between SQL builds.

When a selected addition extends an exact contact or runner-history census,
EG1 retains the original obligations and adds only the newly selected facts
from the unchanged source selector. The receipt records both source witnesses,
the original census/shape hashes and counts, and the projection implementation.
Existing SHACL checks the resulting exact set. Original admission outcomes and
population-completeness claims remain unchanged; a partial history stays
partial. Balk checks use the existing `RunProcess` for a scoring resolution
and `SafeProcess` for a safe base advance.

### Automatic repair observations

The existing `Add Approved Q7 Histories` NiFi worker publishes
`pipeline/control/mlb-game/repair-status.json` under the runtime state root
after each one-minute tick, including ticks deferred for memory. Its compact
summary is also recorded by the existing NiFi logger. `checkedAtUtc` identifies
the observation time; a stopped worker leaves an old report, not a current
health claim.

The report reads its registered targeted repair queues, admission-maintenance
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
Inspection fingerprints cover the history selector and its relevant context
definitions, constants and imports. Unrelated main assembly, defensive selection,
terminal-clock selection, reporting and compatibility bookkeeping do not
invalidate that census; a relevant helper change still does. An identical
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

Existing source owners continue bounded discovery and retries. The observer
only writes its report: it does not acquire inputs, execute RML, query RDF,
change another checkpoint, or gate promotion/SQL. It runs after releasing the
repair lease and cannot hold a mapping slot. Reporting-code changes are outside
the history execution fingerprint. No new NiFi lane, schedule or validation
gate was introduced. Identity/source conflicts still require aligned evidence
or an accepted correction; an unchanged failed input is not refetched every
minute. Deployment uses the existing `nifi/provision-history-addition.ps1`.
