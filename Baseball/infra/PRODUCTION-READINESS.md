# Private installation and production readiness

BaseballO runs privately on the existing Windows workstation. The metric
dashboard is not ready for a production declaration: the last read-only check
on September 23, 2026, at 17:19 Eastern returned healthy materialized serving
but **0/19 populated player leaderboards**. Current metric gaps and publication
identity are maintained in [metric readiness](../serving/METRIC-READINESS.md).

The [earlier September 14-23 record](../archive/operational-history/2026-09-23/PRODUCTION-READINESS.md)
preserves the original hardening checks and failed builds. Its stale-readiness,
missing-game and pending source-proof instructions are historical, not a current
request to replay ingestion or rebuild RDF.

## Implemented hardening

- Explorer uses the locally pinned Node 24.21.0 and isolated Python 3.13.15
  runtimes. Versions and hashes are in [versions.psd1](versions.psd1).
- The HTTP server bounds request concurrency, deadlines, input/output and
  cache size; cancellation reaches workers. Loopback, origin and Fetch Metadata
  guards, read-only allowlists and browser security headers are implemented.
- The launcher identifies the application and owning PID through liveness,
  checks a replacement before stopping an old Explorer and reuses a healthy
  compatible process. Working-tree changes do not trigger automatic restarts.
- Database checksum receipts are prepared before SQL publication. HTTP readers
  retain file-identity checks without hashing a large new database on first load.
- [Per-user supervision](LOCAL-OPERATIONS.md) starts at logon and checks local
  services every five minutes. SQL readiness does not restart services.
- The storage migration helper uses the configured NiFi port. The guarded
  external RDF store is already configured; normal startup does not rerun migration.
- Independent Dashboard SQL, Authority SQL, report checkpoints and
  [RDF Recovery](RDF-RECOVERY.md) ownership are implemented. Recovery has a
  configured local separate-drive export and retention policy; full disaster
  recovery acceptance remains separate.

Dated component evidence remains in the
[runtime hardening](../benchmarks/metrics/runtime-hardening-2026-09-14/verification.json),
[Python runtime](../benchmarks/metrics/python-runtime-2026-09-14/verification.json)
and [date repair](../benchmarks/metrics/date-provenance-2026-09-14/verification.json)
records. Those tests establish their captured behavior, not today's metric coverage.

## Health contract

`GET /health/live` checks the Explorer process and returns its PID, application
fingerprint and runtime versions. It does not query a database.

`GET /health/ready` reads the latest loaded regular-season selection through
SQL. It requires a nonempty game selection and the 19 public metric identities;
the backend role metric is excluded from that public count. Missing/stale
serving data, overload or a timeout fails service readiness. This route has no
RDF fallback and launches no rebuild.

The response includes `dashboardReadiness`: populated boards, complete
populations, complete-but-empty boards and exact gaps. HTTP 200 does not imply
complete player scores, a full reference season or all 19 populated cards.
The September 23 check selected 15 games on September 16 and reported service
`ready` alongside dashboard `ready: false`. The older HTTP 503 is resolved for
that inspected release; metric completion remains open.

## Remaining release work

| Area | Remaining requirement |
| --- | --- |
| Metric delivery | Publish the completed source/admission/calculation fixes and verify qualified player rows and expanded details for all 19 metrics. Resolve the exact remaining populations in metric readiness. |
| Deployment boundary | Choose the intended host and audience. The current installation uses loopback services; public authentication, TLS and firewall policy are not configured. |
| Recovery | Establish RPO/RTO and off-machine recovery, preserve source/promotion evidence and required configuration, and verify the actual corpus on an isolated replacement. RDF backup alone does not restore NiFi state or credentials. |
| Operations | Verify sign-out/reboot and volume-loss behavior, before-login requirements if needed, runtime/log retention and external alerting. Keep the existing NiFi source and Repository Evidence owners. |
| Runtime maintenance | Explorer has its pinned runtimes; NiFi processor dependencies retain their separately configured Python. Any migration needs focused validation and a safe execution boundary. |
| Semantic governance | The global freeze remains `frozen-unratified`. Accepted source contracts do not resolve unrelated ontology debt or authorize new vocabulary. |
| Legacy Explorer | Additional SQL route admission still requires that family's equivalence. This is separate from dashboard availability. |

Role-appropriate leaderboard minimums are already accepted and implemented in
[the player contract](../serving/PLAYER-LEADERBOARDS.md). They are not an open
product question. A missing metric input does not authorize reacquisition,
source-proof recovery or a season RDF rebuild.

## Release procedure for the private installation

Use `dev`, fetch before publishing, run the smallest useful check for the changed
component and push. Documentation needs only diff review and `git diff --check`.
NiFi Repository Evidence performs aggregate validation asynchronously.

From `Baseball/`, the explicit web launch command is:

```powershell
.\scripts\infra\launch-explorer.ps1 -NoBrowser -SkipNiFi
```

Install the pinned Explorer runtimes with the existing runtime/Python installers
only when missing or intentionally upgrading them. `-SkipNiFi` preserves a running
source ingester during web deployment. A web change uses its relevant component
check and, where interaction changed, the focused browser smoke check. Do not
turn the historical test lists into a mandatory manual release chain.

Metric/SQL changes are consumed through the existing serving owner. Preserve
the current immutable pointer while its replacement runs. Inspect terminal
failure evidence when NiFi reports failure; do not wait on a healthy corpus job.

## Rollback

Revert the identified application change with a new commit on `dev`; never
reset or force-push published history. Use the retained supported runtime and
matching immutable SQL/code release. SQL rollback uses the existing serving
procedure and retained evidence; do not edit a database or its hash to make
an incompatible build appear current. Application rollback does not authorize
rewriting authoritative RDF.
