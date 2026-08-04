# Query-index benchmarks

This directory stores reproducible, exploratory comparisons between existing
authoritative canned queries and reviewed indexed companions. Generate the
single-fixture baseline from the repository root with loopback Fuseki running:

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

Results from game `566279` are method-validation evidence only. They are not a
multi-game performance or TDB2-indexing claim. Query-plan capture and scale
acceptance remain pending until additional completed-game fixtures are
deliberately supplied without enabling live acquisition.

The current 20-iteration result is recorded in
[`fixture-566279-baseline.md`](fixture-566279-baseline.md), with raw samples and
provenance in [`fixture-566279-baseline.json`](fixture-566279-baseline.json).
