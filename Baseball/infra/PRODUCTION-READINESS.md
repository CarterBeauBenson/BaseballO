# Production readiness — 2026-09-14

The Explorer is hardened and running privately on the existing Windows machine.
This is not a production launch. Deployment location and access policy remain
undecided, and the materialized-serving readiness check failed during this release.

## Implemented and verified

- The launcher uses checksum-pinned Node.js 24.21.0 LTS in the local runtime
  directory and checks its version when reusing a running Explorer. The global
  Node installation is unchanged. Release metadata and SHA-256 come from the
  [official Node distribution](https://nodejs.org/dist/v24.21.0/SHASUMS256.txt).
  Node 20 is end-of-life according to the
  [Node release schedule](https://nodejs.org/en/about/previous-releases).
- At most four API/readiness requests execute concurrently; overload receives
  HTTP 503 and `Retry-After: 2`. Static pages and liveness remain accessible.
  Admission uses the same normalized URL path as routing.
- Requests have a 45-second deadline. Python workers have a 30-second deadline,
  16 MiB stdout limit and 64 KiB stderr limit. Cancellation kills the worker and
  waits for its close before releasing the request slot. Client disconnects
  propagate cancellation to workers and upstream HTTP requests.
- JSON input is capped at 64 KiB, including chunked bodies. Graph responses and
  serialized API results are capped at 32 MiB. The query-result cache has a
  32 MiB serialized-content budget, 100-entry limit and 30-second TTL. These are
  payload bounds, not a process RSS or Python memory limit.
- HTTP header/body receipt and keep-alive have explicit timeouts. Headers are
  capped at 16 KiB. Local hostname, same-origin and Fetch Metadata checks reject
  foreign browser requests. Existing CSP, frame denial and read-only route
  allowlists remain; camera, microphone and geolocation permissions are denied.
- SIGINT/SIGTERM handlers drain requests, then abort remaining work after ten
  seconds. Windows process termination can still be abrupt; these handlers are
  not a Windows service supervisor.
- The RDF migration helper now probes the configured NiFi port. The migration
  was not run; the existing external RDF storage contract remains in place.

The [verification record](../benchmarks/metrics/runtime-hardening-2026-09-14/verification.json)
records 71 passing focused web tests, four parsed PowerShell scripts and a
passing live browser smoke check. Failure tests exercise hung workers, oversized
output/input, disconnects, deadlines, origin checks, overload and readiness.
The browser verified all 20 guides, six perspectives, shared dashboard queries,
exact detail values, stale-response handling and mobile layout. All 20 metric
results and the calculation fingerprint exactly match the prior August 25
capture. The separate nine-run fixture is still distinct from live promotion.

## Health contract

`GET /health/live` reports whether the Explorer process responds and includes
its Node version. It performs no database query.

`GET /health/ready` queries the latest loaded regular-season day through the
validated SQL adapter. It requires a nonempty graph selection and exactly the
catalog's metric identities. It never falls back to RDF. A stale, missing or
incomplete build returns 503; overload and deadlines also fail readiness.

A ready response means materialized serving is usable for that selection. It
does not establish full metric coverage, season completeness, data freshness
against today's schedule, route-wide SQL admission, or semantic ratification.
`metricsWithScopedResults` counts available results for that selection only.
Health endpoints are read-only and do not launch a rebuild.

The measured liveness response was 200 on Node v24.21.0. Readiness returned 503;
the read-only adapter reported `Serving build is stale for mlb-game.rml.ttl`.
The first asynchronous rebuild exhausted its retries. The retained NiFi failure
at 19:35:22 Eastern reported that `sparql/metric-display-labels.rq` was missing
from the approved canned DSQ SQL surface. This optional display lookup had been
placed beside materialized questions, causing the existing exact catalog check
to reject it. The unchanged query now lives under `sparql/options/`, alongside
other display lookups. No DSQ, reducer, query definition or validation rule was
removed or relaxed. A focused regression loads the actual checked-in catalog
and verifies all 56 DSQs while excluding the display helper.

The corrected build was resubmitted through the existing
`serving/dsq-nifi/provision.ps1 -RunFullBackfill` workflow. Submission is not
completion or promotion. Terminal NiFi evidence and a later readiness check
must establish recovery; the corrected run was left asynchronous.

The follow-up also makes launcher identity independent of graph/SQL queries:
`/health/live` returns the process ID and application fingerprint. The launcher
checks the replacement runtime before stopping an older process and verifies
that its reported PID owns port 4173. A dependency outage no longer prevents
identifying the running Explorer. The legacy status endpoint is used only when
upgrading an older Explorer without the full liveness response. Restart and
subsequent reuse of the current Explorer were both verified on the workstation.
The follow-up passed 38 focused web tests, the exact DSQ catalog regression and
the source-scope checks. It does not install unattended startup or claim SQL
readiness.

## Remaining release blockers

| Area | Required before declaring production |
| --- | --- |
| Deployment boundary | Choose the host and intended audience. Current Explorer, NiFi and Fuseki are loopback services. Public hosting, authentication, TLS and firewall policy are not configured. Host/origin guards deliberately do not trust forwarding headers. |
| Serving | Obtain a validated current immutable SQL build and passing readiness. Keep source and SQL equivalence/admission gates intact. The current browser smoke used authoritative RDF for 15 games on August 25. |
| Metric coverage | Complete the accepted source backfill and inspect coverage across the intended release population. Twenty implemented cards and worked examples do not mean twenty population-level scores are available. |
| Recovery | Define recovery-time and recovery-point objectives, an off-machine destination, retention and ownership. Exercise an isolated restore of authoritative RDF, source/promotion evidence and required machine configuration. The existing Fuseki backup helper alone is not a tested disaster-recovery system. Put recurring work in NiFi. |
| Operations | Configure and verify unattended startup, failure restart, disk/log retention and alerting on the selected host. Use the existing NiFi source and Repository Evidence owners. A desktop launcher is not an unattended service. |
| Runtime maintenance | The observed Python runtime is 3.10.8. Select and validate a maintained patched runtime for all owning NiFi and web components. Node is pinned for Explorer, but other tools using global Node have not been migrated. |
| Semantic governance | The existing semantic freeze remains `frozen-unratified`. This engineering release does not ratify it, resolve ontology debt or authorize new terms/mappings. |

## Release procedure for the current private installation

Use the root `dev` branch; fetch before publishing. Run focused checks for the
changed component, commit and push to `origin/dev`. NiFi Repository Evidence
owns the aggregate repository gate asynchronously; a push is not a passing gate.

From the `Baseball/` directory, install and start the pinned Explorer runtime:

```powershell
.\scripts\infra\install-explorer-runtime.ps1
.\scripts\infra\launch-explorer.ps1 -NoBrowser -SkipNiFi
```

The installer verifies the downloaded archive before extraction. It fails on
a checksum mismatch or incomplete installation. The launcher restarts only a
recognized stale Node Explorer and verifies the application fingerprint and
runtime version. `-SkipNiFi` avoids changing a running ingester during a web
release. The launcher uses the existing Fuseki startup helper.

Run the three focused web suites with the installed executable:

```powershell
. .\scripts\infra\common.ps1
$explorerNode = Join-Path $script:RuntimesRoot ($script:Versions.Node.InstallDirectory + '\node.exe')
& $explorerNode --test web/tests/runtime-safety.test.mjs web/tests/metric-suite.test.mjs web/tests/analytics-query-builder.test.mjs
```

For a changed web release, inspect `/health/live` and `/health/ready` and run
`web/tests/metrics-browser-smoke.ps1` against the local Explorer. A readiness
failure blocks a production declaration even if RDF fallback still works.
Do not use a successful liveness response as evidence of data readiness.

## Rollback

Retain the current verified Node LTS installation. Revert the identified
application commit with a new commit on `dev`, perform the relevant focused
checks and push the revert. Do not reset or force-push published history.
Launch the reverted application with the retained supported runtime after
checking compatibility; a revert that restores the old launcher must not
silently select the obsolete global Node runtime.

This change does not rewrite RDF or SQL databases. SQL rollback is separate:
use retained validated immutable builds and their matching evidence through
the existing serving procedure. Never edit a database or its hash to make a
stale build pass admission. If compatible serving is unavailable, report that
failure and preserve the authoritative data.
