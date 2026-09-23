# Nineteen public metrics: current readiness

**The dashboard is not fully populated.** Seventeen public metrics have conditional
player producers; the two review player integrations remain unfinished. Twenty
calculation kernels exist, including backend-only Role Realization Breadth.

## Last verified publication

Read-only check on September 23, 2026, at 17:19 Eastern:

| Surface | Recorded result |
| --- | --- |
| Published dashboard | `20260923T175511Z-dashboard-4ca9b33c4b25`, published at 15:29 Eastern, 2,773 games |
| Default selection | September 16, 15 regular-season games |
| Service readiness | HTTP 200, `materialized-serving` |
| Player leaderboards | **0/19 populated; 0/19 complete populations; dashboard ready=false** |
| Latest fixes | Implemented and pushed; publication in the dashboard remains pending |

The healthy SQL service and unavailable player populations are separate facts.
The current pointer is `state/serving/dashboard-current.json`; the independent
builder records progress in `state/serving/dashboard/progress.json`. Read those
owner records for a later state. Do not infer publication from a submitted job,
a source graph count or a successful component test.

## Completed repairs awaiting dashboard publication

- Exact compatible-proof reuse separates unrelated context-code changes from
  actual proof changes. It retains original statuses and fingerprints; prior
  withheld proofs are not promoted to admitted by compatibility alone.
- NiFi refreshed all four latest-day B1 failures (823004, 823655, 823979, 824140)
  from retained single-batter participation evidence through the unchanged B1
  SHACL. All 15 selected-day games now have usable official-PA admissions.
- [Q7](../archive/design-records/mlb-game-zero-episode-history-isolation/README.md)
  completed at 17:05 Eastern. Game 822846 gained four histories / 26 triples
  (promotion `c13a55c7232c413ead2f9376401530cd`); game 824467 gained three histories /
  23 triples (promotion `c01906024ee84e54bbf23e37d7c42410`). Both passed source SHACL
  and query-index equivalence and emitted promotion events. The two omitted
  scoring-history links are repaired. Zero-episode runners and other incomplete
  half-innings stay withheld. The temporary repair timer is stopped.
- Contribution reduction handles complete multi-segment paths with independent
  advances kept separate. All 86 official PAs in the retained game 823979
  component check calculate; exact arithmetic is reused across identical
  numerical cases without caching player identity or admission decisions.
- Binary batting progress and per-player Empty Game certainty no longer depend
  on unrelated unknown running ownership. The retained September 16 component
  check resolved progress in 7/15 games and Empty Games in 13/15 games. Those
  component counts precede Q7's graph additions and are not a new live SQL claim.
- Dashboard SQL retains reusable game products, prepared names and historical
  reference ranks. Admission-only bookkeeping preserves unchanged calculations;
  source drift retains committed work for the next NiFi tick.

The complete earlier diagnosis and dated build history are retained in the
[September 23 history](../archive/operational-history/2026-09-23/METRIC-READINESS.md).
The [operational delivery record](../infra/OPERATIONS-IMPROVEMENTS.md) describes
worker ownership; [build reuse](BUILD-REUSE.md) describes invalidation.

## Next work from the September 23 live check

1. Publish and inspect the SQL results incorporating the completed repairs.
   Confirm scoring histories and named qualified-player rows in the actual
   dashboard, rather than treating the old release's gaps as new source failures.
2. Continue contribution/Empty Game attribution diagnosis. The retained component
   check left player 681508 in game 822846 (PA 37) and player 670770 in game 824467
   (PA 65) uncertain. Reassess against the updated promoted graphs before deciding
   that another source addition is required.
3. Resolve the precise count and PA-boundary cases and the defensive/review
   populations below. These independent gaps do not authorize a corpus rebuild.

### Specific remaining count and review evidence

These retained pitch-count censuses reconcile without source issues. Their
Jena reports identify absent counted-foul Strike Processes:

| Game / PA | Pitch ID | Retained mapping-selection reason |
| --- | --- | --- |
| 822680 / 63 | `a98ede81-c34b-323d-a4bf-c1979d65bcdb` | `SUBSTITUTION_IN_PREFIX` |
| 822763 / 21 | `e1662ba6-37c2-3a1a-8f0d-263c00618234` | `UNEXPLAINED_COUNTER_TRANSITION` |
| 824140 / 0 | `b0dc5b87-ff42-3aab-978a-1f0ca7158498` | `UNEXPLAINED_COUNTER_TRANSITION` |
| 824140 / 58 | `8959d67e-434d-377b-a830-d61ff751ea7b` | `SUBSTITUTION_IN_PREFIX` |

M3/M4 admits specific positively reconciled prefixes. Resolve these exact cases
before any targeted addition; an unexplained transition is not covered merely
by the presence of a foul record. Boundary admissions separately depend on
supported PA-start states, clocks, replacements and review effects. Q7 does
not admit whole half-inning boundary populations.

