# Operational improvements authorized September 23, 2026

The user requested implementation ("Do it up") of the ten recommendations
from the live NiFi/serving diagnosis. This records engineering scope, not an
ontology approval or permission to replace authoritative RDF.

The accepted API -> RML -> SHACL -> Fuseki -> queries -> SQL -> UI lifecycle
continues. Existing source schedules and running builds retain their scope.
Source facts, classes, properties, mapping semantics and SHACL constraints do
not change through this work. Any discovered mapping gap remains separately
identified; stale evidence is not relabeled as current.

| Work | Delivery |
| --- | --- |
| Admission evidence | Distinguish missing, stale and previously withheld proofs; refresh only supported evidence from retained inputs and existing RDF |
| Authority SQL | Recover stale locking and retry congestion without dropping promoted-graph events |
| Waiting and recovery | Queue pending dependencies; reconcile abandoned process status; bounded retries |
| Dashboard reads | Prepared SQL names and reference products; remove graph work from normal requests |
| Derived builds | Independent product ownership, versioned reusable calculations, resumable report partitions |
| Workload lanes | Prioritize current requests and isolate repair/historical requests within their owning source |
| SHACL execution | Reuse one loaded game across existing profiles with distinct reports and outcomes |
| Performance evidence | Retain stage durations and cache statistics; tune within workstation memory limits |
| Recovery | NiFi-owned consistent backup, separate-device export and isolated restore |
| Maintenance | Clear group names, readable canvas, shared small provisioning helpers and accurate operational status |

Live diagnosis: authority SQL has a September 4 orphaned lock and a saturated
retry loop; long-lived replay commands sleep while waiting on SQL; old process
records remain "running"; dashboard proof version mismatches mask earlier
admission outcomes. Historical percentile computation and optional player-name
SPARQL remain on the HTTP path. The workstation has approximately 11.3 GiB
usable RAM and had about 1 GiB available during the review.

Changes are deployed incrementally through their NiFi owners. Successful
component checks are not repeated as a manual aggregate release gate.

## Delivery on September 23

| Work | Implemented and deployed outcome | Runtime boundary |
| --- | --- | --- |
| Admission evidence | Source-owned five-minute worker; separate missing/stale/previously-withheld diagnoses; exact-input refresh with independent receipts | Latest inspected 100-game sweep: 92 lacked retained local RDF, eight lacked an exact retained RML manifest; zero refreshed. This does not mean Fuseki graphs are absent |
| Authority SQL | OS lifetime lock replaces orphan-file locking; owned event folders only; retry edges no longer deadlock under backpressure; group renamed `Authority SQL` | Published 75 source graphs / 1,761 SQL result rows at 12:15 Eastern; queue drained |
| Waiting and recovery | Pending replay requests return unchanged to penalized NiFi queues; exited-process progress becomes `interrupted`; durable resume for old stopped-but-active replay worker | Existing old waiters remain undisturbed until their named SQL dependency finishes |
| Dashboard reads | Prepared SQL labels, historical reference ranks, cached immutable-release verification; server no longer issues SPARQL for SQL-result names | Initial dashboard SQL published 2,773 games at 12:55 Eastern; following automatic pass was preparing historical ranks |
| Derived builds | Shared metric cache retains three versions per game; completed report SQL partitions survive failed candidates and resume in fresh candidates | Active immutable report build retains its old code; next NiFi report attempt adopts partitions without repeating unchanged source work |
| Workload lanes | Priority 0 current, 10 selected repair, 20 historical; FIFO within each class across existing RML/SHACL/promotion queues | Deployed; existing worker counts retained within workstation memory limits |
| SHACL execution | One Jena graph load per game; existing profile producers, report artifacts and independent outcomes retained | Published for the next source stage; no source corpus execution was started to test this engineering change |
| Performance evidence | Per-phase dashboard durations, shared-Jena load/profile timings, query/calculation/report cache counters, memory-aware maintenance | Source refresh defers below 1.5 GiB available RAM; isolated restore requires at least 2 GiB |
| Recovery | New `RDF Recovery` group, daily consistent backup/export and weekly isolated restore, one stage per timer tick, at most two failed attempts | Enabled; first run correctly reports `waiting-for-serving` while two SQL builds run. No completed new backup/restore claimed |
| Maintenance | Named independent groups, shared small periodic-worker provisioner, updated runbooks, one-shot `status-stack.ps1 -Operations` | Status reads owner records and queues without starting or validating work |

