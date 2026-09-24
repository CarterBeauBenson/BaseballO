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

## Second hostile sweep: presentation and publication recovery

This pass found further failures in user-visible status, name resolution and
derived-publication recovery. The fixes preserve the existing qualification
rules and metric calculations.

| Finding | Revision |
| --- | --- |
| Complete player populations with nobody meeting the minimum were described as missing evidence. | Status now distinguishes no qualifiers from incomplete player results. |
| The "With results" filter used the aggregate score's status and could hide a qualified player leaderboard. Details could also headline "Unavailable" above valid player rows. | Cards, filters and detail headlines use qualified player availability while retaining independently supported event details. |
| A review leaderboard with one populated mechanism and another unresolved mechanism was announced without its incomplete coverage. | Status and coverage filtering retain the unresolved mechanism alongside the available players. |
| Prepared names were applied only to top-level player rows, skipping `byMechanism` review populations. | Names now reach each separate population, preserving graph scope, conflicting-name handling and original score inputs. |
| Every player rescanned every selected-game label, repeated across metrics. A 100-player/100-label fixture made 10,000 label-identity reads. | One graph-scoped label index is built per response and reused across players, metrics and review populations. |
| A truncated/non-object publication pointer stopped recovery; a pointer with an incorrect build ID could still return `unchanged` when its database checksum matched. | Builder and reader share the same publication-opening checks. Damaged metadata is recorded as `previousPublicationIssue`, and committed SQL game work is reused to publish a replacement. The old pointer is replaced only after success. |

Checks for this revision: 50 metric-interface tests and 11 dashboard
materializer/recovery tests passed. No live-data rebuild or production
population claim is part of these results.

## Final sweep: publication boundaries and detail scope

The final pass stayed within these changed paths and their immediate release
dependencies. It reproduced and corrected three remaining failure modes:

- An intact SQL snapshot with a missing or malformed paired runtime release
  still returned `unchanged`. The builder now reuses the launcher's release
  verification as well as the reader's database checks. An unusable pairing
  returns to normal SQL publication with committed game calculations retained.
- The pointer changed before build evidence was saved, and later progress,
  evidence-status or retention I/O errors reported the already published build
  as failed. Complete candidate evidence is now saved before the atomic pointer
  change. Failures before that commit point preserve the previous publication;
  bookkeeping errors afterward remain explicit `postPublicationWarnings` in
  the NiFi result. If the final evidence-status update cannot be saved, the
  candidate evidence remains intact and the active pointer establishes whether
  that candidate was published.
- Detail scope text could describe partial review results as Walk/HBP advances
  and complete run results as incomplete. It now follows the player board or
  the actual supported event population.

The new regressions failed before the corrections. The final focused run passed
51 metric-interface tests and 24 dashboard-materializer/release tests. This
pass made no ontology or mapping changes and did not run live data processing.

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
