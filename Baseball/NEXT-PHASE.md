# BaseballO continuation plan

This is the single current handoff. Completed implementation details belong in
the subsystem READMEs and Git history; do not recreate them here.

## Verified state

- External MLB acquisition requires an explicit approval switch; no unattended
  schedule is enabled. The checked-in 2026-07-14 through 2026-08-06 corpus must
  not be reacquired merely to rerun the local workflow.
- Raw JSON is immutable. The full event graphs are authoritative; query-index
  graphs are disposable and reproducible.
- The active RML has 297 triples maps, 83 logical sources, and no
  referencing-object-map joins.
- The accepted query baseline remains the eight-game 2026-08-03 subset, which
  produces 231,670 authoritative triples and 52,944 index triples. The expanded
  checked-in corpus contains 288 distinct completed games and is being promoted
  through the same per-game validation and equivalence gates.
- Two explicit, non-entailing SHACL profiles contain 35 node shapes. The
  fixture and all eight corpus graph pairs conform with zero results; RML,
  index, and dehydration workflows now fail closed on violations.
- The query library contains 48 canned and 17 advanced queries with reproducible
  corpus baselines.
- Eighteen authoritative/index pairs have exact results and benchmark evidence.
  The reviewed runner uses 15 indexed routes and keeps three neutral routes
  authoritative.
- The loopback Explorer provides four compiled analytics families, Empty Games,
  and the 17-query Advanced catalog. Browser queries remain allowlisted and
  authoritative-only.
- Pitching defaults now partition every mapped pitch into SME-labeled final
  call categories. Replay graphs distinguish the on-field judgment, optional
  challenge, replay-review act, both decisions, review-result ICE, and source
  record, with explicit ball/strike and out/safe transition classes. Reviews
  initiated by an umpire do not create a Challenge Act, and unsupported review
  decision families remain explicitly unclassified. Pitch reviews attach
  the on-field call to the home-plate umpire; the source still does not identify
  the individual base umpire for non-pitch reviews.
- Intentional walks use the complete walk pattern. Three source-limited terminal
  baserunning outcomes remain explicit generic results for ontological review.
- Passed balls and wild pitches now preserve a shared physical
  PitchBallControlFailureProcess while retaining separate scorer judgments,
  decisions, rules, and counted classifications. An uncaught third strike is a
  composite containing the strikeout and physical failure. MLB null runner
  placeholders remain event records and never fabricate baserunning acts or
  runner resolutions.
- Three selective reasoning profiles operate only on an explicitly anchored
  plate appearance. They enforce fixed computational budgets, preserve the
  authoritative graph, materialize into disposable fingerprinted graph IRIs,
  and emit pinned BFO CLIF proof packages. The published fixture slice produces
  52 order, 47 structure, and 30 participation inferences for plate appearance
  0; its three named graphs add four deterministic provenance triples each.
- A reviewed real-game comparison now exercises every profile over a one-pitch
  field out and an eight-event, multi-runner scoring single. The six bounded
  runs produced 24/23/15 and 46/65/48 inferences respectively, proved all 176
  translated obligations, and recorded explicit-versus-closure query hashes.
- New reasoning profiles are now fail-closed behind a data-driven admission
  contract. All three current semantic families declare fixed budgets,
  positive and forbidden entailments, and every applicable contradiction case;
  participation explicitly documents that no asymmetry constraint is present.
- The BFO CLIF source contract is pinned to commit
  `dd89f4a193038b66ef0e891d546c05a5b477f40f`. Z3 5.0.0 proved all 107
  translated fixture obligations and found all three asserted slices
  consistent. This covers the selected CLIF projections, not arbitrary CLIF or
  the complete BFO theory.
- No query-index shortcut terms have been added to the ontology.
- NiFi now owns the per-game sequence through separate freshness, RML,
  authoritative-validation, graph-load, index/equivalence, and promotion
  processors. A forced fixture rebuild and an unchanged manual-inbox handoff
  both passed with stage evidence and no raw or ontology mutation.
- Audit-enabled corpus submissions now complete from promotion events rather
  than independent timers. NiFi waits for every submitted graph pair, runs the
  four corpus gates, and emits one fingerprinted completion manifest.

## Next work

### 1. Advance the selective reasoning experiment

- Continue running SHACL on explicit graphs before reasoning. Add post-reasoning
  shapes only for constraints whose semantics remain valid over inferred
  closure.

### 2. Review the Explorer

- Add an official-game-date range control that scopes game graph IRIs before an
  analytical query executes. Provide one-day, seven-day, 30-day, and
  season-to-date presets alongside custom start and end dates; use seven days
  as the initial default and show the resolved date range and game count.
- Treat date scoping as both an interaction and performance feature. Resolve
  the relevant game graphs through a compact game/date index before running the
  substantive query rather than scanning every authoritative game graph.
- Review whether individual Advanced questions need result-level player or role
  filters in addition to the implemented season, game, team-in-game, and venue
  graph scope. Add them only through per-query catalog declarations where the
  intended variable is unambiguous.
- Decide which fixed Advanced result groupings should become selectable without
  changing the claim made by each reviewed query. Empty Games may similarly add
  optional grouping by batting team or game after its current filtered result
  contract is reviewed.
- Keep the implemented shared filter behavior consistent as the interface
  evolves: identical option loading, `All values` behavior, selected-state
  display, reset behavior, generated-SPARQL inspection, result metadata, and
  CSV export.
- Evaluate the Advanced view against real research questions after filter
  parity is implemented.
- Decide how the three generic terminal baserunning outcomes should relate to a
  plate appearance. Keep them explicit until the owner approves the model.
- Continue replacing ontology-facing UI terminology with standard baseball
  language. Where a metric is partial or evidence-bounded, show that limitation
  beside the selector and in result metadata rather than relying on its name
  alone.
- Connect proven query families to the reviewed authoritative/index router,
  while retaining authoritative fallback for unsupported queries. Cache filter
  options and safe repeated results against the corpus fingerprint, and show
  execution time plus the selected `Indexed` or `Authoritative` route in result
  metadata.
- Defer a broad visual redesign until this common query interaction is settled.

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

### 5. Finish repeatable orchestration in NiFi

- Add a parameterized request boundary for explicitly selected reasoning
  anchors and profiles; retain all fixed budgets and the prohibition on
  full-game or corpus closure.
- Exercise the connected per-game flow over the checked-in corpus and retain
  the bundled importer only until broader parity evidence is accepted.
- Reduce PowerShell to Windows bootstrap, local operator entry points, and
  maintenance tasks after equivalent NiFi paths are proven. Do not remove the
  existing scripts until the automated flow has demonstrated parity.

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