The read-only dashboard check returned `execution: materialized-sql`, selected
15 games, and **0/19 populated player leaderboards**. SQL publication and
operational recovery are real progress; they do not establish complete metric
admission. Missing/stale proofs and previously withheld source outcomes remain
separate diagnoses. The evidence worker does not reacquire inputs, rerun RML,
rebuild a graph, weaken SHACL or certify an old proof as current. The current
source refresh limitation is retained-file availability, alongside the original
per-family source/conformance issues recorded in those proofs.

The live check also exposed a false health failure: SQL returns the backend-only
twentieth role metric, while the public dashboard has 19 cards. Health reporting
now selects the same public metrics as the dashboard before checking completeness;
missing or duplicate public metrics still fail service readiness. It continues
to report unavailable player populations separately.

## Follow-through: unrelated proof invalidation

The next diagnosis inspected the latest published day (September 16): batting
proofs were admitted in 11/15 games, scoring-run proofs in 15/15, and four proof
families were being replaced by generic missing/stale results. Q5's one-function
pinch-hitter change invalidated all four through a whole-context-file hash.
Runner-resolution, pitch-count and defensive producer dependencies are unchanged
by that edit; runner-boundary dependencies are affected.

The exact unchanged implementation pairs now support reuse with the original
fingerprint and outcome. This is restricted to the recorded code transition,
the original promotion and retained artifacts. No source/SHACL proof is
reissued, no historical outcome is relabeled, and no RDF is changed. The real
822680 check recovered admitted runner-resolution evidence, preserved
`PITCH_COUNT_MAPPING_COVERAGE` and `INCOMPLETE_DEFENSIVE_POPULATION` as withheld,
and continued withholding the affected runner-boundary proof. The dashboard
change detector now includes admission-reader code and the equivalence record,
so its next owned build observes the correction without a new source event.

Historical-rank preparation also defers loading projected game rows until the
existing batting-qualification function actually consumes them. That function
already rejects withheld source admissions first. This avoids repeatedly
decoding a rejected season at every date cutoff, with identical population
decisions and exact ranks. Source admission checks are not duplicated in a new
precheck. Focused regressions cover the known code equivalence, corrupt/mismatched
artifacts, preserved withheld outcomes, incremental dashboard behavior and
historical-rank equality. The existing immutable builds finish with their
captured versions; the next NiFi tick adopts these changes.

NiFi's next 100-game diagnostic batch showed an older cause too: 79 previously
admitted batting proofs and 96 previously admitted scoring-run and runner
resolution proofs predated T1. Their exact producer revisions are now covered
by positive-only reuse. T1 keeps the same source issue predicates and splits
clock diagnostics from blocking structural issues; a prior admitted proof
already had no issues of either kind. The existing graph shapes and validator
are unchanged for these three families. Reuse requires the original admitted
proof and its hash-bound, reconciled, zero-issue census. Previous withholding
is not eligible. Inspected game 822682 now loads all three original admissions
with separate reuse provenance. Neither source acquisition nor RDF execution
was needed to recover them.

The next delivery pass extends positive-only reuse to pre-T1 pitch-count and
runner-boundary proofs, and pre-Q5 runner-boundary proofs. Earlier successful
checks excluded the newly handled cases: reversed clocks caused source
reconciliation failures, and an initial PH without an outgoing ID could not
supply a successful batting-participation check. T1's clock selection leaves
undisputed pairs unchanged; Q5 preserves previously successful substitutions.
The boundary and count SHACL contracts are unchanged. Complete producer
fingerprints restrict reuse to these exact revisions, with the original
admitted, zero-issue census and all retained artifact hashes still required.
Previously withheld proofs remain withheld.

