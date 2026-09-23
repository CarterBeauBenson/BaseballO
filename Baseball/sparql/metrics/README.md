# Graph-native metric queries and policies

This directory owns the analytical evidence queries, metric catalog and
accepted calculation policies. The suite has 20 calculation kernels: 19 public
metrics and backend-only Role Realization Breadth. Implemented arithmetic does
not establish complete qualified-player populations. Use
[metric readiness](../../serving/METRIC-READINESS.md) for current availability
and the [roadmap](../../ROADMAP.md) for the ordered work queue.

The [original production roadmap](../../archive/operational-history/2026-09-23/METRIC-QUERY-ROADMAP.md)
is preserved as history. Its unchecked implementation tasks, early award-only
limits and historical source-refresh instructions are superseded.

## Ownership and execution

```text
existing promoted RDF
-> source-scoped SPARQL evidence
-> accepted calculations and population preparation in NiFi
-> immutable SQL products
-> selected-period dashboard reads
```

The authoritative graph is the source of baseball facts. Metric kernels consume
admitted SPARQL bindings, not raw MLB JSON. NiFi prepares game products, names
and season reference ranks; SQL serves the UI with lightweight date filtering
and pooled aggregation. Dashboard requests must not start SPARQL, source
acquisition, RML execution or a season-wide calculation.

| Contract | Purpose |
| --- | --- |
| [Metric catalog](metric-catalog.json) | Stable metric IDs, canonical calculation queries and declared requirements |
| [Gap register](gap-register.json) | Shared availability requirements; current affected populations belong in metric readiness |
| [Source-scope catalog](../source-scope-catalog.json) | Explicit source dependencies and derived-query registration |
| [Calculation contract](../../serving/METRIC-SUITE.md) | Exact definitions, inputs and calculation behavior |
| [Implementation guide](../../serving/METRIC-SUITE-IMPLEMENTATION.md) | Evidence consumers, game products, reference preparation and SQL ownership |
| [Player leaderboards](../../serving/PLAYER-LEADERBOARDS.md) | Accepted qualification and selected-period aggregation |
| [Presentation](../../web/METRIC-NAMING-REVIEW.md) | Public names and explanations, separate from stable calculation IDs |

PAQ-1.0 remains a separately versioned legacy metric. Do not relabel its scores
as PAQ-2. The public dashboard defaults to selected-period averages, except
Empty Games as a count, and applies the accepted automatic participation minima.

## Accepted policies

- [PAQ-2 defaults](paq-2-release-defaults.json): 0-100 percentile display,
  eligible MLB regular-season PAs from the selected season, exact fractions
  internally and rounding only for display.
- [Inning-ending erosion](tfs-inning-ending-policy.json): charge evidenced
  stranded-runner opportunity without inventing another out.
- [Error/FC exclusion](contact-progress-policy.json): exclude that safe progress
  from TFS and Empty Game qualification while preserving actual safe states,
  attributed outs and erosion.
- [Trajectory origins](trajectory-origin-policy.json): use supported movement
  origins; the PA batter's metric origin is HOME=0. Existing-runner PA-start
  fallback requires positive support and no intervening movement.
- [Continuous-path terminal outs](continuous-path-terminal-out-policy.json):
  an admitted path ending out retains no intermediate progress; destruction
  uses its original start.
- [Shared-play erosion](shared-play-erosion-policy.json): use supported actual
  end state as erosion context without crediting independent progress.

These links record accepted choices. A documentation cleanup does not expand
their semantic scope or authorize a new RDF assertion.

## Evidence queries

| Query | Evidence exposed |
| --- | --- |
| [runner-location-evidence.rq](runner-location-evidence.rq) | Explicit PA-start stasis, location links and temporal anchors; missing times remain missing |
| [runner-movement-evidence.rq](runner-movement-evidence.rq) | Individual act/resolution pairs, runner identity, base codes, origins, contact-play and award paths |
| [attribution-evidence.rq](attribution-evidence.rq) | Explicit runner, resolution, destination, origin, contact-play and award coverage |
| [pitch-count-evidence.rq](pitch-count-evidence.rq) | Mapped count evidence for supported count-dependent calculations |
| [suite-evidence.rq](suite-evidence.rq) | Shared graph evidence consumed by the suite |

Evidence row counts are not completeness claims or zero-valued contributions.
Missing state is unknown; adjacent rows alone do not establish continuity.
Independent steals, passed balls and similar running events do not earn batter
progress credit. A selectively covered set of PAs cannot replace the complete
accepted season or contextual reference population.

The owning source profiles determine source/graph conformance. Analytical
queries project the accepted graph contract and retain traceable evidence.
Do not reproduce source semantics in a parallel imperative validator.

## Continuing work

Read the published SQL results and the owning stage's terminal evidence first.
Fix a query, calculation, SQL product or reader in its own layer and let NiFi
refresh the affected derived product. A stale fingerprint alone does not require
regenerating RDF. The [Q7 history repair](../../sources/mlb-game/pipeline/TARGETED-HISTORY-ADDITION.md)
demonstrates the separately approved targeted-addition path; it is not a
standing instruction to replace games or reacquire the corpus.

Follow the [minimal-check policy](../../../AGENTS.md#incremental-work-and-minimal-manual-validation):
one useful focused developer check for changed behavior, with recurring and
aggregate execution owned by NiFi. Existing-term analytical SPARQL needs no new
ontology proposal. New semantics or RML assertions still require the user's
named decision; new object properties are prohibited.
