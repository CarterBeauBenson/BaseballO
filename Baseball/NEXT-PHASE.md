# BaseballO next phase plan

Resume this plan on or after **2026-08-05**. The repository is deliberately
paused with the live MLB acquisition flow disabled.

## Progress on 2026-08-04

- The accepted corpus inventory confirmed that game `566279` is still the only
  active raw completed-game fixture. The archived preprocessing artifact is not
  a second accepted fixture.
- All 48 canned queries are classified in
  [`sparql/query-index/query-decision-matrix.md`](sparql/query-index/query-decision-matrix.md):
  46 are structurally index-ready and two remain authoritative.
- Ten reviewed indexed companions now cover hits, batting, pitching,
  baserunning, games, assignments, and UI options.
- The index builder now runs exact semantic row equivalence before writing a
  current manifest; shape-valid but incomplete indexes are removed.
- A reproducible 20-iteration single-fixture benchmark is recorded under
  [`benchmarks/query-index/`](benchmarks/query-index/). All ten result sets were
  exactly equivalent. Indexed medians ranged from 1.011x to 3.720x faster on
  this fixture.
- Canonical query and UI migration remains intentionally deferred pending
  additional deliberately supplied fixtures and query-plan review. The timing
  result is method-validation evidence, not a scale claim.
- Portable package version 1 is implemented and exercised. It preserves raw
  bytes, both exact RDF graphs, both build manifests, repository generator
  contracts, graph identities, counts, and hashes in a closed inventory.
- Exact package rehydration restored both fixture graphs and passed semantic
  equivalence. Tampered bytes were rejected, and malformed `CONSTRUCT` failure
  left the authoritative graph intact while removing and rebuilding the stale
  derived graph.
- Optimized ARQ algebra is captured for all ten benchmark pairs with pinned
  Jena 6.1.0. Hits shrink from 24 to 8 triple patterns and pitch summary from
  18 to 10; the nearly neutral umpire/options benchmarks show no triple-pattern
  reduction. Storage-specific TDB2 execution logging remains distinct and
  pending.

## Entry state

- Branch `dev` is published through commit `aba8cd3`.
- Commit `795b11f` corrected the nested RML event context without changing raw
  source data.
- Commit `aba8cd3` added the separate per-game query-index graph.
- The authoritative fixture graph contains 29,736 triples.
- Its disposable query index contains 6,981 triples, about 23.5 percent of the
  authoritative graph.
- Twelve `CONSTRUCT` components live under
  [`sparql/query-index/components/`](sparql/query-index/components/).
- Exact full/index row equivalence passes for game dimensions,
  plate-appearance results, hits, pitches, pitch calls, batting acts, contacts,
  runner resolutions, stolen bases, and game assignments.
- The existing 48 canned queries and both UI query builders still query the
  authoritative patterns. They have not silently been redirected to the
  shortcut graph.
- No files under [`ontology/`](ontology/) were changed for the operational
  shortcut vocabulary.

## Non-negotiable constraints

1. Keep the raw JSON byte-identical and keep the complete event graph as the
   source of truth.
2. Keep external MLB acquisition off until the project owner explicitly
   reopens it. Use only checked-in or deliberately supplied local fixtures.
3. Do not modify the ontology without an explicit ontological decision from
   the project owner.
4. Treat the query index as disposable. A failure may make it unavailable but
   must never leave stale shortcut assertions presented as current.
5. Preserve exact answer equivalence before moving any consumer from a full
   pattern to an indexed pattern.
6. Do not treat faster execution as permission to weaken the success pattern
   that creates a shortcut fact.

## Phase objective

Decide, with measurements and equivalence evidence, which canned and
UI-compiled queries should use the dehydrated graph. Then make those migrations
without changing their baseball meaning or obscuring the authoritative
evidence.

## Ordered work plan

### 1. Establish the benchmark corpus

- Inventory any additional completed-game JSON files deliberately supplied to
  the repository or manual inbox.
