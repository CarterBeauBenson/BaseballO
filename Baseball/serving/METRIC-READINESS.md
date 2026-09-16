# Nineteen public metrics: implementation and release status

Fourteen public player producers are implemented conditionally. Five remain
unfinished. This is not a claim that fourteen live leaderboards are populated:
each requires complete source/graph, period, eligibility and qualification
admission. All twenty calculation kernels exist; Role Realization Breadth is
the backend-only twentieth metric and is not another public card.

| Public metric | Player producer | Remaining work before complete live results |
| --- | --- | --- |
| Plate Appearance Contribution | Implemented conditionally | Complete attributed PA inputs and selected schedules; supported independent prefixes stay separate |
| Plate Appearance Quality | Implemented conditionally | Every reference-season contribution input and independent schedule through cutoff |
| Situation-Adjusted PAQ | Implemented conditionally | Same complete season, admitted immediate base/out states and at least two reference observations per applicable state |
| Offensive Reach | Implemented conditionally | Complete selected schedules, B1, runner census, supported attribution and contact continuations |
| Help Without Advancing | Implemented conditionally | Same complete progress population; pooled applicable PA denominator |
| Runner Out Rate | Implemented conditionally | Complete runner-on-base eligibility and attributed existing-runner outs; independent changes cannot be charged to the batter |
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

[The corrected real-game proof](../benchmarks/metrics/contribution-mixed-plays-2026-09-15/result.json)
passes source SHACL, canonical Jena extraction and exact SQL retention for
game 566279: **79 of 79 contribution scores resolve**. Its 31 personal histories
and all PA-start boundaries reconcile. The isolated one-game player summaries
for Contribution, Runner Out Rate, Runner Loss and Opportunity Lost match SQL.
No season or public date-range schedule is fabricated by this developer proof.

The three formerly withheld scores are now retained: PA 12 (balk then walk)
= 1/4 for the batter; PA 23 (steal then single) = 5/4 for the batter with the
steal kept separate and the contact beginning at second; PA 40 (fielder's
choice plus error) = 0 under the accepted positive-credit exclusion.
The award proof independently checks all expected causal/normative award
members before absence of an award link can exclude another movement.

PAQ can consume the complete contribution inputs once its season is admitted.
PAQ-A separately requires a supported immediate comparison state: 77 of the
79 have one. PAs 12 and 40 still lack sufficient graph ordering for that state;
this is not a reason to suppress their known contribution values. The existing
balk record is descriptive; the adapter does not convert its text into a new
causal assertion. Independent damage/positive-running classification is also
kept separate, so complete batting inputs do not falsely certify Empty Games.

The five remaining producers require defensive/review evidence adaptation;
these new conditional producers do not finish those pipelines.
