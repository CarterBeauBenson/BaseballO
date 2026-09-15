# What still prevents operational player metrics

Engineering audit, September 14, 2026. **The requested dashboard is incomplete.**
This draft does not record a new ontologist decision or authorize vocabulary.

The top-five display and qualification code exist. The backend does not yet
produce their `playerResults` input. In `serving/metric_suite.py`, `live_result`
returns unavailable whenever the catalog entry has prerequisites; it does not
evaluate a complete source-to-player scoring adapter for those entries. Formula
implementations and browser fixtures are not evidence of operational metrics.

## Settled decisions remain settled

The [accepted E1/C1 decision](../../archive/design-records/metric-source-c1-operation-2026-09-14/review.json)
already permits the reviewed source authority and personal-history mapping.
The [C1/C2 decision](../../archive/design-records/runner-continuity-boundary-projection/review.json)
already accepts the personal Process and analytical boundary projection.
Neither needs another approval. The batting qualification rule is also
[accepted](../../archive/design-records/metric-leaderboard-qualification-2026-09-14/user-decision.md):
3.1 PA per applicable team game, rounded to the nearest whole PA.

Error/FC progress remains excluded; independent running belongs to the runner;
erosion uses the actual end state. Percentiles retain the complete accepted
season reference before applying display filters or player qualification.
No new object properties are permitted.

## Concrete remaining work

| Metric | Current live calculation | Required input/implementation still missing |
| --- | --- | --- |
| TFS | Bounded loaded Walk/HBP consequences | Complete consequences, immediate boundaries, operative attributed outs, and player aggregation |
| PAQ-2 | None | Complete TFS population through the season cutoff and player aggregates |
| PAQ-A | None | PAQ population plus immediate pre-consequence base/out cohorts |
| Offensive Reach | Bounded loaded Walk/HBP consequences | Complete positively attributed trajectories and player aggregation |
| Hidden Help Rate | None | Complete PA contribution numerators and eligible denominators |
| Rally Kill Rate | None | Supported attributed existing-runner outs and all eligible PAs |
| Rally Kill Severity | None | Existing-runner destruction over all eligible PAs |
| Opportunity Erosion | None | Complete operative boundary states and PA erosion |
| Empty Game Rate | None | Official PA eligibility and complete batting/independent-running contributions |
| Empty Game Damage | None | Complete Empty Game classification and all accepted damage components |
| Contribution Path Diversity | None | Complete positive play/channel inventory with one count per channel |
| Recovery Quality | None | Supported ordered post-pitch counts, termination, and complete reference population |
| Defensive Resolution Depth | None | Complete intentional defensive acts and supported precedence |
| Defender Breadth | None | Complete defensive agents in the resolution |
| Run Construction Depth | Complete individual admitted scoring histories | Coverage of the selected run population and a player aggregation rule |
| Run Construction Breadth | None | Complete histories and supported causal contributions, including the scorer |
| Adjudication Volatility | Explicitly resolved mapped reviews | Player attribution if this is to become a player leaderboard |
| Review Dependence Rate | None | All eligible decisions, mechanism-specific eligibility, operative review links, and player attribution |
| Role Realization Breadth | None | Complete actual realization of the four accepted role kinds |
| PAQ-2.1 | None | Complete TFS, recovery and defensive inputs, applicability, and reference population |

Independent runner advancement, damage, and net also require their complete
episode and affected-runner evidence. None of the available bounded results
establishes complete player participation or qualifies a player for ranking.

## Engineering versus evidence and modeling gaps

1. **Engineering:** finish the accepted source proof, corpus refresh, C2
   adapter where its evidence is supported, consequence adapters, population
   reconciliation, exact player aggregation, and serving integration. The
   source proof for game 566279 passed SHACL with 31,717 triples and promoted,
   but failed materialization on the subsequently repaired DSQ catalog issue.
   The replacement SQL build was active at this audit. Its completion does not
   create missing score adapters or complete the failed proof's stage records.
   Recovery belongs in NiFi; competing promotion during its snapshot build
   would invalidate the build. See [the operational record](../../infra/PRODUCTION-READINESS.md).
2. **Source evidence:** the inspected MLB feed's fielding credits do not
   enumerate a complete intentional field/throw/catch/tag sequence. A census
   of reviewed plays does not enumerate eligible never-reviewed decisions.
   E1 explicitly did not admit those additional contracts. This limitation
   is documented in [the accepted package's E2 discussion](../../archive/design-records/metric-source-c1-operation-2026-09-14/source-admission.md).
   Another SQL rebuild cannot resolve it.
3. **Modeling/evidence:** official statistical PA attribution is distinct from
   the player who finishes a substituted turn. Counting mapped Batter Acts
   cannot silently stand in for official PA totals. Qualification additionally
   needs the player's applicable team-game exposure, including missed games
   and team changes; counting only appearances would lower the minimum.
4. **Player presentation meaning:** a score for a run, defensive play, or review
   is not automatically a score for every participant. The assignment and
   aggregation rule must be explicit before those cards can rank players.

## Outstanding player-presentation decisions

These are concrete candidates, not accepted policy:

- **Runs:** assign a run's construction score to its scoring runner and display
  that player's mean across their fully supported runs in the selected range.
  This describes the construction of their runs; it does not credit the runner
  with every teammate's contribution.
- **Defensive plays:** display each participating defender's mean play depth
  or breadth over fully supported defensive resolutions in which they acted.
  This describes their participated-in plays, not individual defensive skill.
  Do not assign a play to a rostered fielder without actual agency evidence.
- **Reviews:** either retain the accepted review-level panels, or define player
  populations around the batter/runner whose particular outcome is affected.
  The latter requires an explicit outcome-to-player evidence path. Review
  Dependence must still include that player's eligible never-reviewed decisions
  in its denominator, and retain separate review mechanisms.
- **Participation:** the role-appropriate approach is accepted. Numerical
  non-batting thresholds and their exposure denominators remain unspecified;
  record them before ranking. Never substitute a PA minimum for a pitcher.

Acceptance of one candidate does not establish the required source evidence
or authorize a new predicate. The full deliverable is reached only when real
qualified player rows pass source admission, calculation, SQL equivalence and
the live HTTP/browser path. The current seven-player browser fixture proves
presentation only. This audit records the unfinished work; it does not close it.
