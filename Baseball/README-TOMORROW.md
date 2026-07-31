# BaseballO session handoff

The live MLB API remains disabled; continue using the checked-in completed-game
fixture until data acquisition is explicitly reopened.

## Status after the 2026-07-31 query audit

- All 48 canned SPARQL files were reviewed against the granular RML patterns.
- Both allowlisted UI query builders were synchronized and representative
  maximal queries executed successfully in loopback Fuseki.
- [`sparql/query-inventory.md`](sparql/query-inventory.md) records the counted
  entity, evidence joins, dimensions, and status of every query.
- [`sparql/query-index/`](sparql/query-index/) now contains 12 reviewable
  `CONSTRUCT` components for a separate, disposable per-game shortcut graph.
- The corrected offline fixture materialized to 29,736 triples, and all 48 canned queries
  executed without a SPARQL error. The Empty Games prototype still returned six
  candidates.
- The two RML-processor coverage problems are corrected by a disposable,
  hashed execution-context copy. All 282 pitches now have plate-appearance,
  pitcher-person, and pitcher-role links; all 134 swing/bunt acts and all 112
  contacts have complete ancestor context; and the graph has one terminal game
  timestamp.

The first dehydrated query-index contract is implemented. For fixture game
566279 it contains 6,981 triples versus 29,736 authoritative triples and passes
exact full-pattern/index row equivalence for ten semantic families. The next
priority is multi-game benchmarking followed by a reviewed decision about
which canned and UI-compiled queries should use the index.

## Completed first priority: update all SPARQL

Review and update all 48 `.rq` files under [`sparql/`](sparql/) against the revised RML—not just the hit queries. Work through every family:

1. Root hit queries: 7
2. Batting queries: 9
3. Pitching queries: 7
4. Baserunning queries: 6
5. Game queries: 7
6. UI option queries: 12

The query audit needs to account for these current mapping decisions:

- SwingAct and BuntAct are acts distinct from BatBallContactProcess and BattedBallMotionProcess.
- PitchAct precedes PitchBallMotionProcess.
- Institutional results have explicit judgment acts and decision ICEs.
- Called and swinging strikes are different patterns; only a called strike has a call act.
- A foul tip is one individual typed as both FoulTipProcess and StrikeProcess.
- Plate-appearance results use one result individual with the most specific supported class plus BaseballInstitutionalProcess.
- Player and official roles are scoped to a game.
- Participation uses `obo:BFO_0000057` rather than the removed `cco:ont00001833` agent relation.
- Runner acts use the neutral `/runner-act/movement/` identity path; outcomes belong to the resulting processes and adjudications.
- Venue/location queries should follow the mapped field/site relationships rather than infer location from an IRI.
- Event records, acts, physical processes, institutional processes, judgments, decisions, and calls are separate individuals.

For each query, decide whether it should count source records, acts, physical processes, institutional results, or distinct games. Do not let one JSON event generate accidental double-counting through its multiple RDF individuals.

## Completed: synchronize UI query components

Both compilers under [`web/query-builder/`](web/query-builder/) now use the revised full patterns:

- `analytics-query-builder.js` is the primary component catalog.
- `hit-query-builder.js` is the narrower compatibility layer.
- Every select-box dimension or filter should have a corresponding allowlisted options query.
- User selections should compose reviewed query fragments; never accept arbitrary SPARQL text.
- Add useful combinations beyond the current examples, including season totals, player totals, venue totals, player-by-venue, result types, pitch outcomes, runner outcomes, umpires, and official scorers.

## Implemented: graph condensation and query acceleration

The complete ontological event pattern remains available. A separate named
graph now materializes operational shortcut facts for common traversals. The
shortcut namespace is not part of the ontology, and every fact retains
`derivedFrom` links to decisive authoritative evidence.

Use hits as an initial example: when the complete hit pattern is satisfied, investigate how a condensed assertion could directly express that the relevant player is the agent in that hit. Apply the same analysis to other recurring baseball patterns.

The remaining review and benchmark tasks are:

- benchmark full and indexed shapes over multiple games and inspect TDB2 plans;
- decide which canned and UI-compiled queries should switch to the index;
- define a portable dehydration-package manifest for archive/rehydration;
- add failure-injection and stale-index tests; and
- decide whether any operational shortcut ever merits ontology promotion.

Do not promote the operational shortcut vocabulary into the ontology without
the project owner's explicit ontological review.

## Completed work order

1. Create an inventory table for all 48 queries with columns for query family, counted entity, required joins, filters, and update status.
2. Document the graph-condensation requirements and candidate recurring patterns without implementing them yet.
3. Update shared graph patterns first so the query families use the same interpretation of games, plate appearances, roles, venues, and results.
4. Update the canned `.rq` files family by family.
5. Update the option queries and JavaScript component catalogs.
6. Search for legacy paths, predicates, and identity assumptions.
7. Update the SPARQL and query-builder READMEs so their examples match the final queries.
8. Parse all queries and run the repository validator.
9. Materialize the local fixture and verify query results after the full rewrite; do not enable external acquisition to do this.

## RML items still needing review

Do not silently solve these in SPARQL. They are recorded modeling or source limitations that may require an ontology decision:

- An event-local foul count of two is ambiguous, so the mapping only asserts a separately counted foul strike where the source supports it conservatively.
- Batted-ball coordinates can identify a coordinate ICE and designated site, but approved scalar coordinate datatype properties are still missing.
- The source does not identify the responsible official for every fair/foul, safe/out, or run judgment.
- Runner records are not reliably linked to their enclosing plate appearance by the selected RML processor.
- The final play timestamp is used as the game terminal time, but a walk-off ending need not be a final out.

The project owner is the ontologist. Report any required ontology additions or corrections before modifying [`ontology/`](ontology/).

## Starting checks

From the repository root:

```powershell
git status --short
git branch --show-current
python Baseball/scripts/validate_repository.py
```

The expected starting branch is `dev`, and the repository should be clean. The
current mapping inventory is 247 triples maps, 56 logical sources, and no
referencing-object joins. The local fixture most recently generated 29,736
triples with complete context on 282 pitches, 134 swing/bunt acts, and 112
bat-ball contacts, plus adjudication on all 79 plate-appearance results.
