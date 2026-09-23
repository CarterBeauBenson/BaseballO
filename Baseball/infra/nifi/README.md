# Clean NiFi runtime

BaseballO uses one loopback-only Apache NiFi instance at
`http://127.0.0.1:8080/nifi/`. Runtime state is stored under
`%LOCALAPPDATA%\BaseballO\state\nifi`; no flow or processor state is kept in
the NiFi installation directory. The starter persists
`-Duser.timezone=America/New_York`, and every acquisition trigger uses the
reviewed `0 0 5 * * ?` schedule.

The canvas has one repository-owned root process group named `BaseballO`.
Each detachable source owns its child group, API connector, RML, SHACL,
retries, quarantine, promotion, and provenance path:

| Source module | Process group | Corpus discovery |
| --- | --- | --- |
| `mlb-game` | `MLB Game` | MLB schedule response to final-game requests |
| `mlb-teams` | `MLB Teams` | season request |
| `mlb-leagues` | `MLB Leagues` | season request |
| `mlb-divisions` | `MLB Divisions` | season request |
| `mlb-people` | `MLB People` | player population to per-person requests |
| `mlb-venues` | `MLB Venues` | venue population to per-venue requests |
| `mlb-transactions` | `MLB Transactions` | date-range request |

Six sibling downstream groups do not own or control any source lane:

| Downstream group | Responsibility |
| --- | --- |
| `Authority SQL` | Consume authority-source promoted-graph events, execute declared SPARQL, validate immutable SQLite candidates, and atomically promote the authority pointer |
| `DSQ SQL Materialization` | Run an explicit full backfill of all 56 approved DSQs into independently named graph-partitioned SQL tables; nightly refresh remains owned by the MLB Game post-promotion batch stage |
| `Dashboard SQL` | Check for changed promoted games once per minute, checkpoint each game's calculations, and publish prepared dashboard results independently of the report build |
| `Repository Evidence` | Run the aggregate repository gate daily at 06:30 Eastern and retain immutable stdout, stderr, hashes, and status evidence |
| `Serving Equivalence` | Run an explicit manual authoritative-versus-candidate-SQL family proof without admitting the route |
| `RDF Recovery` | Check durable recovery work every 15 minutes; daily consistent backup and separate-drive export, weekly isolated restore, bounded retries and resource limits |

The provisioners reconcile only their named source group and leave sibling
groups untouched. They do not use or migrate the retired control plane.

## Operating contract

The broad lifecycle is:

```text
API -> source-owned RML -> source-owned SHACL -> graph promotion
    -> approved queries -> persistent SQL serving layer -> UI
```

