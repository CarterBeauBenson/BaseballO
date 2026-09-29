# Nineteen public metrics: current readiness

**The dashboard is not fully populated.** Seventeen public metrics have conditional
player producers; the two review player integrations remain unfinished. Twenty
calculation kernels exist, including backend-only Role Realization Breadth.

## Last verified publication

Read-only selected-range checks on September 29, 2026:

| Surface | Recorded result |
| --- | --- |
| Published dashboard | `20260929T143536Z-dashboard-07a62db6ff3d`, published September 29 at 11:16 Eastern, 2,917 games; producer from `de840d4`, reader from `dcbab56` |
| Week selection | September 21-27: all 90 expected regular-season games |
| Week player leaderboards | **11/19 populated**, with names, selected-period aggregates, automatic minimums and disclosed exclusions; `ready=false` |
| Newly populated cards | Plate Appearance Contribution (20 qualified players), Runner Out Rate (19), Runner Loss per PA (19), Scoring Opportunity Lost (20) |
| Other populated cards | Offensive Reach (122), Help Without Advancing (122), Empty Games (142), Empty Game Damage (58, up from 6), Contribution Mix (2), Scoring History Length (163) and Run Contributors (130) |
| Expanded details | Scoring History Length has 163 named players for September 21-27, with Trea Turner and Jake Bauers among the leaders at an average of 4; 48 incomplete player records are explicitly excluded. The prior publication's full card/detail comparison matched all 163 rows. |
| Month selection (last checked on prior publication) | August 29-September 27: all 403 expected games; **5/19 populated**, with all game rosters verified. Qualified counts: Offensive Reach 7, Help Without Advancing 7, Empty Games 11, Scoring History Length 144, Run Contributors 69. |
| Season selection | The live dashboard now returns successfully for all 2,429 expected regular-season games and verified rosters. **1/19 populated**: only Scoring History Length has a qualifying complete record. Loading is repaired; full-season metric coverage is still incomplete. |
| Season leader | Scoring History Length returns Will Smith at **14/5**, averaging 35 complete scoring histories; the automatic minimum is 33 runs. The dashboard and previously checked detail agree. |
| Recent-game coverage | All 130 September 17-26 catch-up games are in SQL, including 823087 |

The latest weekly request spent 0.93 seconds inside the serving adapter. The
full-season API returned in 25.98 seconds on first use and 21.03 seconds on the
subsequent measurement (18.35 seconds inside the adapter). It no longer hits the
30-second request limit, but season loading is still too slow for the intended
instant interface. The deployed reader groups requested metrics into one
game-first traversal through the existing primary index and decodes only complete
records. Focused tests preserve exact results, exclusions and missing-game
detection across all 13 prepared types. The selected period and automatic
minimums remain unchanged.

The healthy SQL service and unavailable player populations are separate facts.
The current pointer is `state/serving/dashboard-current.json`; the independent
builder records progress in `state/serving/dashboard/progress.json`. Read those
owner records for a later state. Do not infer publication from a submitted job,
a source graph count or a successful component test.

That publication reused all 2,917 game calculations and refreshed the affected
player products. The seven previously
unverified rosters (824295, 823648, 823682, 823523, 824807, 823589 and 823668)
are now verified in published SQL. Several player/PA checks still fail; a complete
roster does not admit those players' metric records. Independent PA admission,
the compact snapshot, per-player damage isolation and the grouped reader are
live. Later reference-product changes still require their own NiFi publication;
do not infer their deployment from these results.

## Implemented repairs and retained component evidence

- The existing runner-resolution checks can now isolate individual PAs when a
  game's full census fails graph conformance. NiFi reads matching retained
  censuses and the existing game graph; the source-owned SHACL still checks
  every resolution, participant, outcome and endpoint in each admitted PA.
  The player projection uses this only for supported batting-progress averages
  and certain non-empty classification (including ineligibility for Empty Game
  Damage). Unknown PAs, TFS inputs and complete contribution channels remain
  separately constrained. Focused checks cover wrong runners, unexpected
  resolutions, empty/missing PAs, unknown source issues, exact player values,
  unchanged-partition reuse and incremental SQL publication without game
  recalculation. Runtime coverage must be read from NiFi's subsequent receipts
  and SQL publication; component checks are not populated-card counts.
  September 29 runtime receipts now admit 459 PAs across games 823712, 823805,
  824613, 823332, 823448 and 823087, leaving one failed PA in each game withheld.
  These are source-owned checks over unchanged RDF, awaiting the subsequent
  SQL player publication. Other games remain wholly withheld. For example,
  a read of game 822864's PA 0 confirmed its promoted Baserunning Act lacks
  the required agent assertion and its Runner Resolution Episode is absent.
  Its resolution has an existing runner participant; that does not supply the
  full admitted pattern. W1's PA 54 award repair alone would not supply these
  other missing facts. Game 824807 separately retains source reconciliation
  failures. Repeating SQL preparation cannot add either missing RDF assertions
  or missing source evidence, and none of these receipts certify all 19 cards.
