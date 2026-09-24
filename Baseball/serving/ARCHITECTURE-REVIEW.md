# Skeptical repository review: September 24, 2026

The RDF -> SPARQL -> prepared SQL -> UI design is coherent. The immediate
problem found in this review was that failure paths did not enforce that
separation. A successful test of normal SQL reads had left those paths intact.
This review covers dashboard HTTP requests, publication selection, recovery
and their code dependencies. It is not an ontology audit or a claim that the
nineteen metrics are fully populated.

## Reproduced defects and revisions

| Finding | Consequence | Revision |
| --- | --- | --- |
| The metrics HTTP handler fell back to SPARQL and a Python reducer when SQL failed, unless the caller supplied a special header. | A routine dashboard failure could trigger the expensive graph work the serving design was meant to avoid. | Both metrics routes require prepared SQL and return a controlled 503 when it is unavailable. Graph-based label lookup and the HTTP reducer invocation were removed. Legacy Explorer routing remains separate. |
| `query_pointer_path` selected the legacy report when the dashboard pointer was absent. | Dashboard availability and computation depended on a different product's database and implementation. | Product selection follows the request even when that product has no publication. Missing dashboard SQL cannot select the report release. |
| The dashboard builder returned `unchanged` solely from source notification identity. | Deleting or corrupting the published SQLite snapshot left every subsequent ordinary tick reporting success without repair. | The unchanged path reuses the reader's cached database verification. Missing or damaged snapshots proceed through the existing builder, reusing committed game work. |

The owning files are [the HTTP server](../web/server.mjs),
[release selection](../scripts/pipeline/serving_release.py), and
[dashboard publication](../scripts/pipeline/materialize-dashboard.py).
The HTTP presentation also now qualifies and ranks each player population once
instead of twice, and uses the existing error serializer so diagnostic codes
survive the handler.

The new regressions failed against the previous implementation. Focused checks
then demonstrated rejection without a graph request, independent product
selection, and readable replacement SQL after publication loss/corruption with
zero repeated game calculations. Existing publication, interruption, reuse,
qualification and presentation checks were retained. No new pipeline gate,
semantic approval, RML execution or RDF rebuild was introduced. These are code
and fixture results; live publication and population status remain in
[metric readiness](METRIC-READINESS.md).

## Remaining engineering risks

- **Operational independence exceeds code independence.** The dashboard builder
  still imports the full report materializer for snapshot, admission and cache
  adapters. A shared import failure can affect both products. A bounded next
  refactor should extract those existing adapters into a shared module while
  preserving their interfaces and behavior; moving functions must not broaden
  ingestion or change admission meaning.
- **Calculation invalidation remains broad.** `calculation_fingerprint()` in
  [metric_suite.py](metric_suite.py) covers the whole calculation module and
  metric catalogs. A change to one calculation can invalidate unrelated game
  products. Per-family dependencies would reduce that work, but need to retain
  the actual shared inputs and reference-population dependencies.
- **Implemented calculations are not a populated product.** Existing readiness
  distinguishes a working SQL service, admitted populations and qualified
  player cards. Continue judging delivery by named players and usable values
  from the published dashboard, using those existing diagnostics rather than
  adding another release gate.
