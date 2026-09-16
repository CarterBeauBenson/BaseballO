# Nineteen public metrics: implementation and release status

Fourteen public player producers are implemented conditionally. Five remain
unfinished. This is not a claim that fourteen live leaderboards are populated:
each requires complete source/graph, period, eligibility and qualification
admission. All twenty calculation kernels exist; Role Realization Breadth is
the backend-only twentieth metric and is not another public card.

| Public metric | Player producer | Remaining work before complete live results |
| --- | --- | --- |
| Plate Appearance Contribution | Implemented conditionally | Complete single-consequence PA inputs, selected schedules; mixed independent/contact attribution remains withheld |
| Plate Appearance Quality | Implemented conditionally | Every reference-season contribution input and independent schedule through cutoff |
| Situation-Adjusted PAQ | Implemented conditionally | Same complete season, admitted immediate base/out states and at least two reference observations per applicable state |
| Offensive Reach | Implemented conditionally | Complete selected schedules, B1, runner census, supported attribution and contact continuations |
| Help Without Advancing | Implemented conditionally | Same complete progress population; pooled applicable PA denominator |
| Runner Out Rate | Implemented conditionally | Complete runner-on-base eligibility and attributed existing-runner outs; mixed consequences remain withheld |
| Runner Loss per PA | Implemented conditionally | Same complete eligibility and outcome ownership; exact direct-loss weights retained |
| Scoring Opportunity Lost | Implemented conditionally | Complete admitted PA boundaries and attributed outs; actual ends and third-out stranding retained |
| Empty Games | Implemented conditionally | Complete official PAs and positive batting/running channels; retained game count |
| Empty Game Damage | Implemented conditionally | Complete Empty Game classification and negative PA contributions; this adapter admits only games with no separate independent damaging episodes or interrupted turns |
| Contribution Mix | Implemented conditionally | Complete positive play/channel inventory and separate running-attempt qualification |
| Two-Strike Extension Rank | Implemented conditionally | Complete pitch/count and B1 admissions for every reference-season game, plus independent schedules through the cutoff |
| Longest Defensive Sequence | Unfinished | Reconciled distinct intentional defensive performances, agents, supported order and complete participation |
| Defenders Involved | Unfinished | Complete supported defensive act/agent population and participation |
| Scoring History Length | Implemented conditionally | Every counted scoring history, source run/roster proof and selected schedule |
| Run Contributors | Implemented conditionally | Same complete scoring histories with supported contribution ownership |
| Replay Overturn Rate | Unfinished as a player producer | Existing review-population calculation is available; affected-player assignment, mechanism and complete player qualification remain |
| Outcomes Changed by Review | Unfinished | Complete eligible never-reviewed decisions, decision-time legal availability, operative outcomes, affected players and separate mechanisms |
| PAQ with Tie-Breakers | Unfinished | Contribution, two-strike and defensive dimensions with known applicability and a complete separate season reference |

The settled meanings, minima, averages, Empty Game count, separate review
mechanisms and backend-only role handling remain unchanged. No object
properties or ontology terms were introduced.

The new Recovery producer is proven from a complete real-game input set
(79 PAs, 282 pitches) through exact SQL retention. Complete-season ranking
and selected-range means have focused integration tests. The common percentile
engine also passes exact equivalence checks for all four rank metrics and a
20,200-observation scale case without a quadratic peer join.

## Concrete release gates

The six metric SHACL profiles are registered in the owning module's
operational `pipeline/validation-profiles.json`. Exact ownership and inventory
checks cover both that registry and the existing pinned source contract.
The registration blocker is resolved without a protected catalog or freeze
change. The [unnecessary approval request was withdrawn](../archive/design-records/mlb-game-metric-profile-registration/disposition.md).

M3/M4 remains a separate draft for four counted-foul cases. A further known
Q5 case in game 824087 PA 32 is withheld because the PA contains a review;
the automatic strike is present in the source. Source evidence presence,
mapping coverage, calculation implementation and live population admission
are separate states. The remaining five producers must not be described as
finished or as blocked solely by absent provider evidence.

NiFi owns repeatable processing, correction invalidation, promotion and serving
refresh. No routine corpus acquisition, manual rebuild or healthy-run polling
was performed for this change. Its source schedule remains unchanged.

## Contribution and season-ranking implementation

The source-owned boundary proof checks the exact existing PA-start stases,
out counts and independently reconciled C1 history membership. Serving can
therefore preserve an unchanged runner through the PA and strand that runner
at the third out without manufacturing an Out Process. No RML, ontology,
object property, semantic freeze or approval status changed.

[The real-game proof](../benchmarks/metrics/contribution-inputs-2026-09-15/result.json)
passes source SHACL, canonical Jena extraction and exact SQL retention for
game 566279: all 79 PA-start boundaries and 31 personal histories reconcile;
76 PA contribution inputs are supported and three are withheld. They are:
PA 12 (balk then walk), PA 23 (steal then single), and PA 40 (an error during a
fielder's choice). The source contains these events. Their remaining work is
separate-channel/boundary adaptation; this incomplete game cannot supply a
contribution leaderboard or season reference.

PAQ and PAQ-A use the same complete-season scheduler checks as Recovery,
rank before selecting display dates, and retain exact player means. PAQ-A
uses immediate base/out cohorts only for admitted single-consequence PAs.
Empty Game Damage averages complete Empty Games, never inserts zero for a
non-Empty Game, and withholds games whose independent damage is unresolved.
The five remaining producers require defensive/review evidence adaptation;
these new conditional producers do not finish those pipelines.