- The September 29 11:56 Eastern publication (`20260929T151652Z-dashboard-fa3a211216a7`)
  still has **1/19** populated season cards. Its full-season HTTP request succeeds
  but took 29.19 seconds (26.22 in the adapter). That build reused all 2,917 game
  calculations and prepared 228 player partitions; it predates the fixes below.
  Publication alone consumed 17.4 minutes. The next reader snapshot now omits
  intermediate calculation tables retained in the working database and adds a
  covering completeness index. Aggregate JSON is read only for complete range
  records. Four focused comparisons preserve values, exclusions, all metric
  detail responses and compatibility with older snapshots. These publication
  and reader changes await NiFi deployment; no live speedup is claimed yet.
- The single-batter B1 repair now recognizes the exact pre-T1 context version.
  A September 29 census found 133 season games with replacement-only failures
  produced by that version. The omitted version previously prevented their
  retained evidence from reaching the existing graph/SHACL check. This is a
  repair candidate count, not 133 admissions or populated cards. Earlier
  completed repairs remain readable with their original status and fingerprint.
  Six focused checks pass, including the historical participation-code
  comparison, unchanged B1 shapes and rejection of conflicting evidence.
  NiFi owns the bounded checks and subsequent SQL publication.
- Full season is now the dashboard default, including invalid or retired URL
  presets; explicitly selected weeks, months and valid custom ranges remain
  supported. The served HTML and script match this change. Admission Evidence
  now orders missing latest-season rosters first, then unverified individual
  batting checks, then other season work. It uses the same admission constraints.
- Offensive Reach and Help Without Advancing no longer require runner-resolution
  evidence for a player with a verified zero-PA game. That game contributes zero
  observations, while unknown PA counts remain withheld. NiFi migrates only the
  affected prepared SQL rows when inputs match; no RDF query or game calculation
  is required. The last published season contains 993 affected records per metric
  across 31 games (529 distinct players). A read-only impact check found no new
  complete season batting records from this repair alone: other exclusions remain.
  This SQL correction awaits normal publication.
- The four percentile metrics now have NiFi-prepared exact player/game totals
  and counts for each complete historical reference. Range reads combine those
  products without decoding PA histories or recomputing ranks. Focused comparison
  against the existing reducers covers all four metrics, selected start dates,
  cutoffs and known ineligible observations. This does not admit missing reference
  populations; the new SQL product still awaits its normal NiFi publication.
- Player coverage displays verified game participation without inventing zero
  PA/run totals when the compact response does not include them. Populated cards
  with exclusions remain visible under Coverage gaps and explain those exclusions
  in their detail view. Known zero counts remain zero; missing counts stay absent.
- Empty Game Damage now isolates unrelated running uncertainty for games with
  independent PA admission and an admitted complete runner population. A focused
  regression retains a player's exact 1/4 damage while another runner's turn is
  unresolved; an own interrupted turn, unknown runner or missing census still
  withholds it. Unchanged game calculations and unaffected player products are
  reused. The published weekly leaderboard now has 58 qualified players.
- Publication checks SQL integrity on the prepared reader snapshot once,
  avoiding a second full scan of the larger working store. Progress records
  distinguish the final source check, snapshot copy and digest.
- Empty Game and Contribution Mix preparation now compares the official PA
  census within the independently admitted player population. Another batter's
  failed B1 check does not block that census. Possible running contributions
  from unresolved PAs still withhold any player they may affect.
- Publication excludes retained raw bindings and duplicated game-result blobs
  from the reader snapshot, preserving them in NiFi's existing working SQL.
  The component check preserves dashboard and expanded-detail responses.

- Independent C1/C2 checks now isolate a failed PA boundary while preserving
  its entire dependent half-inning history requirement. The SQL player producer
  uses admitted PAs through the existing exact contribution calculator. A focused
  regression recovers a player contribution while preserving every stored game
  calculation and making no RDF query. This is component evidence; live card
  coverage must be read from a subsequent published dashboard.

