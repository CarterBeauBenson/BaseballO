# BaseballO continuation plan

This is the single current handoff. Completed implementation details belong in
the subsystem READMEs and Git history; do not recreate them here.

## Verified state

- Live MLB acquisition is disabled pending an authorized source. The checked-in
  2026-08-03 corpus must not be reacquired merely to rerun the local workflow.
- Raw JSON is immutable. The full event graphs are authoritative; query-index
  graphs are disposable and reproducible.
- The active RML has 247 triples maps, 56 logical sources, and no
  referencing-object-map joins.
- Eight completed games produce 228,576 authoritative triples and 52,944 index
  triples. All per-game semantic equivalence checks pass.
- Two explicit, non-entailing SHACL profiles contain 30 node shapes. The
  fixture and all eight corpus graph pairs conform with zero results; RML,
  index, and dehydration workflows now fail closed on violations.
- The query library contains 48 canned and 16 advanced queries with reproducible
  corpus baselines.
- Eighteen authoritative/index pairs have exact results and benchmark evidence.
  The reviewed runner uses 15 indexed routes and keeps three neutral routes
  authoritative.
- The loopback Explorer provides four compiled analytics families, Empty Games,
  and the 16-query Advanced catalog. Browser queries remain allowlisted and
  authoritative-only.
- Intentional walks use the complete walk pattern. Three source-limited terminal
  baserunning outcomes remain explicit generic results for ontological review.
- No query-index shortcut terms have been added to the ontology.

## Next work

### 1. Begin the reasoning experiment

- Inventory intended entailments before choosing a rule profile. Start with
  safe class and property consequences already supported by the ontology; do
  not encode unresolved baseball interpretations as rules.
- Keep asserted authoritative graphs immutable. Materialize inferred statements
  into a separate, replaceable per-game reasoning graph with provenance and a
  reproducible ruleset fingerprint.
- Establish positive and negative entailment fixtures, contradiction checks,
  and query-result comparisons before allowing inferred graphs into analytics.
- Run SHACL on explicit graphs before reasoning. Add post-reasoning shapes only
  for constraints whose semantics remain valid over the inferred closure.

### 2. Review the Explorer

- Evaluate the Advanced view against real research questions.
- Decide how the three generic terminal baserunning outcomes should relate to a
  plate appearance. Keep them explicit until the owner approves the model.
- Record confusing labels, defaults, groupings, and result columns, but defer a
  broad visual redesign until the query path is settled.

### 3. Expand index coverage carefully

- Add indexed companions in small semantic families.
- Require exact eight-game row equivalence and repeatable timing evidence for
  every route; keep neutral, slower, or incomplete shapes authoritative.
- Add routes only through
  [`operational-query-routing.json`](sparql/query-index/operational-query-routing.json).
- Treat negative and integrity queries as completeness-sensitive. Do not run
  them against an index unless their required evidence sets are proven complete.

### 4. Preserve the execution boundary

- Retain authoritative queries for audit, fallback, and regression testing.
- Keep Auto fallback and explicit Indexed fail-closed behavior tested.
- Keep the Explorer authoritative-only until its interaction with the reviewed
  router is designed and tested.
- Re-run the canned or advanced corpus audit whenever its queries change, and
  re-run equivalence and benchmarks whenever an indexed shape changes.

## Guardrails

1. Never modify raw or archived JSON.
2. Never enable live acquisition without explicit instruction and an authorized
   source.
3. Never modify [`ontology/`](ontology/) without an explicit ontology request.
4. Never accept a stale or partial index as current.
5. Never infer absence without proven completeness.
6. Work on `dev`; validate, commit, and publish completed changes there.

## References

- [Query library and classification](sparql/README.md)
- [Query-index contract](sparql/query-index/README.md)
- [Benchmark evidence](benchmarks/query-index/README.md)
- [RML and Mermaid review](mermaid/README.md)
- [SHACL validation](shacl/README.md)
- [Explorer](web/README.md)
- [Manual pipeline](scripts/pipeline/README.md)

## Restart

From the Git repository root:

```powershell
git status --short
git branch --show-current
git fetch origin dev
python Baseball/scripts/validate_repository.py
```

The corpus is already imported. Rebuild it only when a mapping or index-contract
change requires an explicit idempotent rerun.
