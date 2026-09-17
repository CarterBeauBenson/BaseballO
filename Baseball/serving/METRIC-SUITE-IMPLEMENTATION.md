# Metric dashboard implementation

Current release status and remaining work are maintained in
[METRIC-READINESS.md](METRIC-READINESS.md). This document describes the active
implementation. Earlier dated results remain in the immutable
[metric benchmarks](../benchmarks/metrics/) and Git history.

## Data and ownership

The accepted lifecycle is API -> RML -> SHACL -> Fuseki -> queries -> SQL -> UI.
NiFi owns acquisition, source validation, promotion, serving builds and retry.
The graph remains authoritative; SQL, query caches and calculated-product
caches are disposable derived data.

| Component | Responsibility |
| --- | --- |
| `sources/mlb-game/` | Source-owned RML, SHACL and promotion-bound admission proofs |
| `sparql/metrics/` | Evidence queries, calculation kernels, catalog and accepted metric policies |
| `serving/metric_suite.py` | Exact calculations, evidence consumers, per-game products and selected-period player summaries |
| `serving/metric-suite-schema.sql` | Evidence, current proofs, exact results and their hashes |
| `scripts/pipeline/materialize-serving-layer.py` | Validated graph snapshot, immutable SQL candidate, integrity checks and atomic publication |
| `scripts/pipeline/serving_release.py` | Committed code capture and matching SQL reader release |
| `scripts/pipeline/serving_query_cache.py` | Exact SELECT reuse for unchanged promoted graph pairs |
| `scripts/pipeline/serving_metric_cache.py` | Per-game calculation reuse for identical evidence, current validated proofs and calculation code |
| `web/query-builder/metric-suite-query-builder.js` | Request validation, accepted qualification, exact ranking and dashboard coverage report |
| `web/server.mjs` and `web/metrics.js` | Read-only API, optional names, automatic top-five cards and expanded details |

## Build and read contracts

Every build checks current source proofs, even on cache hits. The metric cache
skips pure calculation only. It never copies admission authority from an older
build. Evidence and proofs are written into the new candidate, all twenty
metric products round-trip through exact SQL, and final graph/promotion and
integrity checks still precede publication.

NiFi also prepares the database's checksum-verification receipt before publishing
the pointer. Readers retain their file-identity checks, but a newly published
database no longer requires a full file hash during its first HTTP request.
Each database has its own receipt so concurrent old and new readers do not
invalidate each other's verification cache.

Calculation reuse has a separate fingerprint from source admission. A producer
edit with identical validated outputs need not invalidate a calculation. A
changed proof, evidence binding, game identity or calculation input invalidates
that game's cached product. The broader serving manifest and immutable code
release still bind the reader to the entire admitted implementation. See
[BUILD-REUSE.md](BUILD-REUSE.md) for failure and retention behavior.

A selected-period query applies complete schedule, source, eligibility and
player participation requirements. Season-percentile metrics additionally
require the independently complete reference season. Per-game caches cannot
establish either population. Fractions stay exact until display; entropy
retains its exact channel counts and explicitly approximate numeric evaluation.

## Public presentation

There are 19 public metrics and one backend role metric. Cards rank players
using selected-period averages, except Empty Games, which shows a game count.
The approved PA and other participation minimums are applied server-side.
Traditional and ball/strike review mechanisms retain separate populations.

`dashboardReadiness` accompanies shared dashboard responses and the service
health check. It counts qualified player boards, complete populations and
complete-but-empty populations separately. A passing service health check or
an available scoped aggregate cannot establish that the dashboard is populated.

The legacy Explorer's PAQ-1 and Empty Games calculations remain separately
versioned. Their historical formulas and route-admission status do not define
the new dashboard metrics.

## Focused engineering checks

From `Baseball/tests`, run the affected Python component modules with
`python -B -m unittest <module>`. Calculation reuse is covered by
`test_serving_metric_cache`, `test_metric_suite_serving` and
`test_serving_materializer`: cold/warm equality, exact large fractions,
independent proof invalidation, corruption recovery, repeat admission checks,
current graph checks and preservation of the prior pointer on failure.

From `Baseball/web`, the supported Node 24 runtime runs
`node --test tests/metric-suite.test.mjs tests/runtime-safety.test.mjs` for
qualification, dashboard coverage, API delivery and service health behavior.
NiFi's Repository Evidence observer owns the aggregate repository gate.
These developer checks do not certify a populated production release.