Six focused evidence-reader tests pass. The historical and current producers
give identical censuses and shapes for the retained 79-PA reference game;
the new PH case is rejected by the old producer and remains outside positive
reuse. Read-only checks recover both original admissions for promoted game
566279 and boundary admissions for September 16 games 823979, 824140 and
824626. NiFi's existing change detector owns their derived SQL update.

Dashboard build `20260923T165557Z-dashboard-f5ce432061b9` published at 13:55
Eastern with 2,773 games, including the prepared-label/reference implementation.
Its live default selection still returned 0/19 populated boards. The exact
remaining latest-day PA blockers are now recorded in
[`METRIC-READINESS.md`](../serving/METRIC-READINESS.md#next-work-from-the-september-23-live-check).
No later publication incorporating the proof-reuse fixes is claimed here.

The subsequent B1 repair consumes the retained, source-owned participation
inventory and B1 census for the exact promoted input. Four latest-day games
were rejected by the older substitution-position heuristic although all
turns have one recorded actual batter and all independent player totals
reconcile. Maintenance now runs the unchanged B1 shape for these candidates
against a bounded read-only export of their existing graph. It retains the
original withholding and emits a new proof with a separate adapter fingerprint,
source dependencies, export hash and Jena report. No source response is
reacquired and no authoritative triple is written. Ambiguous/multiple batters,
other source discrepancies and graph disagreements remain withheld.

Admission maintenance checks once per minute, with one JVM validation per tick,
the existing memory guard and single worker. It prioritizes the latest published
dashboard day before historical games. This does not change daily acquisition
or the 15-minute batch schedule. Dashboard checkpoints now distinguish changes
to compatibility provenance from actual proof, RDF and calculation inputs;
metadata-only updates preserve prepared scores and historical reference ranks.
Focused checks passed: nine evidence-reader/retained-input checks and seven
dashboard publication/checkpoint checks. Live new admissions are still pending.

Focused checks covered authority recovery, queued readiness, exited-worker
reconciliation, exact cache reuse and corruption fallback, SQL-only names,
historical-rank equivalence, independent SHACL reports with a shared graph,
and backup/export/restore boundaries. The report checkpoint regression builds
two fresh candidates, requires reuse without game calculation, compares all
result tables, and still runs the builder's existing final checks. No aggregate
repository validation was manually chained; the existing hooks and NiFi gate
retain their own jobs.

## Recovery storage and operating limits

Fuseki creates a consistent compressed dataset backup in
`D:\BaseballO\RDF\fuseki\backups`. The worker verifies it and exports to
`%LOCALAPPDATA%\BaseballO\state\recovery\exports` on C:. Its weekly restore
uses a fresh UUID directory under `D:\BaseballO\RDF\recovery-proofs\restores`;
it never opens the live database as a restore destination or swaps a pointer.

The export requires archive size plus 20 GiB free. Restore requires three times
the uncompressed archive size plus 20 GiB free. Two completed owned exports
and two isolated restore directories are retained. Original Fuseki archives
are not pruned by this worker. Existing SQL work has priority; recovery records
the reason for deferral and returns, with no command sleeping on dependencies.
An active restore records its child PID so a later tick cannot start a second
loader after an interrupted controller. Recovery covers the RDF dataset;
repository, NiFi configuration and SQL products are not included in this archive.

Inspect the owning records once when needed:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File `
  .\Baseball\scripts\infra\status-stack.ps1 -Operations
```

The 05:00 Eastern acquisition schedule and existing 15-minute batch checker
remain enabled. No new source acquisition, RML semantics, ontology terms or
authoritative RDF rebuild is part of this change set.
