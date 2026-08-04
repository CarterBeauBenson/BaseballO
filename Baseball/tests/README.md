# Tests

Repository-level validation remains in
[`../scripts/validate_repository.py`](../scripts/validate_repository.py). It
currently parses 95 SPARQL files, checks the RML and 93 generated pattern pages,
executes the web tests, verifies 48 canned and 16 advanced baselines, and checks
18 benchmark pairs, 18 reviewed routes, 36 optimized algebra plans, and 36
direct TDB2 captures. The active mapping provides its source and collision
validator under [`../mappings/direct/`](../mappings/direct/).

With the local stack running, execute the offline end-to-end acceptance test from the repository root:

```powershell
.\scripts\pipeline\test-manual-vertical-slice.ps1 -ForceRdfLoad
```

The test uses only the checked-in fixture and loopback Fuseki. It checks
source/archive byte identity, RML manifest hashes, source-to-RDF counts, the
expected named graph, and twelve authoritative/index semantic row families. It
makes no external data request.

With the eight-game corpus loaded, route safety is exercised separately:

```powershell
.\scripts\pipeline\test-reviewed-query-routing.ps1
```

That test covers all 18 routes, current-index selection, exact runtime
equivalence, Auto fallback, and explicit Indexed fail-closed behavior.
