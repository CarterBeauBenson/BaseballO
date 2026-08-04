# Query-index benchmarks

This directory stores reproducible comparisons between existing authoritative
canned queries and reviewed indexed companions. Generate the single-fixture
method baseline from the repository root with loopback Fuseki running:

```powershell
.\Baseball\scripts\pipeline\benchmark-query-index.ps1 `
  -GamePk 566279 `
  -Iterations 20 `
  -OutputDirectory .\Baseball\benchmarks\query-index
```

The benchmark scopes every query to the explicit authoritative or query-index
graph for the supplied game, verifies exact SPARQL JSON result bindings before
timing, primes both paths, and alternates execution order across repeated
samples. It measures loopback request/response latency, JSON serialization, and
query execution together.

Results from game `566279` are method-validation evidence only. The current
result is recorded in [`fixture-566279-baseline.md`](fixture-566279-baseline.md),
with raw samples and provenance in
[`fixture-566279-baseline.json`](fixture-566279-baseline.json).

Generate the eight-game 2026-08-03 corpus baseline with:

```powershell
.\Baseball\scripts\pipeline\benchmark-query-index-corpus.ps1 `
  -Iterations 20 `
  -OutputDirectory .\Baseball\benchmarks\query-index
```

The corpus baseline verifies exact authoritative/indexed bindings before it
times either path. It currently covers 18 pairs with 20 alternating samples per
layer. Fifteen reviewed pairs improve by 1.38x to 48.02x at the median.
`games-by-team-and-season`, `umpire-assignments`, and `available-players`
remain operationally authoritative because their simple lookup shapes are
effectively neutral. See
[`corpus-2026-08-03-baseline.md`](corpus-2026-08-03-baseline.md) and its
machine-checkable [JSON baseline](corpus-2026-08-03-baseline.json).

`hitless-games-by-player` is benchmarked separately from ordinary positive
counts because it uses negative semantics. Its indexed companion returns the
same 65 corpus rows and is eligible only through the reviewed runner after all
selected per-game indexes pass current-manifest and complete
`PlateAppearanceFact`/`HitFact` equivalence checks.

High-level optimized ARQ algebra is captured separately under
[`algebra/`](algebra/). It uses the pinned Fuseki JAR's
`arq.qparse --print=opt` command and records every raw plan plus a triple-pattern
comparison. This is query-shape evidence, not TDB2 storage-specific runtime
join-order evidence.

Storage-level execution evidence is under
[`tdb2-execution/`](tdb2-execution/). Regenerate it only with Fuseki stopped,
because the direct read-only command opens the same persistent TDB2 datastore:

```powershell
.\Baseball\scripts\infra\stop-fuseki.ps1
.\Baseball\scripts\pipeline\capture-tdb2-query-execution.ps1
.\Baseball\scripts\infra\start-fuseki.ps1
```

Its normalized, hashed logs retain Jena's query, optimized algebra, TDB2
algebra, and the first reordered execution trace for each layer. Repetitive
aggregate subexecutions are omitted. These are query-planning evidence, not
timing measurements. The current capture contains 36 logs: authoritative and
indexed layers for all 18 pairs.
