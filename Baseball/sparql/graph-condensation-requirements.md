# Graph condensation and query-acceleration requirements

This document defines the review problem only. It does not select shortcut
properties, change the ontology or RML, materialize a condensed graph, or
change query semantics.

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

The example “player is agent in hit” is deliberately a candidate semantic
shape, not an approved property assertion. Review must determine whether
`agent`, `participant`, or a baseball-specific shortcut is valid, which
individual is its subject, and which direction supports both ontology hygiene
and query use.

## Decisions required before implementation

1. Which candidates justify a shortcut, and which should rely on datastore
   indexes or materialized views instead?
2. What is the exact domain, range, direction, and intended entailment of each
   shortcut property?
3. Which complete triples constitute sufficient evidence, including required
   judgments and decisions?
4. Does the condensed layer live in a separate named graph, an external index,
   generated RDF-star annotations, or another replaceable structure?
5. How are assertion provenance, generator version, source graph, and evidence
   identity recorded?
6. What change detection invalidates a shortcut, and how are partial failures
   prevented from leaving stale assertions?
7. Which TDB2 indexes and Fuseki query shapes should be benchmarked before
   adding ontology-level shortcuts?
8. What is the dehydration package format, and what exact inputs are required
   to rehydrate both the authoritative and condensed layers?
9. What paired full/condensed query suite and fixture results establish
   semantic equivalence?

## Review deliverables

- an approved shortcut-property table or a decision to use datastore-only
  acceleration for each candidate;
- a named-graph/index lifecycle and provenance design;
- a deterministic generation and invalidation specification;
- representative full-pattern and condensed SPARQL pairs;
- equivalence, regeneration, and stale-data tests; and
- measured query plans and timings on representative graph sizes.

