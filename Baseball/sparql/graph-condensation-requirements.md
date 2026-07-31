# Graph condensation and query-acceleration requirements

This document records the original review requirements and the first approved
implementation contract. The implementation does not change the ontology,
RML, raw source, or existing canned-query semantics.

## Implemented first contract

- The condensed layer is a per-game named graph in the same TDB2 dataset:
  `https://w3id.org/baseball/graph/query-index/game/{gamePk}`.
- Shortcut terms use the operational
  `https://w3id.org/baseball/query-index/` namespace and are not declared as
  BaseballO ontology properties.
- Direction is fact/event to relevant person: `?fact idx:agent ?person`.
  The person must be explicitly typed as a CCO Person in every agent-producing
  source pattern.
- Twelve small `CONSTRUCT` components cover provenance, game dimensions,
  completed plate appearances, hits, pitches, pitch calls, batting acts,
  contacts, runner resolutions, stolen bases, game assignments, and labels.
- Every materialized fact points to decisive authoritative evidence with
  `idx:derivedFrom`.
- A complete Graph Store `PUT` replaces the derived graph. A failed build
  removes it rather than leaving a stale projection.
- The build manifest records the component-contract hash, source and index
  graph IRIs, optional local authoritative RDF hash, graph sizes, index hash,
  fact counts, and timestamps.
- Exact full-pattern/index row-set equivalence is executable for ten semantic
  families. See [`query-index/`](query-index/).

## Invariants

- The complete event pattern remains the authoritative graph.
- Every condensed assertion must be derivable from sufficient evidence in the
  complete graph and traceable back to that evidence.
- A condensed layer must be disposable and reproducible. Deleting and
  rebuilding it from the same authoritative graph must produce equivalent
  assertions.
- Dehydration must not discard information required to re-establish the full
  pattern. If full-pattern data is archived separately, its identity,
  provenance, version, and graph membership must remain recoverable.
- Condensed and full-pattern versions of an approved query must return
  equivalent answers under an explicitly documented entailment regime.
- No shortcut may erase the distinctions among source records, intentional
  acts, physical processes, institutional processes, judgments, decisions, or
  calls.

## Candidate recurring patterns for review

| Candidate | Full-pattern evidence that must remain inspectable | Common query pressure |
| --- | --- | --- |
| Player participation in a hit | Batter act, player participation, PA result, specific hit class, hit judgment, PA/game containment | Hits by player, season, venue, game, or type |
| Player participation in a PA result | Batter act, specific result class, generic adjudication, PA/game containment | PA and outcome distributions |
| Pitcher participation in a pitch | Pitch act, player participation, following pitch-ball motion, enclosing PA/game | Pitch totals by pitcher, season, venue |
| Pitch call/outcome | Pitch, shared event record, ball/strike/foul-tip process and its judgment/call evidence | Balls, strikes, pitch summaries |
| Batter participation in contact | Swing or bunt act, contact process, batted-ball motion, player participation | Swings and batted balls |
| Runner participation in a resolution | Runner act/resolution, player participation, run/out/safe judgment | Runner outcomes and runs |
| Stolen-base resolution | Stolen-base process, stolen-base judgment, runner participation | Stolen bases by player |
| Event-to-game and event-to-venue traversal | PA/half-inning/inning/game containment and game/field/site/venue chain | Most season and venue groupings |
| Contextual team or official assignment | Person/team, game-scoped role, realization in game | Team, umpire, scorer filters |

The example "player is agent in hit" is implemented only as the operational
shape `?hit idx:agent ?person`. It is approved for the disposable query index,
not as an ontology assertion. The authoritative graph continues to distinguish
the batter act, person participation, result, judgment, and containment chain.

## Decisions still required before production promotion

1. Which TDB2 indexes and Fuseki query shapes should be benchmarked before
   adding ontology-level shortcuts?
2. What is the dehydration package format, and what exact inputs are required
   to rehydrate both the authoritative and condensed layers?
3. Which of the 48 canned queries and UI components should switch to the
   operational index after multi-game benchmarks?
4. Should any operational term eventually be promoted to an ontology property,
   and if so, what domain/range axioms and name should the project ontologist
   approve?
5. How should old per-game index graphs and manifests be garbage-collected at
   production scale?

## Review deliverables

- an approved list of canned/UI queries to migrate;
- a portable dehydration package manifest;
- failure-injection tests for regeneration and stale-data removal; and
- measured query plans and timings on representative graph sizes.
