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

Four sibling downstream groups do not own or control any source lane:

| Downstream group | Responsibility |
| --- | --- |
| `Analytical Serving` | Consume immutable promoted-graph events, execute declared authority SPARQL, validate immutable SQLite candidates, and atomically promote the authority pointer |
| `DSQ SQL Materialization` | Run an explicit full backfill of all 56 approved DSQs into independently named graph-partitioned SQL tables; nightly refresh remains owned by the MLB Game post-promotion batch stage |
| `Repository Evidence` | Run the aggregate repository gate daily at 06:30 Eastern and retain immutable stdout, stderr, hashes, and status evidence |
| `Serving Equivalence` | Run an explicit manual authoritative-versus-candidate-SQL family proof without admitting the route |

The provisioners reconcile only their named source group and leave sibling
groups untouched. They do not use or migrate the retired control plane.

## Operating contract

The broad lifecycle is:

```text
API -> source-owned RML -> source-owned SHACL -> graph promotion
    -> approved queries -> persistent SQL serving layer -> UI
```

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

The MLB Game group uses two Apache Jena workers for its unchanged source SHACL
profile. Its single promotion worker constructs the unchanged query-index
SPARQL locally over each validated game graph, then serializes only the final
graph-store write. This prevents index construction from competing with the
shared dataset while retaining the graph-pair and per-game equivalence gates.

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
  .\Baseball\infra\nifi\repository-evidence\provision.ps1 -Start
powershell -ExecutionPolicy Bypass -File `
  .\Baseball\serving\equivalence\provision.ps1 -Family paq -Start
```

`Serving Equivalence -RunOnce` is deliberately manual. Submit it only after
the relevant immutable serving build exists. The proof starts and stops its
own token-protected loopback Explorer child process, so it does not depend on
or expose candidate routes through the normal desktop UI. A proof failure
cannot replace an RDF or SQL pointer and cannot stop a source lane.

The current 2026 season-to-date request for all seven lanes was submitted on
2026-09-01. This runbook does not infer completion from submission; its
terminal evidence remains the authority for promoted, cleaned, or quarantined
work.

Provisioners require owned processors to be stopped and refuse to replace a
connection containing queued FlowFiles. The full corpus trigger is therefore
separate from reconciliation; proving or editing a lane cannot accidentally
start the season.
