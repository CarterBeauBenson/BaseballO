# Nineteen public metrics: implementation and release status

Seven public player producers are implemented conditionally. Twelve remain
unfinished. This is not a claim that seven live leaderboards are populated:
each requires complete source/graph, period, eligibility and qualification
admission. All twenty calculation kernels exist; Role Realization Breadth is
the backend-only twentieth metric and is not another public card.

| Public metric | Player producer | Remaining work before complete live results |
| --- | --- | --- |
| Plate Appearance Contribution | Unfinished | Complete attributed outcomes, immediate runner/out boundaries, actual end states and stranded histories |
| Plate Appearance Quality | Unfinished | Complete contribution scores and season reference |
| Situation-Adjusted PAQ | Unfinished | Contribution scores, immediate pre-consequence base/out state and complete state-specific season references |
| Offensive Reach | Implemented conditionally | Complete selected schedules, B1, runner census, supported attribution and contact continuations |
| Help Without Advancing | Implemented conditionally | Same complete progress population; pooled applicable PA denominator |
| Runner Out Rate | Unfinished | Complete runner-on-base eligibility and attributed existing-runner outs |
| Runner Loss per PA | Unfinished | Same complete eligibility plus direct-loss weights and outcome ownership |
| Scoring Opportunity Lost | Unfinished | Supported immediate and actual ending states, attributed outs and stranded-runner coverage |
| Empty Games | Implemented conditionally | Complete official PAs and positive batting/running channels; retained game count |
| Empty Game Damage | Unfinished | Complete Empty Game classification, negative PA contributions and independent-running damage |
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

The unchanged source ownership check rejects the current catalog because five
metric SHACL profiles are unregistered, four of which predate Recovery. The
[prepared ownership repair](../proposals/mlb-game-metric-profile-registration/README.md)
passes the validator in isolation. Applying its protected catalog pin requires
the named user decision. No global ratification is proposed.

M3/M4 remains a separate draft for four counted-foul cases. A further known
Q5 case in game 824087 PA 32 is withheld because the PA contains a review;
the automatic strike is present in the source. Source evidence presence,
mapping coverage, calculation implementation and live population admission
are separate states. The remaining twelve producers must not be described as
finished or as blocked solely by absent provider evidence.

NiFi owns repeatable processing, correction invalidation, promotion and serving
refresh. No routine corpus acquisition, manual rebuild or healthy-run polling
was performed for this change. Its source schedule remains unchanged.