- The page defaults to the full latest loaded season and preserves explicitly
  selected week, month and valid custom date ranges;
  it no longer offers a latest-day preset or a single-day example as its entry
  point. The API continues accepting explicit one-day requests for compatibility.
- The analytical timestamp reader accepts Jena's shortened fractional seconds
  on Python 3.10. For example, `.55` and `.550` denote the same instant, but the
  previous parser rejected `.55`. The corrected reader recovers all 73 official
  PA count histories in retained SQL game 822841 using its existing admissions,
  including its three admitted zero-pitch walks. This is component evidence,
  not a claim that selected-period or season-wide leaderboards are populated.
- Database verification receipts are separated by Python runtime as well as
  immutable database digest. Windows reports different device/ctime values to
  NiFi's Python 3.10 and Explorer's Python 3.13. Sharing a receipt caused them
  to invalidate each other and rehash the 8.75 GB dashboard file. Each runtime
  retains all identity and digest checks; it verifies once and reuses its own
  receipt while that exact file is unchanged. Dashboard publication also tracks
  reader-code changes independently of metric calculation fingerprints.
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
- The September 28 complete-player range decision is
  [accepted](../archive/design-records/player-metric-presentation-2026-09-15/complete-player-ranges-2026-09-28.md).
  NiFi prepares exact player/game aggregates. A gap excludes the player's
  entire selected-range record for that metric; it does not shorten their
  period or average only their known plays. Cards disclose exclusions and
  retain the automatic participation minimums. Season percentiles still
  require their complete reference populations. The published SQL now includes
  these products; the dated results above distinguish the available week from
  the blocked month and season.
- Game 823087 promoted successfully at 11:16 Eastern on September 28 after
  the expected runner-record count was aligned with the existing RML selection.
  Its 114 raw rows include one null placeholder that the mapping does not select;
  the 113 selected records passed the existing checks. NiFi retried only this
  retained failed input. No mapping, ontology or corpus rebuild was needed.
- The retained B1 repair now recognizes the accepted Q7 context version.
  Its missing version entry previously prevented matching single-batter
  censuses from reaching the unchanged B1 SHACL. All ten recent matching games
  subsequently passed that validation in NiFi: 822760, 823165, 823411, 823733,
  824059, 824223, 824543, 824709, 824787 and 824948. Their source-owned admission
  records report `battingStatus=admitted`. Other failed censuses remain withheld;
  an applicable context version alone never establishes admission.
- Player-name extraction now binds only the selected graph in `VALUES` and
  discovers players from its label triples. The previous `(graph, UNDEF)`
  form returned zero names in deployed Jena; the corrected query returned 52
  names in game 822756. NiFi refreshes only the display product. The reader
  attaches names to player records using their selected game graphs, withholding
  conflicting names and avoiding repeated per-game labels in season responses.
  The published release above includes the corrected names.
- Player-range preparation is restricted to the dashboard's selectable
  regular-season and All-Star game sets. An unrelated exhibition roster with
  both club and national-team exposures had aborted the first full preparation
  at game 831427. Exhibition RDF and its existing derived game products are
  retained; those games do not participate in this dashboard's player products.
- The dashboard's pre-build quiet window no longer waits for admission
  maintenance to stop. Minute-by-minute retained B1 receipts had continually
  reset its 60-second timer after the failed build. Receipts still trigger input
  refreshes; only RDF promotion and independent schedule events reset that
  short wait. Publication keeps its existing final source check.
- NiFi recorded a transient Windows access denial replacing `progress.json`
  on the next attempt. Atomic serving metadata writes now retry short-lived
  sharing errors while preserving the previous complete file. Persistent
  failures still stop the operation. The diagnostic file watcher was stopped.

The complete earlier diagnosis and dated build history are retained in the
[September 23 history](../archive/operational-history/2026-09-23/METRIC-READINESS.md).
The [operational delivery record](../infra/OPERATIONS-IMPROVEMENTS.md) describes
worker ownership; [build reuse](BUILD-REUSE.md) describes invalidation.

## Remaining work after the September 29 selected-range check

1. The four retained September 17 retries for 822848, 822854, 822936 and 823338
   completed and are in the 05:35 publication. Do not queue them again. All four
   have admitted run censuses; 822936 also has admitted B1. The other three
   retain their precise within-turn replacement issues.
