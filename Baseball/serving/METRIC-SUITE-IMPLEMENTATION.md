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

Metric implementation starts at the existing graph, not at API acquisition.
Change the affected queries, calculations, SQL products, or presentation and
let NiFi run their applicable stages. If an input is unsupported, document
that specific gap and continue supported work; do not initiate a source
refresh to make every metric complete. Authorized RDF additions stay targeted.
The [minimal-check policy](../../AGENTS.md#incremental-work-and-minimal-manual-validation)
limits manual checks to the edited behavior and leaves repeatable validation
to NiFi. The source-owned [Q7 history addition worker](../sources/mlb-game/pipeline/TARGETED-HISTORY-ADDITION.md)
implements the approved targeted addition. The general game recovery path still
performs whole-game replacement and is not a default prerequisite for metric work.

## Required serving design

Existing RDF -> SPARQL answers and metric calculations during the NiFi build
-> prepared SQL results -> interface reads.

Keep the authoritative RDF as the stable research record. SPARQL answers the
analytical questions over that record; NiFi performs graph work and accepted
metric calculations before publishing the SQL product. SQL must retain usable
results, not merely move raw graph bindings to a different store and repeat
the expensive processing when a user opens the page. Selected-range requests
may filter and aggregate prepared SQL rows and format the response. They must
not run live SPARQL, reconstruct game histories, repeat pipeline validation,
or calculate an entire reference-season population. This separation is the
reason for SQL serving: users should not wait on graph-query timeouts.

The dashboard builder now prepares game products, player names and exact
reference ranks for each historical date cutoff. The dashboard reader selects
the matching retained population; it never calculates missing ranks on a
request. The reader still pools projected observations and checks participation
and population completeness, so selected-range queries are not constant-time.
Each publication captures its implementation; in-flight builds finish with
that version. See [metric readiness](METRIC-READINESS.md) for the last observed
published build and changes still awaiting SQL publication.

An unhandled case in an existing MLB field belongs to that source lane's
mapping-coverage debt. It does not establish a new source, and successful
ingestion does not establish complete API mapping. Record the exact missing
facts separately; any authorized correction must stay targeted.

## Current component ownership

| Component | Responsibility |
| --- | --- |
| `sources/mlb-game/` | Source-owned RML, SHACL and promotion-bound admission proofs |
| `sparql/metrics/` | Evidence queries, calculation kernels, catalog and accepted metric policies |
| `serving/metric_suite.py` | Exact calculations, evidence consumers, per-game products and selected-period player summaries |
| `serving/metric_blocks.py` | Indexed analytical inputs, pooled game summaries, reference-rank retention and input diagnostics |
| `serving/metric-suite-schema.sql` | Evidence, current proofs, analytical observations, exact results and their hashes |
| `scripts/pipeline/materialize-dashboard.py` | Dashboard game products, labels, historical reference ranks and independent immutable SQL publication |
| `scripts/pipeline/materialize-serving-layer.py` | Full report/legacy Explorer SQL, resumable partitions, integrity checks and independent atomic publication |
| `scripts/pipeline/serving_release.py` | Committed code capture and matching SQL reader release |
| `scripts/pipeline/serving_query_cache.py` | Exact SELECT reuse for unchanged promoted graph pairs |
| `scripts/pipeline/serving_metric_cache.py` | Per-game calculation reuse for identical evidence, current validated proofs and calculation code |
| `scripts/pipeline/serving_report_cache.py` | Completed report-game SQL partitions and ordered source rows for restart reuse |
| `serving/reference_products.py` | Dashboard reference ranks prepared by NiFi for historical cutoffs |
| `serving/dashboard_display.py` | Player labels prepared from accepted graph queries into dashboard SQL |
| `web/query-builder/metric-suite-query-builder.js` | Request validation, accepted qualification, exact ranking and dashboard coverage report |
| `web/server.mjs` and `web/metrics.js` | Read-only API, prepared names, automatic top-five cards and expanded details |

## Build and read contracts

Every build checks current source proofs, even on cache hits. The metric cache
skips pure calculation only. Report partitions additionally reuse completed SQL
writes after matching current admission outcomes, promoted RDF/index hashes,
dimensions and construction code. They do not grant admission from an older
build. A cold game round-trips all twenty metric products through exact SQL;
reused report writes retain that result. Existing candidate-wide row/hash,
graph/promotion and integrity checks still precede publication.

NiFi also prepares the database's checksum-verification receipt before publishing
the pointer. Readers retain their file-identity checks, but a newly published
database no longer requires a full file hash during its first HTTP request.
Each database has its own receipt so concurrent old and new readers do not
invalidate each other's verification cache.
The builder and reader share the cached file and publication-metadata checks;
the builder also verifies the paired runtime release before reporting an
unchanged publication. A missing or corrupt database, malformed pointer,
mismatched build identity or unusable release pairing therefore returns to the
normal SQL build, which reuses committed game products. Recovery records the
previous publication issue. Complete candidate evidence is saved before the
atomic pointer change, which is the publication commit point. Subsequent
progress, evidence-status or retention I/O failures are reported to NiFi as
`postPublicationWarnings`; they cannot undo a readable publication. If the
final evidence-status write fails, the saved candidate evidence and active
pointer retain the build's identity and publication state. None of this
authorizes source acquisition or RML execution.

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

Calendar transport corrections are owned by the MLB-game batch worker's
`pipeline/schedule-qualification.py`. It retains hash-addressed snapshots for
affected incomplete ranges. The builder merges those snapshots with original
batch provenance; SQL stores the selected snapshot's hash. This calendar-only
repair does not change source game admission fingerprints or restart mapping.

## SQL building blocks and final arithmetic

This section describes current code, including the remaining request-time
work identified above; it is not the definition of the required end state.

Version 2.1 projects the existing accepted evidence once during the NiFi build.
The request reader selects these reusable observations instead of loading raw
graph bindings and reconstructing movement, scoring and pitch histories:

| SQL product | Grain and purpose |
| --- | --- |
| `metric_suite_scope_fact` | Distinct PA, roster, run and contact-play facts needed for participation and census checks |
| `metric_suite_input_row` | One observation per graph and input family: contribution PA, recovery PA, defensive resolution, PAQ-2.1 PA or progress PA |
| `metric_suite_input_state` | Each game's projection completeness, unresolved observations and expected row count |
| `metric_suite_shell` | Compact per-game results and supported scoring/review details, excluding the five large input families |
| `metric_suite_reference_rank` | Exact ranks for a metric, season and identical admitted reference graph set |
| `dashboard_reference` | Compressed exact ranks for each supported historical reference population |
| `dashboard_display_label` | Prepared unambiguous player labels for SQL-only display |

Observation identity, player, game, applicability and exact numerator/denominator
are SQL columns. Detail JSON preserves the existing reducer inputs and evidence
traces. This is a physical projection of accepted inputs; it adds no RDF terms.
The original evidence and full game products remain available for inspection.

The server pools exact counts and fractions across the selected games, then
calculates player averages and applies the existing participation minimums.
It sums Empty Games as a count and combines review numerators/denominators
before division. It never averages game percentages. Individual Offensive Reach
and Help Without Advancing requests now load the same contribution dependencies
as their dashboard cards.

NiFi prepares dashboard ranks after all game inputs are stored, using the
unchanged qualification and percentile functions for each regular-season date
cutoff. A different historical cutoff selects its own retained population;
it cannot reuse the latest population's ranks. Missing prepared ranks require
NiFi preparation rather than request-time calculation. Reference requests still
read projected records for membership and completeness checks. The legacy full
report reader remains separately versioned; this prepared-reference adapter is
owned by the dashboard product.

The internal `_use_blocks=False` reader remains a developer comparison oracle,
with no HTTP switch. `buildingBlockCoverage` reports per-family projection and
gap counts for diagnosis. Complete projection is distinct from admitted source,
complete calendar coverage, qualified participation and a populated leaderboard.

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

`test_metric_blocks` compares every metric response against the evidence reader
over distinct one- and two-game fixtures. It denies SQL access to raw evidence
and full game results and fails if request-time graph kernels run. It also
checks missing/corrupt inputs, cached-rank corruption, historical cutoffs,
changed reference inputs, independent schedules and both PAQ-2.1 ranking passes.
`prove_metric_building_blocks.py` provides a bounded read-only comparison on one
already promoted game; it neither acquires source data nor publishes a build.

From `Baseball/web`, the supported Node 24 runtime runs
`node --test tests/metric-suite.test.mjs tests/runtime-safety.test.mjs` for
qualification, dashboard coverage, API delivery and service health behavior.
NiFi's Repository Evidence observer owns the aggregate repository gate.
These developer checks do not certify a populated production release.
