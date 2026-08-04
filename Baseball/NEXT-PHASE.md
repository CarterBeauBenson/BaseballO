# BaseballO current continuation plan

This is the repository's single current handoff document. It replaces the old
dated session notes and completed work orders. Do not restart completed tasks
unless a regression demonstrates that they are broken.

## Current verified state

- `dev` and `origin/dev` were synchronized when this handoff was written. Use
  Git at restart time for the current commit instead of trusting a pinned hash.
- Live MLB acquisition remains disabled. New data must come from deliberately
  supplied local files.
- Raw game JSON is preserved byte-for-byte. The complete event graph remains
  authoritative; the query index is disposable and reproducible.
- The active RML contains 247 triples maps, 56 logical sources, and no
  referencing-object joins.
- Fixture game `566279` produces 29,736 authoritative triples and 6,981
  query-index triples. All supported semantic row sets are equivalent.
- All 48 canned queries have already been reviewed. Forty-six are structurally
  index-ready; `empty-games-prototype.rq` and `game-timeline.rq` remain
  authoritative.
- Ten representative authoritative/indexed query pairs have exact-result
  tests, timing measurements, and optimized ARQ algebra captures.
- Portable dehydration packages can export, validate, detect modified bytes,
  and restore both named graphs. Failed index construction removes the stale
  derived graph without changing the authoritative graph.
- No canonical canned query or UI query builder has been redirected to the
  index yet. The single-game measurements are not sufficient for that decision.
- No query-index shortcut term has been added to the ontology.

## Work that is complete - do not redo

- granular act/process/judgment/result RML redesign;
- nested RML context correction and terminal-time correction;
- RML-to-Mermaid generator and current pattern diagrams;
- the 48-query authoritative audit and UI component synchronization;
- query-index contract version 1 and its 12 `CONSTRUCT` components;
- single-fixture equivalence, benchmarks, and optimized algebra capture;
- portable dehydration-package export, validation, tamper testing, and exact
  graph restoration; and
- malformed-component/stale-index recovery testing.

## Immediate input

The project owner is populating a directory named `games_from_8-3`. Treat that
directory as an incoming local corpus, not as permission to call an external
API. Do not touch it until the copy is complete. Then locate it explicitly
rather than assuming whether it sits at the repository root or under
`Baseball/`.

## Next work, in order

### 1. Inventory the supplied corpus without modifying it

For every file under `games_from_8-3`:

- parse JSON and record its relative path, SHA-256, byte count, `gamePk`,
  season, and game state;
- require a safe numeric `gamePk` and completed (`Final`) state before RDF
  processing;
- identify byte-identical files and duplicate `gamePk` values;
- distinguish malformed, incomplete, non-game, and unsupported files without
  rewriting or deleting any source; and
- write the inventory separately from the supplied files.

Stop before ingestion if two different byte streams claim the same completed
game and the correct version cannot be determined from existing policy.

### 2. Run a guarded multi-game import

- Use the existing manual importer, content-addressed raw archive, RML
  validator, per-game authoritative graph, and per-game query-index builder.
- Process games independently so one rejected game does not obscure the status
  of the others.
- Preserve per-game input, mapping, context-builder, RDF, index, and contract
  hashes in manifests.
- Confirm failed mappings leave no stale query-index graph.
- Do not weaken a success pattern merely to make a new source file pass.

### 3. Extend correctness checks to the corpus

- Require complete pitch, swing/bunt, contact, result, runner-resolution, and
  assignment context for every accepted game.
- Run exact authoritative/index equivalence per game.
- Run the 48 authoritative canned queries across the accepted multi-game
  corpus and inspect unexpected zeroes, duplication, or cross-game joins.
- Add regression fixtures only by reference/hash; do not edit supplied raw
  JSON to manufacture expected results.

### 4. Repeat performance evaluation at multi-game scale

- Rerun the ten authoritative/indexed benchmark pairs with corpus size and
  graph counts recorded.
- Measure first and repeated executions separately and alternate execution
  order.
- Capture TDB2 storage-specific execution logging in addition to the existing
  high-level optimized ARQ algebra.
- Compare datastore query planning with the materialized shortcut graph before
  proposing nonstandard TDB2 indexes.

### 5. Decide query and UI migration

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

### 6. Hold ontology decisions separately

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

Before reading or importing `games_from_8-3`, confirm that the project owner
has finished copying it and inventory its contents read-only.
