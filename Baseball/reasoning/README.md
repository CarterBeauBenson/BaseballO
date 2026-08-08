# Selective reasoning

BaseballO reasons over one explicitly selected plate appearance at a time. It
does not expose a full-game or corpus reasoning mode. Authoritative RML graphs
remain immutable; every result is a disposable inferred graph with a build
manifest and a reproducible ruleset fingerprint.

Three small profiles are available:

| Profile | Consequences | BFO CLIF basis |
| --- | --- | --- |
| `event-order` | precedence inverses and transitive paths | `order.cl` |
| `event-structure` | occurrent-part inverses and transitive paths | `occurrent-mereology.cl` |
| `participation` | RDF participant inverses; temporally qualified CLIF facts when supported | `participation.cl` |

Each profile has fixed limits for containment depth, nodes, source triples,
inferred triples, iterations, and wall-clock time. A limit violation fails the
run without publishing a graph. These limits are part of the hashed reasoning
contract, not command-line suggestions. The reasoner also has lower-level
system ceilings, so enlarging a profile cannot create a full-game mode.
The ruleset fingerprint covers the profile, pinned CLIF manifest, ontology
snapshots, and materializer source code.

## BFO source boundary

[`bfo-clif-manifest.json`](bfo-clif-manifest.json) pins the official BFO 2020
Common Logic modules to commit
`dd89f4a193038b66ef0e891d546c05a5b477f40f`, including byte counts and SHA-256
checksums. Fetch them into the local, untracked runtime cache with:

```powershell
python Baseball/scripts/reasoning/sync-bfo-clif.py --output "$env:LOCALAPPDATA\BaseballO\runtimes\bfo-clif-dd89f4a"
```

The materializer implements only the named, forward-safe projections declared
by a profile. It also emits a CLIF proof package containing the exact official
modules, translated asserted facts, and separately translated expected
entailments. A pinned Z3 backend checks consistency and proves each translated
expected entailment by refutation. This executes the selected CLIF axiom
projections; it is not an interpreter for arbitrary CLIF or a proof over the
complete BFO theory. Each obligation has a proof hash, and the complete report
is hashed into the build manifest.

Proof execution has separate hard ceilings: 200 obligations, 30 seconds for a
complete set, and five seconds for an individual solver check. A timeout,
unknown result, inconsistency, or unproved obligation fails before graph load.

RDF participation is binary while BFO CLIF participation is time-indexed. A
binary `has participant` assertion is translated into a three-place CLIF fact
only when the process has exactly one explicit `occupies temporal region`
value. Unsupported assertions are counted as omissions instead of being
silently assigned the whole plate-appearance interval.

## Run one bounded slice

```powershell
powershell -ExecutionPolicy Bypass -File Baseball/scripts/reasoning/run-selective-reasoning.ps1 `
  -GamePk 566279 `
  -Anchor https://baseballontology.org/data/game/566279/plate-appearance/0 `
  -Profile event-order
```

Add `-Load` to replace that exact disposable reasoning named graph in Fuseki.
The graph IRI includes the profile, game, anchor hash, and ruleset fingerprint,
so different profiles cannot overwrite one another. Loading is never implicit.

Run `python Baseball/scripts/reasoning/test-selective-reasoning.py` for positive,
negative, budget, deterministic-output, CLIF-export, and proof tests. The
checked-in [fixture proof baseline](evidence/fixture-566279-pa-0.json) records
107 of 107 proved obligations across the three profiles with Z3 5.0.0.

## Reviewed complexity comparison

[`reviewed-samples.json`](reviewed-samples.json) fixes two real plate
appearances from game 566279: a one-pitch field out and an eight-event,
multi-runner scoring single. The checked-in
[`reviewed sample evidence`](evidence/fixture-566279-reviewed-samples.json)
compares explicit and inferred predicate-query row sets for every profile.

| Case | Profile | Selected nodes | Inferred triples | Proved obligations |
| --- | --- | ---: | ---: | ---: |
| Simple | `event-order` | 18 | 24 | 24/24 |
| Simple | `event-structure` | 18 | 23 | 23/23 |
| Simple | `participation` | 22 | 15 | 4/4 |
| Complicated | `event-order` | 56 | 46 | 46/46 |
| Complicated | `event-structure` | 56 | 65 | 65/65 |
| Complicated | `participation` | 69 | 48 | 14/14 |

Regenerate the comparison against the current local fixture RDF with:

```powershell
python Baseball/scripts/reasoning/evaluate-reviewed-samples.py `
  --output-report Baseball/reasoning/evidence/fixture-566279-reviewed-samples.json
```

The evaluator never loads its disposable graphs into Fuseki.
