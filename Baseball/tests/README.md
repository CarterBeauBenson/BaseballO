# Tests

Repository-level validation remains in
[`../scripts/validate_repository.py`](../scripts/validate_repository.py). It
currently parses 96 SPARQL files, checks the RML and 107 generated pattern pages,
executes the web tests, verifies 48 canned and 17 advanced baselines, and checks
18 benchmark pairs, 18 reviewed routes, 36 optimized algebra plans, and 36
direct TDB2 captures. The active mapping provides its source and collision
validator under [`../mappings/direct/`](../mappings/direct/).

The same repository check validates all 24 dated schedule responses, 288
distinct final-game identities, official-date placement, six repeated schedule
entries, and the challenge/umpire-review regression discovered by the expanded
corpus.

The repository check also meta-validates 37 SHACL node shapes across the
authoritative, query-index, and reasoning-output profiles. Negative smoke
graphs prove that an incomplete `PitchAct`, `HitFact`, and reasoning provenance
envelope fail rather than passing vacuously.

Selective reasoning has a separate offline suite:

```powershell
python .\scripts\reasoning\test-selective-reasoning.py
```

It proves plate-appearance isolation, expected order/part/participant
consequences, rejection of precedence cycles, hard budget failure,
deterministic serialization, and temporally qualified CLIF translation.
The profile-admission contract also requires positive and forbidden
entailments plus every semantically applicable contradiction case for each
profile before repository validation accepts it.
The same test executes a bounded Z3 proof, while repository validation checks
the committed 107-obligation fixture proof baseline against current profile,
reasoner, and prover fingerprints.
It also validates the six-run reviewed simple/complicated comparison, including
profile and ruleset hashes, fixed budgets, predicate-query row hashes, and all
176 proved obligations.

The NiFi evidence runner also has an offline regression suite:

```powershell
python .\tests\test_nifi_evidence_stage.py
```

It proves successful manifest generation, unchanged-input skipping,
dependency-triggered reruns, nonzero exit propagation, and failure quarantine.

The staged per-game flow has an offline contract suite:

```powershell
python .\tests\test_nifi_game_flow.py
```

It verifies byte-identical archival, work-request creation, dependency
assessment evidence, strict local path boundaries, and raw-hash failure
quarantine. With the local stack running, `test-nifi-rdf-flow.ps1` additionally
forces all six semantic processors through a complete fixture rebuild.

The promotion-driven corpus coordinator has its own offline contract suite:

```powershell
python .\tests\test_nifi_corpus_flow.py
```

It verifies incomplete-submission waiting, exactly-once audit queueing from
matching promotion markers, and fingerprinted completion across all four
corpus audit gates.

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
