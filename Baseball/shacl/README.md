# BaseballO SHACL validation

This package is an executable graph-quality contract. It does not add ontology
axioms and it does not replace source-to-RDF count checks, query equivalence, or
reasoning.

## Profiles and ownership

- [`../sources/mlb-game/shacl/authoritative.ttl`](../sources/mlb-game/shacl/authoritative.ttl)
  is owned by the MLB game source module and validates stable structures produced
  by its RML: games, plate appearances, pitching and batting acts,
  contact and ball-motion chains, baserunning, adjudication, decisions, and
  record identity separation. It forbids inferring a physical pitch-ball
  control failure from a passed-ball or wild-pitch label, while checking those
  institutional scoring structures, uncaught-third-strike
  composites, and the non-fabrication boundary for unresolved runner records.
- [`query-index.ttl`](query-index.ttl) validates the disposable shortcut graph:
  one index resource and game, required fact fields, RDF term kinds, datatypes,
  and same-game containment.
- [`reasoning-output.ttl`](reasoning-output.ttl) validates the closure-safe
  provenance envelope of a disposable inferred graph: its authoritative source,
  admitted profile, and complete ruleset fingerprint.

These are the core profiles. MLB-game operational admission profiles are
registered separately in
[`validation-profiles.json`](../sources/mlb-game/pipeline/validation-profiles.json),
including batting, runner, count, defense and clock checks. Each source module
owns its profiles and their runtime results.

The top-level SHACL directory contains only source-neutral derived-layer
contracts. Each source keeps its authoritative profiles inside its own
module. Source profiles must not constrain entities supplied by another source;
cross-source integrity questions belong in dependency-declared SPARQL or a
separately reviewed integration contract.

Every enforced constraint is a `sh:Violation`. Source-supported but
ontologically unresolved conditions remain audit findings outside this suite;
the generic terminal pickoff and caught-stealing structures therefore do not
make an otherwise valid graph fail.

Validation runs with no entailment. Authoritative shapes check the explicit
graph before reasoning. Reasoning-output shapes constrain only provenance
metadata whose meaning remains valid when inferred triples are present.

## Focused component diagnosis

NiFi owns routine execution. Use a command below only for the affected component
when diagnosing a recorded failure or checking a substantive change; these are
alternatives, not a manual pipeline checklist. Retained files may already have
been cleaned after promotion; use the exact artifact named by the owner evidence.

From the Git repository root:

```powershell
python Baseball/scripts/pipeline/validate-shacl.py `
  --profile authoritative `
  --data "$env:LOCALAPPDATA\BaseballO\state\pipeline\rdf\game-566279.ttl"

python Baseball/scripts/pipeline/validate-shacl.py `
  --profile query-index `
  --data "$env:LOCALAPPDATA\BaseballO\state\pipeline\query-index\game-566279.nt"

python Baseball/scripts/pipeline/validate-shacl.py `
  --profile reasoning-output `
  --data <selective-reasoning-build>\published.nt
```

The direct RML fallback validates authoritative RDF before returning it.
In NiFi, RML defers semantic validation to the separate source SHACL stage;
graph promotion follows its outcome. The index
builder validates compiled N-Triples before replacing the disposable named
graph. Dehydration-package
validation repeats the authoritative and index checks before accepting a
portable graph package.

## Design policy

- Constrain only structures the active mapping or index contract promises.
- Use qualified counts when a property intentionally has heterogeneous values.
- Keep JSON/RDF count comparison in the source-aware procedural validator.
- Keep exact authoritative/index row equivalence in the index acceptance test.
- Add reasoning only after explicit, non-inferred data passes these profiles.
- Do not apply explicit-graph cardinality assumptions to inferred closure;
  post-reasoning shapes must remain valid when sound entailments are added.
