# Nineteen public metrics: release status

This is the current implementation and release checklist. Historical component
proofs live in `benchmarks/metrics/`; they are not live readiness certificates.

**The dashboard is not fully populated.** Seventeen public metrics have
conditional player producers. The two review player integrations remain
unfinished. All twenty calculation kernels exist; Role Realization Breadth
is the backend-only twentieth metric.

September 23 operational update: the independent dashboard builder published
`20260923T150540Z-dashboard-50eab993cb66` at 12:55 Eastern with 2,773 games.
A subsequent live dashboard request selected 15 games from SQL and returned
**0/19 populated boards**. Publication therefore resolves neither the retained
admission-evidence gaps nor the unfinished review populations below. The
following automatic build was preparing the newly implemented player labels
and historical reference ranks. Authority SQL separately published 1,761 rows
from 75 source graphs. See the [operational delivery record](../infra/OPERATIONS-IMPROVEMENTS.md)
for deployed changes and their remaining runtime limits.

The subsequent evidence diagnosis separated genuine withholding from unrelated
Q5 fingerprint drift. Exact code-equivalent reuse is implemented for three
unchanged proof families, preserving the original status and fingerprint.
For inspected game 822680 this restores admitted runner-resolution evidence;
pitch-count and defense remain withheld for their original coverage reasons,
and runner-boundary remains unresolved. This has not yet established populated
live player cards. The next automatic dashboard build consumes the correction.
Exact pre-T1 admitted batting, scoring-run and runner-resolution proofs can
also be reused when their retained census passes the original stricter
zero-issue condition. Real game 822682 recovered all three admissions through
this path. Their original fingerprints and status remain in SQL provenance;
this is not a new conformance claim for a previously withheld graph.

The 13:55 Eastern publication, `20260923T165557Z-dashboard-f5ce432061b9`,
contains 2,773 games and the prepared-label/reference implementation. A fresh
live default request still returned 0/19 populated leaderboards for September
16. It predates the evidence-reuse fixes; the next NiFi build adopts those
automatically. Positive-only reuse now also covers exact earlier pitch-count
and runner-boundary implementations. The original admitted boundary proofs
for games 823979, 824140 and 824626 load successfully; original withholding in
the other twelve selected games remains unresolved.

## Next work from the September 23 live check

Use this list with the delivery order below. Operational implementation is
tracked separately in the linked operations record; no new RDF rebuild is
authorized by either list.

1. Confirm the next NiFi dashboard publication consumes the proof-reuse fixes
   and inspect qualified-player rows. The last live result remains 0/19.
2. Diagnose these four existing B1 failures against retained source censuses
   and promoted RDF. All eleven other selected games have admitted official
   PA proofs. These are actual retained withholding reasons, not generic
   missing-evidence claims:

   | Game | PA index | Event index | Retained issue |
   | --- | --- | --- | --- |
   | 823004 | 78 | 7 | `OFFENSIVE_REPLACEMENT_WITHIN_TURN` |
   | 823655 | 55; 98 | 5; 1 | `OFFENSIVE_REPLACEMENT_WITHIN_TURN` |
   | 823979 | 69 | 1 | `OFFENSIVE_REPLACEMENT_WITHIN_TURN` |
   | 824140 | 55 | 0; 3 | `OFFENSIVE_REPLACEMENT_WITHIN_TURN` |

   Q4/Q5 establish actual batting participation; they do not independently
   assign ambiguous official PA credit. Keep that distinction when fixing the
   adapter or recording the exact remaining graph contract gap.

   Follow-through: all four retained manifests contain exactly one actual
   batter per turn, matching every member in the retained B1 census; every
   player's independent PA total already reconciles. The checker had rejected
   substitution records despite this complete single-batter evidence. The
   source-owned maintenance worker now compares these exact retained source
   projections and runs the unchanged B1 SHACL over a read-only export of the
   promoted game. It preserves the original failed proof and publishes a
   separate adapter-versioned result. Multiple actual batters, unsupported
   context revisions, mismatched player totals or graph failures remain
   withheld. NiFi has now refreshed and admitted all four games through the
   unchanged B1 SHACL. All 15 selected-day games therefore have usable official
   PA admissions. Dashboard publication must still consume those results;
   admission alone is not a populated leaderboard claim.