The retained review inventory is diagnostic. It does not establish a complete
eligible never-reviewed denominator, decision-time challenge availability or
all affected-player/mechanism populations. September 23 research sources remain
[MLB ABS metric documentation](https://baseballsavant.mlb.com/abs-metrics-documentation)
and the [MLB ABS dashboard](https://baseballsavant.mlb.com/abs). The complete
ordered defensive-act inventory also remains unresolved; the first-fielder
`hit_location` in the [Statcast documentation](https://baseballsavant.mlb.com/csv-docs)
does not establish every fielding, throwing, catching and tagging act. These
are exact graph/population gaps, not claims that the provider has no evidence.

## How to check the actual release

Open `/metrics` for the selected date range. The cards and dashboard summary
count qualified players after the approved participation minimums. The
`POST /api/metrics/dashboard` response also includes `dashboardReadiness`:

- `populatedLeaderboards`: cards with qualified player rows;
- `completePopulations`: cards whose required populations pass qualification
  validation, including every separate review mechanism;
- `emptyLeaderboards`: complete populations with no qualifying players;
- `unavailableLeaderboards`: cards without complete player results;
- `ready`: all 19 cards populated and all required populations complete;
- `cards`: each metric's row count, population state and remaining gap codes.

`GET /health/ready` keeps reporting **service** readiness and includes the same
coverage report for its default one-day selection. A healthy service may have
an unready dashboard. A complete period with no qualifying players is distinct
from missing evidence; it does not justify lowering the minimum.

## Remaining work by metric

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
| Empty Games | Implemented conditionally | Certain classification for every eligible player-game; retain all official PAs and the game count |
| Empty Game Damage | Implemented conditionally | Complete Empty Game classification and negative PA contributions; successful independent steals are assigned to their runner across PAs. Separate independent damaging episodes, unknown running ownership and interrupted turns remain gated |
| Contribution Mix | Implemented conditionally | Complete positive play/channel inventory and separate running-attempt qualification |
| Two-Strike Extension Rank | Implemented conditionally | Complete pitch/count and B1 admissions for every reference-season game, plus independent schedules through the cutoff |
| Longest Defensive Sequence | Implemented; population gated | Complete act/agent/order admission and independent roster proof |
| Defenders Involved | Implemented; population gated | Complete act/agent admission and independent roster proof; order is a separate gate |
| Scoring History Length | Implemented conditionally | Every counted scoring history, source run/roster proof and selected schedule |
| Run Contributors | Implemented conditionally | Same complete scoring histories with supported contribution ownership |
| Replay Overturn Rate | Unfinished as a player producer | Pitch-review affected-player extraction and SQL retention implemented; other subjects, mechanisms, complete population and qualification remain |
| Outcomes Changed by Review | Unfinished | Complete eligible never-reviewed decisions, decision-time legal availability, operative outcomes, affected players and separate mechanisms |
| PAQ with Tie-Breakers | Implemented; defensive population gated | Admitted contribution, two-strike and defensive inputs; complete separate season references and selected participation |

The approved display remains a selected-period player average, except Empty
Games, which is a game count. Batting qualification is 3.1 PA per team game,
rounded to the nearest whole PA; other metrics use the accepted participation
minimums. Review mechanisms remain separate. These are settled decisions.

## Verified component evidence

| Evidence | What it establishes | What it does not establish |
| --- | --- | --- |
| [Schedule qualification](../benchmarks/metrics/schedule-qualification-2026-09-17/README.md) | All 258 requested dates and 2,788 occurrences reconcile with the unchanged response; postponed makeup dates no longer invalidate the range | Complete promoted game set, player inputs or live dashboard population |
| [SQL building blocks](../benchmarks/metrics/sql-building-blocks-2026-09-16/README.md) | Exact equality of all 20 responses over one promoted game; indexed projections round-trip and reduce reader work | Full-season performance, current source admission completeness or live leaderboard population |
| [Count-history completion](../benchmarks/metrics/count-history-completion-2026-09-16/README.md) | All 81 official PAs in game 823585 pass source SHACL, batting/count admission, canonical Jena extraction and exact SQL; virtual intentional walks and reconciled foul/replacement prefixes are handled | Complete live date range or reference season |
| [Runner placement and third outs](../benchmarks/metrics/runner-placement-completion-2026-09-16/README.md) | All 15 August 25 fixtures reconcile 415 personal histories; two full-game proofs retain all 15 scoring histories in SQL | All contribution ownership or immediate PA-state cases |
| [Contribution proof](../benchmarks/metrics/contribution-mixed-plays-2026-09-15/result.json) and [progress adapters](../benchmarks/metrics/authorized-metric-fixes-2026-09-15/README.md) | All 79 PA contributions in game 566279 resolve; isolated player means survive SQL | Complete season rankings; two comparison states remain unresolved |
| [D1 defensive proof](../benchmarks/metrics/d1-defensive-mapping-2026-09-16/README.md) | 20 supported acts and all 107 contact plays reach SQL; 13 simple-catch plays have complete act evidence | Complete defensive populations or unsupported action order |
| [Review subject extraction](../benchmarks/metrics/runner-records-review-subjects-2026-09-16/README.md) | Two real affected batters survive graph extraction and SQL | Complete review mechanisms, eligible never-reviewed decisions or player rates |

D1 and M3/M4 were accepted before implementation in `e4166c1`; C3 was accepted
in `06cc732`. Their decisions remain in `archive/design-records/`. Existing
mapping debt must not be described as absent provider evidence. The accepted
source profiles, attribution policies and participation minima remain enforced.

## Delivery order

The result to deliver is prepared SQL answers served quickly to the interface.
NiFi owns graph queries, metric calculations, reference preparation, retries
and publication. The dashboard reads SQL and performs selected-range pooling
and participation checks; it does not reconstruct graphs on page load.

1. Consume the completed fixes through the existing SQL owner and inspect the
   published qualified-player report.
2. Fix supported analytical defects and document exact remaining graph gaps.
   Implement only authorized, targeted source additions, preserving other RDF.
3. Verify actual named-player rows and expanded details for all 19 metrics.

The September 17 source-batch permission is historical and does not authorize
another season rebuild. Neither stale proof fingerprints nor a serving-code
change justifies reacquisition or RML execution. Use the
[minimal-check policy](../../AGENTS.md#incremental-work-and-minimal-manual-validation),
[implementation guide](METRIC-SUITE-IMPLEMENTATION.md) and [roadmap](../ROADMAP.md).
NiFi's asynchronous Repository Evidence observer is separate from product readiness.