- Do not fetch games from the live API to enlarge the corpus.
- If only game `566279` is available, complete correctness and single-game
  measurements first and record multi-game scale testing as externally
  blocked, rather than manufacturing acceptance evidence.
- Record source hashes and expected graph counts for every accepted fixture.

### 2. Build a full-versus-index query decision matrix

Classify all 48 canned queries and the UI component families as:

- `index`: every required fact and dimension exists in the shortcut contract;
- `hybrid`: an indexed fact still needs an authoritative-only traversal; or
- `authoritative`: the index does not represent the required distinction.

For each query record the counted entity, full pattern, indexed pattern,
required shortcut component, and equivalence test. Start with hits, pitches,
plate-appearance outcomes, runner resolutions, assignments, and their option
queries. Do not force every query onto the index merely for uniformity.

### 3. Benchmark before migration

- Capture full and indexed result sets, elapsed times, and Fuseki/TDB2 query
  plans for representative queries.
- Measure cold and warm executions separately and repeat them enough to avoid
  treating one timing as evidence.
- Record graph counts and corpus size with every result.
- Compare datastore indexing/query-plan improvements with materialized-view
  improvements before proposing custom TDB2 index changes.
- Store the benchmark method and results in the repository so decisions are
  reproducible.

### 4. Add indexed companions, then migrate consumers

- Create reviewable indexed companions for approved canned queries.
- Extend exact bidirectional row-set tests before switching the canonical
  query or UI component.
- Update the allowlisted UI compiler with fixed index patterns; never accept
  user-provided SPARQL fragments or graph IRIs.
- Keep authoritative versions available for audit and regression comparison.
- Update [`sparql/query-inventory.md`](sparql/query-inventory.md) with the
  selected execution layer and evidence for every migrated query.

### 5. Define the dehydration package

Specify a portable manifest containing at least:

- raw content hash and archive identity;
- RML, execution-context builder, and mapper versions/hashes;
- authoritative RDF hash and graph IRI;
- query-index contract hash, index hash, graph IRI, and fact counts; and
- the commands and ordering required to rematerialize the authoritative graph
  before regenerating the query index.

The 6,981-triple query index is not sufficient to reconstruct the full graph.
Rehydration depends on the preserved raw source and mapping provenance.

### 6. Exercise failure and invalidation behavior

Add tests for a malformed `CONSTRUCT` component, invalid constructed RDF,
contract-hash change, authoritative graph replacement, failed Graph Store
`PUT`, and missing index graph. Each test must confirm that the authoritative
graph remains intact and that an old derived graph is not accepted as current.

### 7. Hold a separate ontology review

After operational evidence exists, review whether any shortcut deserves
promotion into BaseballO. Until the project owner approves its name,
direction, domain, range, and relationship to BFO participation and roles,
keep every `https://w3id.org/baseball/query-index/` term operational only.

## Phase exit criteria

- Every migrated query has exact full/index equivalence across the accepted
  fixture corpus.
- The 48-query inventory identifies `index`, `hybrid`, or `authoritative` for
  every query.
- A reproducible benchmark report supports each migration decision.
- Forced rebuild, unchanged-current, invalidation, and failure paths are
  tested.
- The dehydration/rehydration manifest contract is documented and exercised.
- Repository validation passes, the raw fixtures remain unchanged, and the
  live acquisition flow remains disabled.

## Restart checklist

From the repository root:

```powershell
git status --short
git branch --show-current
git fetch origin dev
python Baseball/scripts/validate_repository.py
```

Expected state: branch `dev`, clean worktree, and no divergence from
`origin/dev`. If local Fuseki testing is needed:

```powershell
.\Baseball\scripts\infra\start-fuseki.ps1
.\Baseball\scripts\pipeline\test-manual-vertical-slice.ps1
```

The second command uses the checked-in fixture, makes no external acquisition
request, verifies the authoritative graph, and runs the full query-index
equivalence suite.
