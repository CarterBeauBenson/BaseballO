# BaseballO current continuation plan

This is the repository's single current handoff document. It replaces the old
dated session notes and completed work orders. Do not restart completed tasks
unless a regression demonstrates that they are broken.

## Current verified state

- `dev` and `origin/dev` were synchronized when this handoff was written. Use
  Git at restart time for the current commit instead of trusting a pinned hash.
- Live MLB acquisition remains disabled. A single explicitly authorized
  acquisition captured the completed 2026-08-03 schedule and game feeds; it
  did not enable the parked acquisition pipeline.
- Do not bulk-download the post-All-Star-break corpus from MLB Digital
  Properties under the current setup. The [MLB Terms of
  Use](https://www.mlb.com/official-information/terms-of-use) prohibit automated
  scripts that collect from or interact with those properties. Seek written
  authorization through the official [StatsAPI registration
  page](https://inside.mlb.com/UserRegistrationForm/?GROUP=StatsAPI), or choose
  a licensed/open source before expanding the corpus.
- Raw game JSON is preserved byte-for-byte. The complete event graph remains
  authoritative; the query index is disposable and reproducible.
- The active RML contains 247 triples maps, 56 logical sources, and no
  referencing-object joins.
- Fixture game `566279` produces 28,419 authoritative triples and 6,617
  query-index triples. All eleven supported semantic row sets, including exact
  UTF-8 label fidelity, are equivalent.
- All eight completed 2026-08-03 games are loaded independently. Together
  they contain 228,576 authoritative triples, 53,542 query-index triples, 823
  runner resolutions, and 11 stolen-base processes. Every per-game
  authoritative/index equivalence suite passes.
- All 48 canned queries have been reviewed and executed against the eight-game
  corpus. Every query returns rows, no query returns duplicate result rows, and
  the RDF-term-aware row sets are content-hashed for regression checks.
  Forty-six are structurally index-ready; `empty-games-prototype.rq` and
  `game-timeline.rq` remain authoritative.
- A separate 16-query advanced semantic suite now covers PA fingerprints,
  grinder scoring, swing/contact funnels, take/whiff profiles, matchups,
  productive movement, contact conversion, rally anatomy, action density,
  scorer and umpire profiles, hit diversity, base destinations, steal attempts,
  unproductive contact games, and event-chain integrity. Its eight-game audit
  records exact row sets and currently exposes three baserunning-only terminal
  outcomes (`pickoff_1b` twice and `caught_stealing_2b` once) that still use the
  generic result pattern. `intent_walk` now reuses the full walk pattern.
- Ten representative authoritative/indexed query pairs have exact corpus
  results, 20-sample alternating timings, optimized ARQ algebra, and direct
  TDB2 execution captures. Seven traversal-heavy pairs improve by 2.10x to
  9.73x at the median; the three simple lookup pairs are effectively neutral.
- Query-index generation now preserves Fuseki's UTF-8 Turtle bytes directly.
  The corpus benchmark exposed and the eleven-family equivalence gate now
  prevents correctly accented player labels from becoming mojibake.
- Portable dehydration packages can export, validate, detect modified bytes,
  and restore both named graphs. Failed index construction removes the stale
  derived graph without changing the authoritative graph.
- A playable loopback-only BaseballO Explorer now exposes the four allowlisted
  analytics families. It builds filter lists from loaded graph values, returns
  result tables, exports CSV, and shows the generated SPARQL. The server accepts
  component selections rather than arbitrary SPARQL and queries only
  authoritative game graphs.
- The Explorer's dedicated Advanced view exposes all 16 cataloged semantic
  queries through allowlisted IDs. It shows each query's claim and evidence mode
  before execution and never accepts browser-supplied SPARQL or file paths.
- Empty Games is exposed separately as a reviewed prototype because its
  negative completeness semantics do not belong in the general component
  compiler. Its set-based authoritative query returns a 26-player result set
  across the eight-game audit corpus after intentional walks were added to the
  reviewed completeness profile, while avoiding repeated correlated
  absence checks.
- Canonical canned queries and the UI query builder remain authoritative. A
  separate reviewed runner now routes the seven proven traversal-heavy query
  pairs to the index and leaves the three neutral pairs authoritative. It
  scopes execution to the loaded graph set, verifies current local manifests
  and graph metadata, falls back safely in Auto mode, and fails closed when
  Indexed mode is explicitly requested without a current index.
- No query-index shortcut term has been added to the ontology.

## Work that is complete - do not redo

- granular act/process/judgment/result RML redesign;
- nested RML context correction and terminal-time correction;
- RML-to-Mermaid generator and current pattern diagrams;
- the 48-query structural review and UI component synchronization;
- the 16-query advanced semantic catalog and reproducible corpus audit;
- query-index contract version 1 and its 12 `CONSTRUCT` components;
- single-fixture equivalence, benchmarks, and optimized algebra capture;
- eight-game canned-query audit, corpus query-index benchmark, UTF-8 label
  fidelity gate, and direct TDB2 execution capture;
- evidence-driven operational routing for seven indexed and three
  authoritative query pairs, including live equivalence, fallback, and
  fail-closed tests;
- portable dehydration-package export, validation, tamper testing, and exact
  graph restoration;
- malformed-component/stale-index recovery testing;
- structural `(atBatIndex, runnerIndex)` identities for runner acts, records,
  resolutions, judgments, decisions, and base-touching processes;
- processor-safe runner-category and sacrifice-bunt source partitioning;
- complete fielders-choice-out batted-result sequencing;
- per-game guarded import and exact index equivalence for all eight completed
  2026-08-03 games;
- multi-game-safe fixture acceptance and refreshed single-fixture benchmark
  evidence;
- the first local BaseballO Explorer with live graph status, batting, pitching,
  baserunning, and game views, graph-backed select boxes, CSV export, generated
  query inspection, a dedicated Empty Games review view, and a tested read-only
  server boundary.

## Current corpus

The checked-in corpus is under [`data/raw/samples/2026-08-03/`](data/raw/samples/2026-08-03/).
It contains the original `schedule.json` plus completed game feeds `822867`,
`823431`, `823520`, `823757`, `824160`, `824324`, `824647`, and `825095`.
The schedule is acquisition metadata and is not an RML input. All raw bytes are
preserved and content-addressed archive hashes match their checked-in sources.

## Next work, in order

### 1. Review advanced analytics in the Explorer

- Review the dedicated catalog-driven Advanced view against real research
  questions; its unlike result shapes intentionally remain outside the general
  select-box compiler.
- Preserve semantic-mode and completeness warnings in the interface, especially
  for takes/whiffs, steal-attempt efficiency, and unproductive contact games.
- Decide how baserunning-only `allPlays` terminal sequences relate to
  `PlateAppearance`. The current three findings must remain explicit until the
  owner chooses an existing class or approves an ontology change; do not assign
  them an unrelated result rule merely to make the audit empty.

### 2. Evaluate advanced query-index coverage

- Build indexed companions for the remaining structurally index-ready canned
  queries in small semantic families rather than switching all 46 at once.
- Classify each advanced query separately. The event-chain audit and
  completeness-gated negative queries should remain authoritative unless an
  index contract can preserve their evidence boundary exactly.
- Require exact eight-game row equivalence and repeatable timing evidence for
  every added route. Keep neutral or slower queries authoritative.
- Add a route only through
  [`operational-query-routing.json`](sparql/query-index/operational-query-routing.json)
  so the evidence, selected layer, and fallback policy remain reviewable.

### 3. Preserve the operational safety boundary

- Keep authoritative companions available for audit, fallback, and regression
  tests; never overwrite them with shortcut query shapes.
- Keep Auto fallback and explicit Indexed fail-closed behavior under executable
  acceptance tests as the route set grows.
- Keep `empty-games-prototype.rq` authoritative unless its negative
  completeness semantics are explicitly redesigned.
- Keep `game-timeline.rq` authoritative unless terminal-time evidence is added
  to a reviewed index contract.
- Do not wire the UI compiler to the operational router until its interaction
  model is reviewed separately.

### 4. Return to broader Explorer usability after query coverage

- Review labels, defaults, grouping, result columns, and visual hierarchy after
  the current query-acceleration path is complete.
- Add select-box components only for questions the owner identifies; do not
  expose arbitrary browser-supplied SPARQL.
- Give each compiled shape an authoritative regression companion and an
  indexed companion only where the materialized contract covers it.
- Re-run the 48-query audit whenever a canonical query changes, and re-run the
  corpus benchmark whenever an indexed benchmark query or index contract
  changes.
- Re-run the independent 16-query advanced audit whenever its queries or
  catalog claims change.

### 5. Hold ontology decisions separately

Do not promote `https://w3id.org/baseball/query-index/` terms into BaseballO
without the project owner's explicit approval of their names, directions,
domains, ranges, and relationship to BFO participation and contextual roles.
Continue reporting source or ontology gaps rather than silently solving them in
SPARQL, RML, or the operational index.

## Persistent guardrails

1. Never modify supplied or archived raw JSON.
2. Never enable live acquisition without explicit instruction.
   Explicit instruction is not a substitute for source authorization where the
   provider's published terms prohibit automated collection.
3. Never modify [`ontology/`](ontology/) without an explicit ontology request.
4. Never accept a stale or partial query index as current.
5. Never infer semantic absence from a graph that has not passed completeness
   and equivalence checks.
6. Never migrate a query solely because it is structurally index-ready.
7. Keep changes on `dev`; validate, commit, and publish completed work there.

## Current reference documents

- Query classification: [`sparql/query-index/query-decision-matrix.md`](sparql/query-index/query-decision-matrix.md)
- Query inventory: [`sparql/query-inventory.md`](sparql/query-inventory.md)
- Advanced analytics: [`sparql/advanced/`](sparql/advanced/)
- Advanced query audit: [`benchmarks/advanced-query-audit/`](benchmarks/advanced-query-audit/)
- Index construction: [`sparql/query-index/README.md`](sparql/query-index/README.md)
- Benchmark method/results: [`benchmarks/query-index/`](benchmarks/query-index/)
- Dehydration and restoration: [`sparql/query-index/dehydration-package.md`](sparql/query-index/dehydration-package.md)
- RML visual review: [`mermaid/README.md`](mermaid/README.md)
- Local analytics explorer: [`web/README.md`](web/README.md)

## Restart checks

From the repository root:

```powershell
git status --short
git branch --show-current
git fetch origin dev
python Baseball/scripts/validate_repository.py
```

The 2026-08-03 corpus is already imported. Do not reacquire or reimport it
unless a changed mapping or contract requires an explicit idempotent rebuild.
