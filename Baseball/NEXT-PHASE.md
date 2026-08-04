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
- Raw game JSON is preserved byte-for-byte. The complete event graph remains
  authoritative; the query index is disposable and reproducible.
- The active RML contains 247 triples maps, 56 logical sources, and no
  referencing-object joins.
- Fixture game `566279` produces 28,419 authoritative triples and 6,617
  query-index triples. All ten supported semantic row sets are equivalent.
- All eight completed 2026-08-03 games are loaded independently. Together
  they contain 228,571 authoritative triples, 53,530 query-index triples, 823
  runner resolutions, and 11 stolen-base processes. Every per-game
  authoritative/index equivalence suite passes.
- All 48 canned queries have already been reviewed. Forty-six are structurally
  index-ready; `empty-games-prototype.rq` and `game-timeline.rq` remain
  authoritative.
- Ten representative authoritative/indexed query pairs have exact-result
  tests, timing measurements, and optimized ARQ algebra captures.
- Portable dehydration packages can export, validate, detect modified bytes,
  and restore both named graphs. Failed index construction removes the stale
  derived graph without changing the authoritative graph.
- No canonical canned query or UI query builder has been redirected to the
  index yet. Multi-game performance and full canned-query review remain
  necessary before that decision.
- No query-index shortcut term has been added to the ontology.

## Work that is complete - do not redo

- granular act/process/judgment/result RML redesign;
- nested RML context correction and terminal-time correction;
- RML-to-Mermaid generator and current pattern diagrams;
- the 48-query authoritative audit and UI component synchronization;
- query-index contract version 1 and its 12 `CONSTRUCT` components;
- single-fixture equivalence, benchmarks, and optimized algebra capture;
- portable dehydration-package export, validation, tamper testing, and exact
  graph restoration;
- malformed-component/stale-index recovery testing;
- structural `(atBatIndex, runnerIndex)` identities for runner acts, records,
  resolutions, judgments, decisions, and base-touching processes;
- processor-safe runner-category and sacrifice-bunt source partitioning;
- complete fielders-choice-out batted-result sequencing;
- per-game guarded import and exact index equivalence for all eight completed
  2026-08-03 games; and
- multi-game-safe fixture acceptance and refreshed single-fixture benchmark
  evidence.

## Current corpus

The checked-in corpus is under [`data/raw/samples/2026-08-03/`](data/raw/samples/2026-08-03/).
It contains the original `schedule.json` plus completed game feeds `822867`,
`823431`, `823520`, `823757`, `824160`, `824324`, `824647`, and `825095`.
The schedule is acquisition metadata and is not an RML input. All raw bytes are
preserved and content-addressed archive hashes match their checked-in sources.

## Next work, in order

### 1. Extend canned-query correctness checks to the corpus

- Run the 48 authoritative canned queries across the accepted multi-game
  corpus and inspect unexpected zeroes, duplication, or cross-game joins.
- Pay particular attention to source result types still intentionally outside
  specific mappings, including `pickoff_1b`, `caught_stealing_2b`, and
  `intent_walk`; do not infer unsupported acts merely to remove zeroes.
- Add regression expectations by reference/hash; never edit raw JSON to
  manufacture expected results.

### 2. Repeat performance evaluation at multi-game scale

- Rerun the ten authoritative/indexed benchmark pairs with corpus size and
  graph counts recorded.
- Measure first and repeated executions separately and alternate execution
  order.
- Capture TDB2 storage-specific execution logging in addition to the existing
  high-level optimized ARQ algebra.
- Compare datastore query planning with the materialized shortcut graph before
  proposing nonstandard TDB2 indexes.

### 3. Decide query and UI migration

- Use [`sparql/query-index/query-decision-matrix.md`](sparql/query-index/query-decision-matrix.md)
  as the starting classification.
- Migrate only queries with exact multi-game equivalence and a meaningful
  measured benefit.
- Keep authoritative companions available for auditing and regression tests.
- Keep `empty-games-prototype.rq` authoritative unless its negative
  completeness semantics are explicitly redesigned.
- Keep `game-timeline.rq` authoritative unless terminal-time evidence is added
  to a reviewed index contract.
- Update the allowlisted UI compiler only after the corresponding canned-query
  decision is recorded.

### 4. Hold ontology decisions separately

Do not promote `https://w3id.org/baseball/query-index/` terms into BaseballO
without the project owner's explicit approval of their names, directions,
domains, ranges, and relationship to BFO participation and contextual roles.
Continue reporting source or ontology gaps rather than silently solving them in
SPARQL, RML, or the operational index.

## Persistent guardrails

1. Never modify supplied or archived raw JSON.
2. Never enable live acquisition without explicit instruction.
3. Never modify [`ontology/`](ontology/) without an explicit ontology request.
4. Never accept a stale or partial query index as current.
5. Never infer semantic absence from a graph that has not passed completeness
   and equivalence checks.
6. Never migrate a query solely because it is structurally index-ready.
7. Keep changes on `dev`; validate, commit, and publish completed work there.

## Current reference documents

- Query classification: [`sparql/query-index/query-decision-matrix.md`](sparql/query-index/query-decision-matrix.md)
- Query inventory: [`sparql/query-inventory.md`](sparql/query-inventory.md)
- Index construction: [`sparql/query-index/README.md`](sparql/query-index/README.md)
- Benchmark method/results: [`benchmarks/query-index/`](benchmarks/query-index/)
- Dehydration and restoration: [`sparql/query-index/dehydration-package.md`](sparql/query-index/dehydration-package.md)
- RML visual review: [`mermaid/README.md`](mermaid/README.md)

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
