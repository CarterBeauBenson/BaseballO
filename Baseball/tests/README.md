# Tests

Run project-relative commands in this document from the `Baseball/` project
directory.

Repository-level validation remains in
[`../scripts/validate_repository.py`](../scripts/validate_repository.py). It
currently parses 103 SPARQL files, checks the RML and 117 generated pattern pages,
executes the web tests, verifies 51 canned and 17 advanced baselines, and checks
19 benchmark pairs, 19 reviewed routes, 38 optimized algebra plans, and 38
direct TDB2 captures. The active mapping provides its source and collision
validator under [`../sources/mlb-game/mapping/`](../sources/mlb-game/mapping/).

The Explorer suite proves that loaded MLB coverage is returned by the status
endpoint, the Plate Appearance Quality workflow is visibly featured, and the
reviewed query does not expose arbitrary SPARQL. It also covers flat
reviewed-question discovery, Unicode player names,
player-average PAQ calculation, and both SQL-backed PAQ views.

The same repository check validates all 43 dated schedule responses, 546
distinct final-game identities, official-date placement, six repeated schedule
entries, and the challenge/umpire-review regression discovered by the expanded
corpus.

The repository check also meta-validates the authoritative, query-index, and
reasoning-output SHACL profiles. Negative smoke graphs prove that incomplete
structures fail rather than passing vacuously.

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
181 proved obligations.

The abandoned NiFi control-plane, evidence-stage, and corpus-coordinator suites
were removed with their implementation. They are archived design history, not
current executable contracts.

The clean NiFi rebuild begins with a source-owned MLB Game process group. Its
checked-in provisioner and stage runner receive only focused parser and contract
checks during development; NiFi owns the live bounded proof. Teams, Leagues,
Divisions, People, Venues, and Transactions will each receive a separate
connector, process group, source SHACL gate, retry/quarantine boundary, and
focused contract test. Tests must not imply that one source lane controls or
acquires another.

The current detachable-source and exit-gate contract is checked offline with:

```powershell
python -m unittest .\tests\test_nifi_source_contracts.py
```

It verifies module-owned artifacts and graph namespaces, distinct endpoint
connectors (including People discovery/detail and both Transactions inputs),
and the rule that an external command reaches its next semantic stage only
through an explicit zero-exit gate.

With the local stack running, execute the offline end-to-end acceptance test from the project directory:

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

That test covers all 19 routes, current-index selection, exact runtime
equivalence, Auto fallback, and explicit Indexed fail-closed behavior.