That lifecycle does not mean every change starts at API acquisition. Metric,
SQL, and UI work begins with existing promoted graphs. An authorized addition
targets its affected facts; a full source rebuild requires explicit scope
authorization. The [operating policy](../../../AGENTS.md#incremental-work-and-minimal-manual-validation)
also limits Codex to scoped edits and the smallest useful developer check.
Ontology/meaning, RML/mapping, and SHACL/conformance remain with their existing
owners; NiFi runs the applicable stages and retains their results. Do not
duplicate them with attended command chains or parallel semantic validators.

Bulk and scheduled requests pass through
`scripts/pipeline/check-source-proof-release.py`. The check is intentionally
narrow: a source is released when a completed bounded proof exists for the
current mapping and SHACL hashes. It does not make ontology decisions or
constrain ordinary NiFi flow design. Proof requests bypass that release check
so a changed source can establish a new proof.

For games, schedule discovery stores only a compact expected-game manifest.
Each final game is mapped, validated, and promoted independently. Corpus runs
defer SQL work until all games in a schedule batch have current promotions;
NiFi then runs one serving-layer materialization for the ready batch. A bounded
proof still materializes immediately.

The MLB Game group uses two Apache Jena workers. Each loads one game's RDF
once and executes its unchanged SHACL profiles with separate shapes, reports
and admission outcomes. Two promotion workers consume the same queue without duplicating
FlowFiles. Each constructs the unchanged query-index SPARQL locally over its
validated game graph; graph-store writes retain the existing write lock.
A source-owned per-game lock keeps stages from modifying the same game's files
or graph pair concurrently. Promotion recovers an interrupted transaction before
starting another one. Graph-pair and per-game equivalence checks are unchanged.

The source queues prioritize current games (0), explicitly selected repairs
(10), then historical backfills (20), with FIFO ordering within a priority.
These are work classes inside the existing source boundary; they do not add
memory-heavy RML or SHACL workers. The workstation's memory limit makes more
simultaneous JVMs inappropriate at present.

Quarantine requests waiting on a named SQL build return their unchanged request
to a penalized NiFi queue. They do not hold a sleeping command process. Older
already-running waiters finish in place; the existing 15-minute batch worker
resumes a stopped replay planner once its old thread exits. That same worker
marks progress interrupted only when its recorded OS process has exited.

`Refresh Admission Evidence` checks up to 100 games every five minutes and
runs at most one game's SHACL refresh per tick. It distinguishes missing,
stale and previously withheld evidence. A refresh requires the exact retained
source bytes and local RDF bytes named by the promotion; missing files are
reported, never regenerated or replaced. See the
[operational delivery record](../OPERATIONS-IMPROVEMENTS.md).

## Provisioning and submission

Start NiFi from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\Baseball\scripts\infra\start-nifi.ps1
```

Each module's `nifi/provision.ps1` accepts the same operating switches:

- no switch: reconcile the stopped group only;
- `-RunProof`: start the lane and submit its bounded proof once;
- `-StartDaily`: start the lane and enable its 05:00 Eastern trigger;
- `-RunBackfill`: start the lane and submit its corpus request once.

Example:

```powershell
powershell -ExecutionPolicy Bypass -File `
  .\Baseball\scripts\infra\submit-nifi-corpus.ps1 -Module all
```

The submit-only command preflights every selected running group and then sends
`RUN_ONCE` to its existing corpus trigger. It does not reconcile the canvas or
poll the resulting work. Use `-Module mlb-game` or an explicit list for a
partial corpus submission. Add `-PreflightOnly` to verify readiness without
submitting anything.

Submission is asynchronous. Do not keep a terminal or Codex turn open to poll
a normal run. Inspect the source-local evidence or quarantine only after NiFi
reports failure or when a status check is requested.

Provision the shared downstream groups independently:

```powershell
powershell -ExecutionPolicy Bypass -File `
  .\Baseball\serving\nifi\provision.ps1 -Start
powershell -ExecutionPolicy Bypass -File `
  .\Baseball\serving\dsq-nifi\provision.ps1 -RunFullBackfill
powershell -ExecutionPolicy Bypass -File `
  .\Baseball\serving\dashboard-nifi\provision.ps1 -Start
powershell -ExecutionPolicy Bypass -File `
  .\Baseball\infra\recovery-nifi\provision.ps1
powershell -ExecutionPolicy Bypass -File `
  .\Baseball\infra\nifi\repository-evidence\provision.ps1 -Start
powershell -ExecutionPolicy Bypass -File `
  .\Baseball\serving\equivalence\provision.ps1 -Family paq -Start
```

`Serving Equivalence -RunOnce` is an explicit submission, not a hand-run proof.
Submit it only when the relevant route needs admission evidence and its
immutable serving build exists; NiFi executes it asynchronously. Do not repeat
an unchanged successful proof for unrelated edits. The proof starts and stops its
own token-protected loopback Explorer child process, so it does not depend on
or expose candidate routes through the normal desktop UI. A proof failure
cannot replace an RDF or SQL pointer and cannot stop a source lane.

This runbook intentionally does not record submission or completion of a
particular run. Source-local terminal evidence is the authority for promoted,
cleaned, or quarantined work; serving pointers and their evidence are the
authority for materialization status.

For a single read-only summary of services, NiFi queues, published SQL products,
current build progress, admission maintenance and recovery, run
`Baseball/scripts/infra/status-stack.ps1 -Operations`. This reads existing
owner records; it does not submit or validate work. Routine healthy runs stay
asynchronous.

Provisioners require owned processors to be stopped and refuse to replace a
connection containing queued FlowFiles. The full corpus trigger is therefore
separate from reconciliation; proving or editing a lane cannot accidentally
start the season.
