# What still prevents operational player metrics

Engineering audit, September 14, 2026. **The requested dashboard is incomplete.**
This draft does not record a new ontologist decision or authorize vocabulary.

**September 15 correction:** the [fresh source-availability audit](source-availability-correction-2026-09-15.md)
retracts the blanket missing-source explanation. Official PA totals, event
counts/times, runner observations, defensive sequences and review details are
present in the inspected MLB payload. Incomplete mappings, adapters and
coverage verification must be distinguished from genuinely absent evidence.
Full intentional-act and review-eligibility sufficiency remains unverified,
not proven universally unavailable.

Follow-up: the user directed web research rather than repeating the questions
below. The [source investigation](defensive-source-research-2026-09-14.md)
identifies accessible historical defensive sequences, throwing/receiving
products, official ABS eligibility, and specific access/coverage limits.
The September 15 [player-presentation decision](../../archive/design-records/player-metric-presentation-2026-09-15/user-decision.md)
now accepts PA-score means, means of individual PA percentiles, scoring-runner
construction means, participating-defender means, and affected-player review
attribution. Role breadth remains backend-only. Those choices need no further
vote; source evidence, aggregation implementation, and non-batting numerical
minimums remain work to complete.

The top-five display and qualification code exist. The backend does not yet
produce their `playerResults` input. In `serving/metric_suite.py`, `live_result`
returns unavailable whenever the catalog entry has prerequisites; it does not
evaluate a complete source-to-player scoring adapter for those entries. Formula
implementations and browser fixtures are not evidence of operational metrics.

**September 15 batting follow-up:** the exact PA-mean reducer now exists,
but the live adapters still cannot supply its independently complete inputs.
The [batting participation proof](../../benchmarks/metrics/batting-participation-2026-09-15/README.md)
extracts 77 observations for 20 players through Jena and SQL, all matching
the inspected game's player boxscore totals. Another checked-in game provides
a concrete counterexample: Harry Ford has five matchup records and four
official PAs; the extra record ends on another runner's inning-ending caught
stealing. `about.isComplete` and a mapped Batter Act do not identify official
credit. The [reducer contract](../../web/PLAYER-SUMMARIES.md#backend-pa-mean-reducer-and-participation-inventory)
separates score membership, official PA qualification and team-game exposure.

The next semantic gate is the accepted representation and identity of official
statistical PA credit, including interrupted turns and substituted batters.
The user has already decided that official credit and actual contribution are
separate; that policy is not being reopened. A source-total literal attached
to a Person or a label on a new ICE would not express the missing relationship.
Applicable team-game exposure additionally needs its supported historical
membership scope. These are not licensed by M1/M2 acceptance, and no new
ontology term, object property, RML or source SHACL is introduced here.

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

The [C2 implementation and real-game proof](../../benchmarks/metrics/c2-boundaries-2026-09-14/README.md)
now supply unchanged runner states for intervening PAs strictly bracketed by
episodes in complete C1 histories. This closes that bounded adapter case.
Within-PA episode order, unbounded stranding, full affected-runner census,
official PA attribution and complete player scores remain separate requirements.
The proof's three states are retained through SQL and shown in UI coverage;
they are not three complete PA scores or qualified player rows.

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
| Run Construction Depth | Complete individual admitted scoring histories | Coverage of the selected run population and implementation of the accepted scoring-runner mean |
| Run Construction Breadth | None | Complete histories and supported causal contributions, including the scorer |
| Adjudication Volatility | Explicitly resolved mapped reviews | Supported links to the affected batter/runner and implementation of accepted player attribution |
| Review Dependence Rate | None | All eligible decisions, mechanism-specific eligibility, operative review links, and player attribution |
| Role Realization Breadth (backend only) | None | Complete actual realization of the four accepted role kinds; no public card |
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
4. **Player presentation implementation:** the September 15 decision now
   specifies assignment and aggregation. The corresponding input evidence
   must still be complete before those cards can rank players.

## Disposition of earlier player-presentation candidates

The September 15 decision accepts the run and defensive means below and selects
affected-player review statistics. Retaining review-only public panels is not
the selected direction. Numerical non-batting minimums remain unresolved.

- **Runs:** assign a run's construction score to its scoring runner and display
  that player's mean across their fully supported runs in the selected range.
  This describes the construction of their runs; it does not credit the runner
  with every teammate's contribution.
- **Defensive plays:** display each participating defender's mean play depth
  or breadth over fully supported defensive resolutions in which they acted.
  This describes their participated-in plays, not individual defensive skill.
  Do not assign a play to a rostered fielder without actual agency evidence.
- **Reviews:** use player populations around the batter/runner whose particular
  outcome is affected. This requires an explicit outcome-to-player evidence path. Review
  Dependence must still include that player's eligible never-reviewed decisions
  in its denominator, and retain separate review mechanisms.
- **Participation:** the role-appropriate approach is accepted. Numerical
  non-batting thresholds and their exposure denominators remain unspecified;
  record them before ranking. Never substitute a PA minimum for a pitcher.

Acceptance does not establish the required source evidence or authorize a new
predicate. The full deliverable is reached only when real
qualified player rows pass source admission, calculation, SQL equivalence and
the live HTTP/browser path. The current seven-player browser fixture proves
presentation only. This audit records the unfinished work; it does not close it.
