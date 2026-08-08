# BaseballO SHACL validation

This package is an executable graph-quality contract. It does not add ontology
axioms and it does not replace source-to-RDF count checks, query equivalence, or
reasoning.

## Profiles

- [`authoritative.ttl`](authoritative.ttl) validates stable structures produced
  by the direct RML: games, plate appearances, pitching and batting acts,
  contact and ball-motion chains, baserunning, adjudication, decisions, and
  record identity separation. It also validates pitch-ball control failures,
  passed-ball and wild-pitch scoring structures, uncaught-third-strike
  composites, and the non-fabrication boundary for unresolved runner records.
- [`query-index.ttl`](query-index.ttl) validates the disposable shortcut graph:
  one index resource and game, required fact fields, RDF term kinds, datatypes,
  and same-game containment.

Every enforced constraint is a `sh:Violation`. Source-supported but
ontologically unresolved conditions remain audit findings outside this suite;
the generic terminal pickoff and caught-stealing structures therefore do not
make an otherwise valid graph fail.

Validation runs with no entailment. The shapes check the explicit graph emitted
by the pipeline, which keeps conformance independent from the later reasoning
layer.

## Run manually

From the Git repository root:

```powershell
python Baseball/scripts/pipeline/validate-shacl.py `
  --profile authoritative `
  --data "$env:LOCALAPPDATA\BaseballO\state\pipeline\rdf\game-566279.ttl"

python Baseball/scripts/pipeline/validate-shacl.py `
  --profile query-index `
  --data "$env:LOCALAPPDATA\BaseballO\state\pipeline\query-index\game-566279.nt"
```

The RML runner validates authoritative RDF before publishing it. The index
builder validates compiled N-Triples before replacing the disposable named
graph. Dehydration-package validation repeats both checks before accepting a
portable graph package.

## Design policy

- Constrain only structures the active mapping or index contract promises.
- Use qualified counts when a property intentionally has heterogeneous values.
- Keep JSON/RDF count comparison in the source-aware procedural validator.
- Keep exact authoritative/index row equivalence in the index acceptance test.
- Add reasoning only after explicit, non-inferred data passes these profiles.