3. Resolve the independent retained count, runner-boundary and defensive
   failures by their owning stage. The latest day has four admitted count
   proofs and three admitted boundary proofs after compatible reuse. The
   remaining boundary issues include PA-start timing, personal histories and
   award attribution. Do not equate those issues with absent provider fields.
4. Complete the two review-player integrations from supported graph inputs;
   then verify named player rows and expanded details for all 19 cards.

The dashboard now updates code-compatibility provenance separately from game
calculations. Existing checkpoints migrate only when their full old identity
matches the stored proofs and the same RDF, dimensions and calculation version.
Changes to outcomes or original proof contents refresh the affected admission
inputs using the existing calculators and retained SQL evidence. Unchanged
game kernels and observations are preserved; changed RDF, dimensions or math
still require game materialization. A compatibility-record edit alone does not
reprocess the season. The shared live graph check can also be reused while
Fuseki reports the same restart identity and write counters; see
[build reuse](BUILD-REUSE.md).

The remaining two latest-day run-construction-depth histories are covered by
the review-only [Q7 proposal](../proposals/mlb-game-zero-episode-history-isolation/README.md).
Its named semantic approval is pending. No targeted addition has been executed.

At 15:29 Eastern, NiFi published
`20260923T175511Z-dashboard-4ca9b33c4b25`. The default September 16 request
reported 560 ms of SQL execution but still **0/19 populated cards**. This
immutable release predates the new admission reader and the four B1 repairs.
Its full source checks took about 18 minutes at startup and 17 minutes at
publication; the newly deployed write-counter cache addresses repeated scans.

Retained SQL exposed a separate progress-calculation defect in three PAs:
822926/14, 823332/35 and 824306/49. An admitted independent steal or wild-pitch
prefix followed by two contact segments was rejected by the progress reducer,
although the contribution reducer already supports that exact C1 history.
Progress now delegates that separation to the existing helper. All three
recorded cases resolve using unchanged retained graph evidence, with reach 2
and separate runner credit. Fifteen focused tests cover terminal outs,
steal/PB/WP prefixes, exact history membership and binding-order independence.
NiFi must still publish these derived calculation changes. Other attribution
gaps and the two Q7 histories are not resolved by this fix.

The next focused diagnosis closed two more contribution defects in game
823979. PA 43 has a fielder's-choice result and a runner's two uncredited
positive segments; PA 54 has successive passed-ball and wild-pitch advances
before a walk. Both already had complete C1 membership, runner boundaries and
official PA admission. The reducer now applies its existing single-segment
rules to their exact multi-segment paths: actual endpoints are retained,
independent positives remain separate, and unknown attribution does not become
batter credit. PA 43 scores 0; PA 54 scores 1/4 for the walk. **All 86 official
PAs in this game now calculate completely** against retained SQL evidence and
current promotion-bound admissions. This is a component result, not a claim
that the selected day's other games or the published cards are complete.
Uncertain immediate comparison states and independent damage coverage remain
withheld separately. Missing members, branching paths and unsupported outs
still fail the existing completeness rules.

The 15:42 Eastern dashboard attempt encountered actual new game promotions
while capturing its snapshot. This overlap now returns `waiting-for-source`
through the existing one-minute NiFi owner, preserving both the published SQL
and completed game checkpoints. It does not publish a mixed snapshot or treat
ordinary concurrent ingestion as a broken metric build.

A further progress repair separates binary batting progress from unknown
running ownership. An excluded fielder's-choice/error batting contribution is
zero under the accepted policy. An explicitly attributed positive contact step
also stays positive across a complete, nonbranching C1 path containing only
safe/scoring steps, even when another step's ownership is unknown. This does
not assign the unknown step to the batter, supply a TFS magnitude, or classify
independent running. Empty Games and Contribution Mix retain their separate
unknown-running gap. Missing C1 members, branches and outs cannot use this
projection. Seventeen focused progress tests pass, including SQL equivalence.
Against the retained September 16 SQL evidence, this resolves seven more PAs:
822763/49, 823004/49 and /60, 823576/6 and /33, 823979/43, and 824382/20.
Seven of the fifteen games now have complete binary batting-progress inputs;
twelve PAs across the other eight games remain unresolved. This is component
evidence pending NiFi publication, not a complete selected-period leaderboard.

