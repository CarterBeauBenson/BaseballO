# Person, act, location, and outcome patterns

This catalog decomposes the active direct RML into one diagram for every
materially different human-act pattern. It is intentionally more granular than
the family summaries in the parent [`mermaid/`](../README.md) directory.

Every solid RDF-relation arrow is directed exactly as the emitted triple:
subject to object. Source-to-map and map-to-individual arrows show
transformation flow rather than instance triples. Dashed arrows are inferred
inverses, missing links, identity equivalences, or possible future corrections
and are labeled accordingly. The diagrams describe and evaluate the mapping;
they do not change the RML or ontology.

## Reading order

1. [`00-relation-directions.md`](00-relation-directions.md) — exact BFO/CCO arrow directions.
2. [`00a-location-construction.md`](00a-location-construction.md) — the shared root-marker and IRI-equality location pattern.
3. [`01-batter-act.md`](01-batter-act.md) — one overall batter act per plate appearance.
4. [`02-pitch-act.md`](02-pitch-act.md) — one pitcher act per source pitch.
5. [`03-called-ball.md`](03-called-ball.md) — ball and ball-in-dirt classification pattern.
6. [`04-called-strike.md`](04-called-strike.md) — called strike without a swing.
7. [`05-swinging-strike.md`](05-swinging-strike.md) — unsuccessful contact attempt.
8. [`06-foul-swing.md`](06-foul-swing.md) — swing, contact, foul, and strike branches.
9. [`07-foul-tip-swing.md`](07-foul-tip-swing.md) — materially distinct foul-tip classification.
10. [`08-in-play-swing.md`](08-in-play-swing.md) — one generic structure shared by X, D, and E call codes.
11. [`09-runner-out.md`](09-runner-out.md) — unsuccessful baserunning resolution.
12. [`10-runner-score-origin.md`](10-runner-score-origin.md) — scoring without a recorded starting base.
13. [`11-runner-score-from-base.md`](11-runner-score-from-base.md) — scoring from first, second, or third.
14. [`12-runner-reach.md`](12-runner-reach.md) — safe reach from an origin state.
15. [`13-runner-advance.md`](13-runner-advance.md) — safe advancement from a recorded base.
16. [`14-plate-appearance-result.md`](14-plate-appearance-result.md) — generic result plus specific outcome typing.
17. [`15-shared-event-record.md`](15-shared-event-record.md) — one source record about several distinct entities.
18. [`16-unmapped-human-acts.md`](16-unmapped-human-acts.md) — fielding, bunting, and adjudication gaps.
19. [`17-correction-candidates.md`](17-correction-candidates.md) — consolidated findings and safe correction boundaries.

## Important interpretation

“Success” and “failure” are review language, not ontology classes. The desired
pattern keeps an intentional act neutral and represents its institutional
outcome as a separate process. Batter, pitch, and swing identities largely do
this. Baserunning uses the neutral `BaserunningAct` class but embeds `out`,
`score`, `reach`, or `advance` in the act IRI, so its identity is not fully
outcome-neutral.

## Act-map coverage

| Act class | RML act maps | Diagram treatment |
| --- | ---: | --- |
| `BatterAct` | 1 | One discrete batter-act pattern |
| `PitchAct` | 1 | One neutral pitch-act pattern plus materially different call outcomes |
| `SwingAct` | 6 | Swinging strike, foul, and foul tip are separate; X/D/E share one exactly repeated in-play pattern |
| `BaserunningAct` | 5 | Out, score-origin, score-from-base, reach, and advance are separate because their source partitions, identities, and resolutions differ |
| **Total** | **13** | Every act-producing TriplesMap in `mlb-direct.rml.ttl` is represented |
