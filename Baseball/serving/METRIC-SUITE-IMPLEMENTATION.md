# Graph-native metric suite implementation

The user requested the complete software suite with unresolved semantics
collected for one review. The implementation must return unavailable values
with reasons when graph evidence cannot support a score. Existing PAQ-1 and
Empty Game behavior remain separately versioned.

Work checklist:

- [x] Versioned catalog of 20 metrics and one register of 21 shared requirements.
- [x] Canonical SPARQL calculation kernels for every specified metric.
- [x] Exact rational calculation, cohort and aggregate support.
- [x] Existing-term RDF evidence extraction with explicit admission limits.
- [x] Rebuildable SQL products, provenance and equivalence checks.
- [x] Existing serving pipeline and read-only API integration.
- [x] Explorer metric suite, definitions, evidence and unavailable reasons.
- [x] Focused calculation, data-boundary, SQL, API and UI-code verification.
- [x] Consolidated handoff with remaining gaps; no individual approval stops.

No new ontology assertions, Mermaid changes, Git operations or source-lane
topology changes are included in this implementation scope.

## Delivered

The [calculation contract](METRIC-SUITE.md) documents the formulas, exact
representation, reducers, graph admission and serving interfaces. The
[single batch review](../proposals/graph-native-metric-suite-batch-review/README.md)
collects the remaining questions. No individual gap needs a separate software
implementation turn just to expose its metric or unavailable reason.

The local Explorer was refreshed at `http://127.0.0.1:4173/metrics`; its
catalog, stylesheet, script and read-only API routes are available. Only the
Explorer Node process was restarted. NiFi and the acquisition schedule were
left running; the existing NiFi materialize stage will build the new SQL
products. No manual corpus rebuild or source-proof polling was performed.

All 20 arithmetic implementations and generic SQL value persistence are
tested. **This does not mean all 20 metrics have valid live scores.** AV has
an existing-evidence adapter scoped to explicitly resolved mapped reviews.
The other 19 return unavailable with named prerequisites until the batch
review resolves the missing graph semantics and source coverage.

## Focused validation on 2026-09-08

100 tests passed across the changed components and directly affected existing
serving/Explorer behavior:

| Check | Tests |
| --- | ---: |
| `tests/test_graph_native_metric_suite.py` | 16 |
| `tests/test_metric_suite_serving.py` | 8 |
| `web/tests/metric-suite.test.mjs` | 7 |
| `tests/test_sparql_source_scopes.py` | 2 |
| `tests/test_serving_materializer.py` | 21 |
| `tests/test_serving_layer.py` | 12 |
| `web/tests/analytics-query-builder.test.mjs` | 34 |

The generator drift check also passed. Changed Python entry points parse.
The Node tests used `--preserve-symlinks --preserve-symlinks-main` because
Windows sandbox path resolution otherwise returned EPERM; the tests themselves
were unchanged for that environment constraint.

The tests include all 20 SPARQL kernels, fifteen accepted TFS scenarios, exact
ties and large fractions, cohort and unknown handling, defensive cycles,
entropy components, every metric's SQL round trip, direct RDF-to-SQL review
rate equivalence, partition replacement, stale/corrupt SQL, API input rejection,
fallback behavior and existing PAQ-1 routes.

The [immutable live smoke capture](../benchmarks/metric-suite-2026-09-08.json)
records a read-only check over the latest loaded day, 2026-08-25: 15 promoted
games and 12,368 evidence rows. TFS returned its expected five shared blockers.
AV returned exact **13/23**, from 13 overturning dispositions among 23 resolved
mapped reviews. That population is explicit; it is not a claim of complete
league-wide review coverage. The live route used authoritative RDF fallback
because a new NiFi-owned SQL build has not yet been demonstrated.

Browser visual inspection could not run because neither a connected browser
nor the in-app browser was available. HTTP delivery, accessibility markup,
safe text rendering, precision display, interaction state and route behavior
were checked in code. Visual appearance remains unverified.

These are focused developer checks, not a replacement for NiFi's asynchronous
Repository Evidence gate or the pending one-game semantic proof.

## Follow-up: accepted batch answers

Suite calculation version 2.0.1 incorporates the named September 8 answers.
The accepted policy is recorded before its engineering consequences in
`archive/design-records/metric-suite-batch-answers-2026-09-08/`.
Empty Game Rate now requires at least one PA; CPD uses play/channel identities;
role breadth filters to the four accepted kinds; and PAQ-2.1 population selection
distinguishes known inapplicability from missing evidence. Independent damage
has an exact helper for runner destruction plus surviving-teammate erosion.
Run-support definitions include the scoring runner's own contributions.

The retained actual-end-state erosion example is tested at -1/4. Additional
cases cover zero-PA exclusion, repeated beneficiaries, four acts by two agents,
two run contributors, generic role-parent exclusion and PAQ-2.1 completeness.

Focused follow-up validation passed 38 tests: 23 calculation tests, 8 SQL and
evidence tests, and 7 Explorer/API tests. The generator drift check passed.
The earlier 100-test report and immutable live capture above describe the
initial implementation; they were not rerun or rewritten as this follow-up.

The central gap register now distinguishes accepted meaning from remaining
graph evidence. Coaching, speed availability, replay research and preliminary
field selection are documented in the active batch review. Positive running
weights, speed-based error attribution, interference credit and the PAQ-A
comparison boundary remain unresolved. No additional live adapter is admitted
by these calculation changes.
