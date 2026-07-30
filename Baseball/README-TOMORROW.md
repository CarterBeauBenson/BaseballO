# Tomorrow's BaseballO Handoff

Resume from commit `4ae4ffc` on the `dev` branch. The direct RML now models the granular event chains discussed today, and the Mermaid pattern catalog reflects those implemented patterns. The live MLB API remains disabled; continue using the checked-in completed-game fixture until data acquisition is explicitly reopened.

## First priority: update all SPARQL

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

## Keep the UI query components synchronized

After the canned queries are updated, revise both compilers under [`web/query-builder/`](web/query-builder/):

- `analytics-query-builder.js` is the primary component catalog.
- `hit-query-builder.js` is the narrower compatibility layer.
- Every select-box dimension or filter should have a corresponding allowlisted options query.
- User selections should compose reviewed query fragments; never accept arbitrary SPARQL text.
- Add useful combinations beyond the current examples, including season totals, player totals, venue totals, player-by-venue, result types, pitch outcomes, runner outcomes, umpires, and official scorers.

## Second priority: graph condensation and query acceleration

Determine the best indexing and shortcut-property strategy for dehydrating and rehydrating the graph as needed. The complete ontological event pattern must remain available, but a derived condensed layer should make common queries substantially faster and simpler.

Use hits as an initial example: when the complete hit pattern is satisfied, investigate how a condensed assertion could directly express that the relevant player is the agent in that hit. Apply the same analysis to other recurring baseball patterns.

This is an open design task for the next session, not a decision recorded today. Evaluate:

- which full patterns warrant condensed assertions;
- which shortcut properties are ontologically valid and what their directions should be;
- what constitutes sufficient evidence for generating each shortcut;
- whether shortcuts belong in a separate named graph or another indexing layer;
- how condensed assertions are generated, invalidated, and regenerated without drifting from the full graph;
- what must be retained so the graph can be reliably dehydrated and rehydrated;
- how canned and UI-compiled queries can use the shortcut layer while remaining traceable to the complete pattern; and
- how to verify that condensed queries and full-pattern queries return equivalent answers.

Do not modify the ontology, RML, or query semantics for this optimization until the design has been reviewed with the project owner.

## Suggested work order

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

The expected starting branch is `dev`, and the repository should be clean. The current mapping inventory is 249 triples maps, 56 logical sources, and 57 joins. The local fixture most recently generated 27,163 triples with 282 pitch motions, 112 bat-ball contacts, and adjudication on all 79 plate-appearance results.
