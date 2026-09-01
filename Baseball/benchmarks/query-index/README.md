# Query-index benchmarks

This directory stores reproducible comparisons between existing authoritative
canned queries and reviewed indexed companions. Generate the single-fixture
method baseline from the repository root with loopback Fuseki running:

```powershell
.\Baseball\scripts\pipeline\benchmark-query-index.ps1 `
  -GamePk 566279 `
  -Iterations 20
```

The benchmark scopes every query to the explicit authoritative or query-index
graph for the supplied game, verifies exact SPARQL JSON result bindings before
timing, primes both paths, and alternates execution order across repeated
samples. It measures loopback request/response latency, JSON serialization, and
query execution together.

Results from game `566279` are method-validation evidence only. The historical
capture is recorded in [`fixture-566279-baseline.md`](fixture-566279-baseline.md),
with raw samples and provenance in
[`fixture-566279-baseline.json`](fixture-566279-baseline.json).

Generate the eight-game 2026-08-03 corpus baseline with:

```powershell
.\Baseball\scripts\pipeline\benchmark-query-index-corpus.ps1 `
  -Iterations 20 `
  -OutputDirectory "$env:LOCALAPPDATA\BaseballO\state\benchmarks\query-index-candidate"
```

The corpus baseline verifies exact authoritative/indexed bindings before it
times either path. The preserved capture covers 19 pairs with 20 alternating
samples per layer. Sixteen reviewed pairs improve by 1.509x to 1923.986x at the
median. The admitted `hits-by-season` route has exact results and improves by
799.406x. `umpire-assignments` and
`available-players` remain operationally authoritative because their simple
lookup shapes are effectively neutral. `games-by-team-and-season` remains an
explicitly reviewed conservative authoritative selection. See
[`corpus-2026-08-03-baseline.md`](corpus-2026-08-03-baseline.md) and its
machine-checkable [JSON baseline](corpus-2026-08-03-baseline.json).

[`evidence-register.json`](evidence-register.json) records each immutable
capture's timestamp, commit, contract hash, and artifact hash. A contract
change marks old evidence historical; it never licenses editing a captured
hash or timing in place. New measurements are written as new captures and then
reviewed for operational admission. The separate
[`operational-query-routing.json`](../../sparql/query-index/operational-query-routing.json)
records measured, admitted, and explicitly reviewed compatible contract hashes;
compatibility does not change the identity of the evidence it admits.

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
.\Baseball\scripts\pipeline\capture-tdb2-query-execution.ps1 `
  -OutputDirectory "$env:LOCALAPPDATA\BaseballO\state\benchmarks\tdb2-execution-candidate"
.\Baseball\scripts\infra\start-fuseki.ps1
```

Its normalized, hashed logs retain Jena's query, optimized algebra, TDB2
algebra, and the first reordered execution trace for each layer. Repetitive
aggregate subexecutions are omitted. These are query-planning evidence, not
timing measurements. The preserved historical capture contains 38 logs:
authoritative and indexed layers for all 19 pairs.
