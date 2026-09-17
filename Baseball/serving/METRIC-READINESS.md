# Nineteen public metrics: release status

This is the current implementation and release checklist. Historical component
proofs live in `benchmarks/metrics/`; they are not live readiness certificates.

**The dashboard is not fully populated.** Seventeen public metrics have
conditional player producers. The two review player integrations remain
unfinished. All twenty calculation kernels exist; Role Realization Breadth
is the backend-only twentieth metric.

The September 16 live check returned HTTP 200 in 16.8 seconds for
August 25 from SQL, with all 15 scheduled games selected and **zero populated
player leaderboards**. The new coverage report explicitly returned `ready:false`
and 19 unavailable player boards. The active SQL build was
`20260917T001611Z-1122c341fcc2`, paired with code `4828061`; publication of the
subsequent serving and source fixes has not been established by these checks.
NiFi's already queued season refresh had advanced to its proof stage. An HTTP
200 or a completed SQL build does not establish populated player cards.

The initial request after that SQL publication hit HTTP 503; a direct read and
the subsequent HTTP check succeeded. A newly published 12.3 GB database was
being checksum-verified inside the first request's 30-second deadline. The
materializer now prepares a separate verified receipt for each database before
publication, with the same complete hash and file-identity checks. This fix
applies to subsequent NiFi builds; it does not manufacture metric populations.

Metric suite 2.1 moves reusable participation and analytical observations into
indexed SQL and prepares admitted season ranks during NiFi builds. On one
already promoted game, the stored-input reader matched all 20 existing metric
responses exactly and took 48.688 ms versus 676.928 ms for the evidence reader.
The [bounded proof](../benchmarks/metrics/sql-building-blocks-2026-09-16/README.md)
records its current withheld admissions. This is reader correctness and timing
evidence, not a claim that the live dashboard or reference season is complete.
`buildingBlockCoverage` now distinguishes each input family's projection counts
and gaps; those diagnostics supplement the player-population report.

On September 17, NiFi's source proof completed and the season refresh reached
`waiting-batch`. The August 25 dashboard still returned 0/19 populated boards
from build `20260917T012319Z-89e828146695` (code `f0f6dbd`), with 15 games and
8,789 ms reported SQL duration. The next stored-input release was not yet live.

The pending season manifest also exposed an independent calendar defect: one
explicitly postponed May game carried a September 22 makeup `officialDate`,
causing all 258 requested dates to be marked incomplete despite reconciled
response totals. The [schedule correction proof](../benchmarks/metrics/schedule-qualification-2026-09-17/README.md)
retains all 2,788 occurrences and restores transport completeness. The existing
NiFi worker now repairs affected coverage using separate immutable snapshots,
without restarting game mapping. Actual graph and player admissions still apply.

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
| Empty Games | Implemented conditionally | Complete official PAs and positive batting/running channels; retained game count |
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

1. Let NiFi finish the already requested current-proof refresh and publish a
   matching immutable SQL/code release. Reuse unchanged graph queries and
   calculated game products; do not restart unaffected work.
2. Inspect the published dashboard's qualified-player report for the requested
   range and use its exact gap codes to locate remaining owning-source or
   serving-adapter failures.
3. Complete the review player integrations and remaining defensive, attribution
   and season-population requirements identified above. Do not admit partial
   populations by dropping unresolved observations.
4. Verify actual named player rows and expanded card details for all 19 metrics.

NiFi owns repeated processing, validation, retries, quarantine and publication.
The asynchronous Repository Evidence gate is separate from this product check.
See [implementation ownership](METRIC-SUITE-IMPLEMENTATION.md) and
[build reuse](BUILD-REUSE.md) for the engineering boundaries.