### Specific remaining count and review evidence

The retained pitch-count censuses for 822680, 822763 and 824140 reconcile
without source issues. Their Jena reports identify absent counted-foul Strike
Processes, not missing pitch responses. The exact examples are:

| Game / PA | Pitch ID | Retained mapping-selection reason |
| --- | --- | --- |
| 822680 / 63 | `a98ede81-c34b-323d-a4bf-c1979d65bcdb` | `SUBSTITUTION_IN_PREFIX` |
| 822763 / 21 | `e1662ba6-37c2-3a1a-8f0d-263c00618234` | `UNEXPLAINED_COUNTER_TRANSITION` |
| 824140 / 0 | `b0dc5b87-ff42-3aab-978a-1f0ca7158498` | `UNEXPLAINED_COUNTER_TRANSITION` |
| 824140 / 58 | `8959d67e-434d-377b-a830-d61ff751ea7b` | `SUBSTITUTION_IN_PREFIX` |

M3/M4 admits specific positively reconciled prefix cases, not arbitrary
substitutions or unexplained transitions. These cases need their exact
retained prefix evidence resolved before a targeted addition; do not suppress
the SHACL failure, rerun the whole game, or reacquire the season.

September 23 research also narrows the review investigation. MLB's
[ABS metric documentation](https://baseballsavant.mlb.com/abs-metrics-documentation)
defines challenge opportunity by a called pitch, the adverse call, remaining
challenge availability, and exclusions for position-player pitching and
technical outages. This supports the already accepted decision-time
eligibility requirement. A final challenge counter or a list of reviewed
pitches alone does not establish the complete never-reviewed denominator.
The retained `review-inventory.json` explicitly remains diagnostic, with no
graph-conformance or metric-population admission; it cannot be silently used
as one. MLB's [ABS dashboard](https://baseballsavant.mlb.com/abs) distinguishes
the initiating player from the opponent affected by an overturn. Provider
challenge rankings therefore cannot directly replace our affected-player
metric. This research changes no source mapping or metric definition.

The [Statcast CSV documentation](https://baseballsavant.mlb.com/csv-docs)
defines `hit_location` as the first fielder's position. That is not an ordered
inventory of all fielding, throwing, catching and tagging acts. These docs do
not close D1's complete-sequence requirement; broader data availability remains
a source investigation, not a basis for asserting that no evidence exists.

## Earlier release evidence

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

The required result is prepared SQL answers served quickly to the interface.
NiFi runs SPARQL and metric calculations over existing RDF before publication.
The dashboard reader performs observation pooling and population checks over
SQL and selects NiFi-prepared historical ranks. The full report reader retains
its separate immutable release. The [implementation guide](METRIC-SUITE-IMPLEMENTATION.md#required-serving-design)
separates serving ownership from RDF mapping coverage. Neither storing inputs
in SQL nor completing a source refresh proves fast dashboard delivery.

On September 17 the user corrected the scope: metric/SQL work must reuse the
existing graph and source additions must remain targeted. The user subsequently
allowed the already running batch `2e0062c6ccff4630840108858425ed4f` to finish.
That exception does not authorize another season RDF rebuild. This record
describes the instruction, not the batch's live completion status.

1. Let NiFi finish that existing batch and publish its matching immutable
   SQL/code release. Subsequent metric and SQL work starts from promoted RDF;
   reuse unchanged graph queries and calculated game products.
2. Inspect the published dashboard's qualified-player report for the requested
   range and use its exact gap codes to locate remaining owning-source or
   serving-adapter failures.
3. Complete integrations and calculations supported by existing RDF. Keep exact
   graph-input gaps separate from serving defects; implement only authorized,
   targeted source additions. Do not admit partial populations by dropping
   unresolved observations or turn their absence into a general rebuild request.
4. Verify actual named player rows and expanded card details for all 19 metrics.

NiFi owns repeated processing, validation, retries, quarantine and publication.
The asynchronous Repository Evidence gate is separate from this product check.
Use the [minimal-check policy](../../AGENTS.md#incremental-work-and-minimal-manual-validation)
instead of manually repeating the pipeline or creating new readiness gates.
See [implementation ownership](METRIC-SUITE-IMPLEMENTATION.md) and
[build reuse](BUILD-REUSE.md) for the engineering boundaries.