2. The September 29 repair separates existing B1/E1 roster checks and individual
   B1 player checks from whole-game admissions. NiFi's existing Admission Evidence
   worker prioritizes missing rosters and unverified individual batting checks
   across the full latest season, ahead of already checked games. It reads
   retained censuses or quarantined inputs and validates the **existing graph**.
   A later source response retains a distinct validation hash; it never becomes
   the promotion's original input. Original admissions stay unchanged.
   Dashboard SQL updates only affected player projections; unchanged game
   evidence, kernels and player aggregates are reused. A focused integration
   regression rejects any attempt to re-extract RDF or rerun game calculations.
   The first runtime check for 822864 verified its roster, PA inventory and all
   53 rostered players. Its receipt initially exceeded Windows MAX_PATH; the
   output filename is now shortened. This is component evidence, not a claim
   that all 28 games or a new selected-season leaderboard have published.
   For retained raw witnesses, that same bounded graph read also runs the six
   unchanged source admission profiles in one Jena session. Each records the
   original graph/input identity separately from the validation export and
   response. The existing-graph B1 check for 822864 is admitted; its run and
   runner-resolution checks fail graph conformance, and its count/boundary
   checks still identify actual gaps (including PA 54's nonpitch count event).
   Missing old proof files and absent current graph facts are distinct outcomes.
3. Continue contribution/Empty Game attribution diagnosis. The retained component
   check left player 681508 in game 822846 (PA 37) and player 670770 in game 824467
   (PA 65) uncertain. Reassess the updated promoted facts before proposing another
   source addition.
4. Resolve the count, PA-boundary, defensive and review populations below.
   These independent gaps do not authorize a corpus rebuild. Percentile cards
   still need the complete reference season; the sole saved Recovery reference
   has only 34 observations at an early cutoff and cannot rank the full season.

The full-season priority diagnosis of the 11:16 publication found 274 games with
withheld whole-game B1: 95 already had individual player checks, one had a failed
PA inventory, and 178 had no individual check in that published SQL. Of those
178, 108 reported missing or stale B1 proof; the rest include actual graph,
replacement, result and PA-count issues. These are publication-time counts, not
a claim that NiFi has not subsequently checked them. The source-owned worker
continues independently, and prepared SQL catches up at its next publication.

The user's September 29 instruction explicitly prohibits rebuilding the database.
This repair does not acquire API responses, run RML, replace game graphs, clear
SQL or recalculate unchanged games. The existing SQL owner updates the retained
working database and publishes its normal immutable snapshot. Updating a derived
player record does not authorize a source rebuild.

Individual batting admission does not certify another metric's missing facts.
Contribution still needs the affected runner boundaries and ownership; defensive
averages need the full relevant act/agent population, and depth also needs order.
The existing D1 contract admits selected performances, not all performances on
every contact play. Review player rates still need a reconciled mechanism,
affected-player census and (for dependence) eligible unreviewed outcomes. The
retained diagnostic review inventory is not that graph contract. These gaps
cannot be closed by converting unknowns to zero or by using a smaller percentile
reference. Any required RDF addition must be separately scoped to the missing
facts and reviewed under the existing RML/identity rules.

### Specific remaining batting, count and review evidence

The September 21â€“27 B1 conformance failures for games 823327 / PA 46,
823489 / PA 6, 824301 / PA 40, 824302 / PA 17 and 824866 / PA 42 share one
precise mismatch: the retained source census expects `StrikeoutProcess` for
`strikeout_double_play`, while the promoted result is typed only as
`BaseballInstitutionalProcess`. The existing B1 reports reject the result
membership and affected player's PA count. This is mapping coverage debt;
there is source evidence. It is not repaired by inventing a statistical PA
in SQL or typing a composite whole from one of its parts. Other interrupted
turns in those games remain distinct from official completed PAs.

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

Game 822864 / PA 54 exposes a separate exact intentional-walk selection gap.
The retained response has a pinch-runner replacement at index 0 and a mound
visit at index 1, both at 0-0, followed by four explicit non-pitch VB records
at indexes 2-5 and the batter's first-base award joined to index 5. Both
`virtual_intentional_walk` and the mapping context's `runner_metric_evidence`
currently require exactly four total events indexed 0-3. Relaxing only the
count validator cannot establish the missing award-attribution graph pattern.
Any repair must cover that mapping selection and its targeted additive
execution; it must not fabricate four pitches or four umpire acts. No mapping
or RDF change for this case was made by the September 29 serving fixes.
The bounded [W1 selection package](../archive/design-records/mlb-game-zero-pitch-walk-prefix/README.md)
was explicitly accepted on September 29 for the existing award pattern and
additive execution scope. Its implementation follows the separate decision commit.

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
coverage report for its explicit one-day service probe. The dashboard itself
defaults to the full latest loaded season and preserves the user's range. A healthy service may have
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
