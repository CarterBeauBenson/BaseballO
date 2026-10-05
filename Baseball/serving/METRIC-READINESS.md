# Nineteen public metrics: current readiness

**The dashboard is not fully populated.** Seventeen public metrics have conditional
player producers; the two review player integrations remain unfinished. Twenty
calculation kernels exist, including backend-only Role Realization Breadth.

The October 4 scope decision retires spring training, exhibitions and WBC work.
New serving builds select the remaining MLB games from existing promoted RDF;
the 486 retained spring/exhibition games no longer enter build dependencies.
Their data and historical diagnoses remain stored. This scope reduction does
not establish completeness for the remaining metric populations.

## Current publication: October 5, 07:14 Eastern

Build `20261005T105915Z-dashboard-275648582d65` published at 11:14:34 UTC,
paired with code `4d72724`. The full-season HTTP response still has **5/19
populated cards and 0 complete populations**. Ranked players: Offensive Reach
1, Help Without Advancing 5, Empty Games 291, Scoring History Length 196 and
Run Contributors 9. The other fourteen have no qualified rankings.

The published SQL now has 293 unknown player-game PA counts across 147 games
and 254 players, down from 1,160 in the earlier snapshot. The previous queue,
retained-census and individual-reference changes have reached this publication.
They improve coverage but do not finish the required metric populations.

The next query repair separates an event's existing interval/instants from its
optional timestamp values and keeps strike evidence tied to the particular
pitch record. Four focused extraction/migration checks pass; unchanged games
reuse their calculated SQL while affected games use the existing NiFi SPARQL
stage. This repair has not yet reached the measured publication above. RML and
authoritative RDF are unchanged. Continue the remaining audit in the
[active plan](../ROADMAP.md#1-complete-the-nineteen-metrics-execution-plan).

The independent PA checker also no longer treats inning/team run-total
diagnostics as failed batting counts. It retains those diagnostics for the
scoring-run owner and still requires every applicable B1 SHACL result. Existing
report evidence supports correcting 52 player records in 824295; 824807 remains
withheld for its separate PA inventory/incomplete-turn failures. Two focused
scope/retry checks pass. This is pending NiFi execution/publication, not another
increase in the measured counts above.

Per-PA boundary checks now consume the current checked B2 census for the same
graph before falling back to original promotion evidence. A recorded example,
824218, was retaining an obsolete PA 5 review failure despite its newer checked
census. The source handoff and bounded negative-result retry are repaired;
the seventh-inning replacement/history issues remain, and NiFi must run the
unchanged PA SHACL before any resulting contribution rows can publish.

## Historical publication: October 4, 23:30 Eastern

The published build is `20261005T031625Z-dashboard-5c27e45118a5`, using
`e75455c`, published October 5 at 03:30:39 UTC. It contains 2,444 active games;
the default 2026 regular season has all 2,429 expected games, a complete
schedule and all 2,429 verified rosters. The full-season HTTP check returns
**5/19 populated cards and 0 complete populations**. Ranked players: Offensive
Reach 1, Help Without Advancing 3, Empty Games 204, Scoring History Length 196,
and Run Contributors 9. The other fourteen have no rankings. Empty Games has
no appearance minimum; its incomplete records remain excluded separately.

The authorized RML repair backlog is clear: 754 selected histories complete,
no pending inspections and no recorded repair issues. That status is scoped
to the recorded repairs, not complete metric evidence. The SQL handoff and
schedule-publication problems below are resolved in this build.

Read-only SQL diagnosis identifies 1,160 unknown player-game PA counts across
236 games and 629 players. Of those, 789 records across 15 games and 433 players
have no individual admission in this publication. Their older NiFi checkpoints
say `retained-rdf-unavailable`; this is not a finding that authoritative RDF or
MLB facts are absent. The other 371 rows retain specific substitution, result,
player-conformance, PA-inventory or source-reconciliation failures.

| Published whole-game admission | Admitted | Withheld |
| --- | ---: | ---: |
| Official batting population | 2,192 | 237 |
| Runner resolutions | 2,420 | 9 |
| Runner boundaries | 1,196 | 1,233 |
| Pitch/count histories | 857 | 1,572 |
| Scoring runs | 2,427 | 2 |
| Defensive population | 0 | 2,429 |

These requirements are independent; missing/stale proof flags must be diagnosed
separately from actual graph omissions. Individual admissions can support a
player despite an unrelated whole-game failure. The reference-player table has
only one early recovery cutoff, not the required full-season references. Both
review-player integrations are still unfinished.

The complete execution order, exact first fifteen games, component owners,
dependencies and nineteen-card completion criteria are in the
[active repair plan](../ROADMAP.md#1-complete-the-nineteen-metrics-execution-plan).
Its October 5 update starts with auditing and, where necessary, rewriting the
SPARQL extraction and calculation queries against current RDF and accepted
definitions. It then follows each family through prepared SQL, publication,
HTTP and the live card/detail flow. Existing query output is not presumed
correct, and a populated card alone does not close its audit. This is planned
work; the dated publication counts above have not been remeasured by that update.
Older dated entries below preserve previous observations and implementation
history; they are not current retry instructions or current population counts.

## October 5 execution, awaiting a new SQL publication

The admission queue now prioritizes the fifteen games missing individual player
proofs, with bounded retries. The retained single-batter adapter accepts the
post-T1 census producer used by the season's promotions, while retaining exact
source/manifest identities, result-type compatibility and current B1 SHACL.
The diagnosed censuses for games 822760 and 824921 can reach that check. Neither
this code repair nor a submitted check is a newly admitted population.

The SQL reference builder now supports complete individual B1 populations when
a whole-game batting check is withheld. All rostered players and the complete
PA inventory must pass, and their identities must match the RDF roster. The
affected contribution/recovery inputs are prepared from retained RDF bindings
in SQL. Count, boundary, resolution and defense requirements remain mandatory.
The published snapshot contains one immediate candidate, 824302; this change
alone does not complete the season reference. Existing game calculations are
reused across deployment, and changed reference inputs invalidate only their
affected player partitions.

The selected-date query now applies the date restriction through the existing
coverage index before loading player aggregates. A direct September 16-27 SQL
comparison returned identical results for 159 games in 1.46 seconds versus
7.23 seconds for the warmed prior query; the earlier cold read took 23.29 seconds.
These are direct SQL-reader measurements, not a new live HTTP or browser claim.

The concrete [BK1 mapping review](../proposals/mlb-game-balk-runner-attribution/README.md)
addresses separately recorded balk advances. It remains pending named approval.
Other recorded work includes the interrupted-turn `other_out` admission case
and the stale per-PA boundary-census handoff described in the
[active plan](../ROADMAP.md). Those are open, not fixed by the reference change.

At the 04:25 UTC runtime check, the existing legacy report SQL job still held
the shared memory slot, so admission maintenance and Dashboard SQL deferred.
It was advancing, not failed. No parallel heavy worker or RDF rebuild was
started to bypass that limit. NiFi owns the queued checks and next publication;
the five-card baseline above remains the last verified dashboard outcome.

## Historical October 4, 22:46 Eastern handoff check

NiFi's repair observer reports `recordedWorkClear=true`: all 754 selected
history cases are complete, with no outstanding inspections, recorded repair
issues or active RML quarantines. This closes the recorded authorized repair
backlog; it does not establish complete populations for all nineteen metrics.
Existing successful SHACL results remain usable. Changed facts receive their
own source-owned validation; there is no blanket RDF rebuild or SHACL rerun.

Two execution defects delayed the next SQL publication. Admission maintenance
now resumes its old deferred checks before the routine sweep, using unchanged
evidence producers. The serving launch budget also accepts PowerShell's
seven-digit fractional timestamps on the installed Python 3.10 runtime.
Its existing release condition remains a fresh, clear NiFi repair report.

The published dashboard is still `20261004T225057Z-dashboard-04f2bc7b7e80`,
published at 19:05 Eastern, with 2,444 active games. Its full-season HTTP response
contains all 2,429 regular-season games and verified rosters, but **0/19 cards**
because its schedule evidence is incomplete. NiFi produced the repaired
schedule snapshot at 19:10, after that publication. The next incremental SQL
publication must import that snapshot and the later game evidence; the check
must not be bypassed or the old publication described as current.

A separate September 16–27 HTTP check covers 159 games with a complete schedule
and all 159 rosters. It returns **11/19 populated cards**, including 119 Offensive
Reach players, 140 Help Without Advancing players, 396 Empty Games counts,
246 Scoring History Length players and 170 Run Contributors players. Player
names and range-dependent participation minimums are present. Empty Games has
no appearance minimum and includes zero counts; its detail endpoint also works.
These are selected-range results, not full-season completion. Eight cards still
lack season reference products, defensive populations or review-player
integration. Custom-range preparation took 22.4 seconds in this check, so
instant arbitrary-range response is not established either.

Next: NiFi publishes prepared SQL from the existing RDF and current evidence,
then verify the default full season and its detail results against that build.
Browser automation was unavailable during this check; HTTP verification does
not substitute for a completed visual interaction check.

## Earlier offense implementation notes (October 1)

The user narrowed active work to offense on October 1. Prioritize batting
qualification, Offensive Reach, Help Without Advancing, Empty Games,
contribution and run construction. Defensive completion is not a prerequisite
for these independent offensive results.

The existing Q7 repair now covers 78 specifically inventoried additional games,
with 190 complete nonempty runner histories recoverable from retained source
reconciliation. This uses the September 30 narrow repair authorization and
three unchanged RML maps; it changes no ontology, mapping selector or semantic
freeze and acquires no source responses. The [worker and exact scope](../sources/mlb-game/pipeline/TARGETED-HISTORY-ADDITION.md)
preserve the unresolved empty histories and incomplete halves. NiFi completed
the first game, 822680, at 17:06 UTC on October 1: one history and six missing
triples. That is a verified graph addition, not yet a published season metric
improvement. The remaining inventory executes asynchronously in the existing
MLB Game group.

The player projection also spread an ambiguous batter's uncertainty across the
entire game roster. It now keeps that uncertainty with all candidate batters and
runners identified by the retained RDF query rows. It assigns no batting credit;
missing participant bindings retain the previous fallback, and Empty Game
classification still requires the admitted runner census and the player's
official PA participation. A read-only comparison of 20 affected regular-season
games resolves 81 wrongly withheld Empty Game records, sufficient to complete
20 additional season player counts in that captured working snapshot. These are
calculated improvements, not yet verified live counts. NiFi updates the affected
player products from stored SQL evidence and reuses unaffected game products.
Four focused checks cover participant isolation, missing evidence, incremental
reuse, and exclusion of a genuinely incomplete selected-range player record.

One admission handoff defect is repaired: individual player checks previously
reused the original B1 source census even after the retained-batting stage had
reconciled its substitution errors. Where another player's graph failure still
withheld the whole game, those stale source errors continued excluding hitters.
The published snapshot has 18 such player-game exclusions with otherwise clean
individual graph checks. NiFi now feeds the existing reconciled census into
the unchanged player SHACL, records the source/proof hashes, and prioritizes
those games. It retains unrelated failures and reuses completed checks. This
changes neither RDF nor RML; the 18 are repair candidates, not a claim of newly
published or fully qualified season players.

Scoring History Length also confused multiple batter bindings in a substituted
PA with conflicting runner states. Depth now uses the supported runner origin
and endpoint, independently of batter attribution; Run Contributors retains its
attribution requirement. Read-only recalculation of the affected stored SQL
evidence resolves all six such scoring histories in games 823632, 823927,
824374 and 824642 (depths 4, 4, 4, 4, 4 and 2). NiFi's incremental SQL upgrade
recalculates only the affected depth results, then their player/range products.
It preserves other metrics and does not query or rebuild RDF. Live publication
must still be verified separately from those six calculated results.

## Earlier publication history (October 1 and September 30)

The October 1 16:34 UTC publication (`20261001T160907Z-dashboard-b3619893bfc3`)
confirmed that the corpus-change publication starvation was repaired. Its HTTP
check exposed a separate timing defect: games 823589 and 823648 had been read
before their post-addition roster checks finished, making all 19 cards
unavailable through `COMPLETE_PARTICIPATION`. Both current roster checks already
pass. The builder now rereads only initially missing roster admissions before
preparing player products and preserves an existing roster-complete publication
if a candidate would suppress the dashboard for that reason. This does not
admit missing evidence or rerun ingestion. Four focused checks cover late
admission arrival, retention and resume, captured-source publication and
independent player-proof updates.
The retained `20260930T162149Z-dashboard-5d417d3bf58b` snapshot was restored after
checking its immutable database and paired reader. The follow-up live HTTP
request again returns all 2,429 verified rosters and five populated cards:
Offensive Reach 1, Help Without Advancing 5, Empty Games 266, Scoring History
Length 17 and Run Contributors 1. The newer incremental build continues;
restoring service does not close the remaining metric coverage gaps.
The older in-flight `504cd7e` build published at 17:03 UTC with the same race
in different games, 823682 and 823668, before it contained the roster handoff
repair. Its pointer was likewise restored to the verified September 30 build.
The next build contains the repaired handoff and publication retention logic.

October 1 publication diagnosis: NiFi's 14:42 UTC and 15:14 UTC builds completed
all 2,917 stored game products and their season products, but both refused
publication because later graph promotions changed the global corpus hash.
The second build had 55 admission updates and five calculation updates. Thus
the old live pointer did not establish that these repairs had failed. The SQL
builder now fences each new graph read with the existing game writer lock,
rejects changed promotions and unfinished transactions at that read, and
publishes the validated captured inventory. Later promotions trigger the next
incremental update. No source validation, eligibility rule or metric completeness
requirement is removed. Five focused checks cover source drift, crash recovery,
incremental SQL reuse and mutual exclusion with the actual Windows NiFi lock.

October 1: the full-season HTTP response from
`20260930T162149Z-dashboard-5d417d3bf58b` has **5/19 populated cards**, restoring
Offensive Reach after the roster fix. All 2,429 regular-season games remain
present. Before today's presentation correction, Empty Games displayed 31
players although SQL contains 266 complete eligible player counts. The
[October 1 decision](../archive/design-records/count-leaderboard-minimums-2026-10-01/README.md)
removes appearance minimums from counts, including zero totals; rates and
averages retain their minimums. Dashboard cards and details share that rule.
After web deployment, both live endpoints return the same **266 Empty Games
players**, with `belowMinimum=0` and no PA or observation minimum. The remaining
446 incomplete player records are disclosed separately; 774 additional rostered
players have no eligible game observations, leaving 266 complete applicable
counts from the 1,486-player roster population.

The low population of rate leaderboards is primarily a coverage problem:
134 players already have at least 502 recorded PA, but 133 have one or more
incomplete Offensive Reach game records. Across all players, 476 have a
progress-evidence exclusion and 258 have an official-PA exclusion; these sets
overlap. These are missing-data exclusions, not failures to reach the PA minimum.

October 1 coverage diagnosis of the same published full-season SQL:

| Whole-game check | Admitted | Withheld or stale |
| --- | ---: | ---: |
| Official batting population | 2,281 | 148 |
| Runner resolutions | 2,421 | 8 |
| Pitch/count history | 413 | 2,016 |
| Runner boundaries | 506 | 1,923 |
| Scoring runs | 2,427 | 2 |
| Complete defensive population | 0 | 2,429 |

These are separate requirements, not one global resolved-game flag. In
particular, 1,540 boundary results and 2,391 defensive results report missing
or stale proofs; that does not establish absent MLB source evidence. Individual
PA/player checks can still support results where a whole-game check is withheld.
Offensive Reach's progress exclusions affect 1,227 regular-season games. The
stored diagnostics concentrate on unresolved contribution attribution and
incomplete same-play runner paths, rather than inadequate player participation.
A bounded 253-record RDF diagnostic found ordinary hit/award links missing
alongside error, balk and independent-advance cases; it was not a census and
must not be extrapolated into population totals or used as metric input.

The D1 additive worker crashed on legacy promotions without a previous
`defensiveAdmission` field. Commit `f821361` repairs that bookkeeping while
retaining current-census SHACL and every unrelated admission check. NiFi
subsequently completed games 822864 and 822918, adding 202 and 240 triples
respectively. These additions are not a claim of complete defensive populations
or newly published SQL results. The separate [counted-foul prefix fix](../archive/design-records/mlb-game-counted-foul-completion/prefix-repair-2026-10-01.md)
selects all four recorded missing strikes in the first blocked game, 822678,
and passes its focused checks, but its publication is pending the specific
hash-update approval requested after automatic approval review rejected it.

Historical September 30 check: **4/19 populated cards**, with all
2,429 regular-season games and their rosters present. Qualified players:
Help Without Advancing 4, Empty Games 23, Scoring History Length 17 and Run
Contributors 1. There are no complete league populations yet. The published
build is `20260930T132608Z-dashboard-df2d3cf08485`, using source commit `97d3e89`.

This is down from the 10:27 Eastern check's five cards. The earlier build
`20260929T231614Z-dashboard-ad4d4593c34f` had one qualified Offensive Reach
player, 678662. The new snapshot excludes that player because the K1 games
824301 and 824302 lacked refreshed individual PA checks at its input capture.
824301's current check already admits that player. In 824302, the newer repair
response had a different roster from the originally ingested source, so using
it as the whole roster witness excluded every player. The repair below restores
the original retained census as the witness, projecting only K1's accepted
compound-result expectation and rerunning existing SHACL. Publication of that
repair is still pending. The September 29 table is historical.

Published engineering repairs on September 30:

- Retained source censuses can drive the owning SHACL checks against existing
  promoted RDF after raw inputs and local exports are retired. Neither graph
  rebuilding nor source reacquisition is part of this refresh. Windows sidecar
  paths use one digest of both input identities to remain below MAX_PATH.
- **Defensive Acts** counts distinct supported acts, including overlap, and
  supplies PAQ-2.1's third comparison. The SQL migration recalculates these
  products from stored bindings while preserving unrelated game results.
- The accepted D1 named groundout pattern is implemented. NiFi completed its
  first additive repair, game 822693, with 208 new triples and no removed
  triples. The complete defensive population remains unresolved.
- Individually admitted PA runner resolutions now support that PA's
  contribution even when another resolution in the game is unresolved. The
  player projection updates affected SQL partitions without graph queries.
- K1 player checks now retain the original source roster and official PA
  census, with an explicitly recorded projection of the accepted compound
  result type. They do not substitute a later response's roster. Successful
  prior checks remain reusable; failed later-response roster checks receive
  a bounded refresh, prioritized before general runner-resolution maintenance.
- NiFi's [counted-foul repair](../sources/mlb-game/review/counted-foul-repair-2026-09-30.md)
  is enabled. It selects exact missing second-foul strikes from retained
  terminal reports and uses only five existing maps, starting with game 822678.
  Its focused RMLMapper test passed; deployment is not a live completion claim.

The two review integrations remain source-contract work. Rechecked against
[MLB's ABS definitions](https://baseballsavant.mlb.com/abs-metrics-documentation)
on September 30: legal challenge opportunities depend on an adverse called
pitch, available challenges and operational ABS, excluding position-player
pitching. Final counters alone cannot establish availability at every prior
decision. Existing pitch-subject extraction is therefore insufficient to admit
the complete separate review denominators; it is not evidence that the MLB
provider lacks those facts. Keep source and RDF coverage debt explicit.

Read-only selected-range checks on September 29, 2026:

| Surface | Recorded result |
| --- | --- |
| Published dashboard | `20260929T192606Z-dashboard-71b422a5da3e`, published September 29 at 16:02 Eastern, 2,917 games; paired release from `1d6a720` |
| Week selection (prior 11:16 publication) | September 21-27: all 90 expected regular-season games |
| Week player leaderboards (prior 11:16 publication) | **11/19 populated**, with names, selected-period aggregates, automatic minimums and disclosed exclusions; `ready=false` |
| Newly populated cards | Plate Appearance Contribution (20 qualified players), Runner Out Rate (19), Runner Loss per PA (19), Scoring Opportunity Lost (20) |
| Other populated cards | Offensive Reach (122), Help Without Advancing (122), Empty Games (142), Empty Game Damage (58, up from 6), Contribution Mix (2), Scoring History Length (163) and Run Contributors (130) |
| Expanded details | Scoring History Length has 163 named players for September 21-27, with Trea Turner and Jake Bauers among the leaders at an average of 4; 48 incomplete player records are explicitly excluded. The prior publication's full card/detail comparison matched all 163 rows. |
| Month selection | August 29-September 27: the live HTTP response succeeds in 7.86 seconds with **6/19 populated**. |
| Season selection | Prepared SQL covers all 2,429 expected regular-season games and verified rosters. The default full-season HTTP request now succeeds, initially in 8.23 seconds (1.72 seconds in the reader). **2/19 populated**: Empty Games (6 qualified players) and Scoring History Length (1). Loading works; the other 17 cards still lack qualified complete records. |
| Current detail and custom week checks | Full-season Scoring History Length detail succeeds in 2.60 seconds and matches Will Smith's dashboard value of 14/5. September 21-27 succeeds in 3.06 seconds with **11/19 populated**. |
| Season leader | Scoring History Length returns Will Smith at **14/5**, averaging 35 complete scoring histories; the automatic minimum is 33 runs. The dashboard and previously checked detail agree. |
| Latest full-season HTTP check | 4.48 seconds, all 2,429 expected games and verified rosters; **2/19 qualified cards**, `ready=false`. This publication predates the Help and Contribution Mix repairs and R1 additions. |
| Recent-game coverage | All 130 September 17-26 catch-up games are in SQL, including 823087 |

The prior full-season HTTP check returned 503 after 30 seconds. Its first pass
visited 1,656,447 metric rows, and its second pass read 523,359 aggregates,
including many zero-observation records. A player-by-all-games join amplified
that cost. The corrected range reader reduces coverage in SQL and uses one
membership-filtered aggregate scan. More importantly, NiFi now prepares each
season's default complete-range response before publication. Matching dashboard
and expanded-detail requests read that prepared result; arbitrary ranges retain
exact range aggregation. The cache is bound to the publication's input set and
exact reader/player code. It never fills unavailable metrics or alters minimums.
Focused checks preserve every metric's results and missing-game exclusions,
exercise dashboard/detail reuse without a range scan, reject stale publication
reuse, and preserve incremental game calculations. The 15:25 publication now
serves the default full-season response successfully from prepared SQL.

A manually selected March 25-September 27 range still hit the 30-second deadline
on that publication. Diagnosis found the production SQLite planner nesting all
7,773 eligible metric/player pairs under each of 2,429 games. The corrected
reader forces the existing player index first; its live read-only diagnostic
returned the same 10,055 aggregate rows in 8.66 seconds. Three focused comparisons
pass on the actual dashboard runtime. This custom-range correction awaits NiFi
reader deployment; the live default-season success does not certify it yet.
The next publisher also explicitly limits its integrity pragmas to the prepared
snapshot, avoiding an unintended scan of the attached working store. Neither
repair changes RML, RDF, metric meanings or qualification requirements.

The healthy SQL service and unavailable player populations are separate facts.
The current pointer is `state/serving/dashboard-current.json`; the independent
builder records progress in `state/serving/dashboard/progress.json`. Read those
owner records for a later state. Do not infer publication from a submitted job,
a source graph count or a successful component test.

The earlier 13:19 publication reused all 2,917 game calculations and refreshed
the affected player products. The seven previously
unverified rosters (824295, 823648, 823682, 823523, 824807, 823589 and 823668)
are now verified in published SQL. Several player/PA checks still fail; a complete
roster does not admit those players' metric records. Independent PA admission,
the compact snapshot, per-player damage isolation and the grouped reader are
live. Later reference-product changes still require their own NiFi publication;
do not infer their deployment from these results.

## Implemented repairs and retained component evidence

- Contribution Mix no longer excludes every player because one completed PA
  has an unresolved running episode. With an admitted full resolution census,
  uncertainty stays with that PA's batter and actual runners. Unknown identities
  retain the whole-roster fallback, and the affected people's channel counts
  remain withheld. Existing SQL contains 1,247 games with this broad exclusion.
  A read-only calculation for game 822679 repairs 52 player/game records,
  including Francisco Lindor's exact channel counts **[3, 1, 1]** and one
  independent running episode. This is a component result pending NiFi's next
  player projection, not a full-season qualification claim. Four focused
  regressions preserve affected-player exclusions, admission requirements,
  existing Help behavior and unchanged-partition reuse.

- The [R1 review](../archive/design-records/mlb-game-runner-pattern-completion/README.md)
  identifies 26 games and 2,023 candidate PAs whose existing SQL diagnostics
  show missing runner-pattern facts. Each game has a retained source input,
  pinned in the review inventory. R1 requests only absent facts from unchanged,
  already accepted runner mappings, with the existing RDF preserved. The user explicitly
  accepted R1 on September 29; this is not yet an executed repair or a new
  population count. W2 was
  limited to W1's intentional walks; it did not authorize these ordinary runner
  rows. K1's compound strikeout case remains a separate decision. SQL repairs
  over supported facts continue independently.
  The implemented source-owned R1 worker now reuses 27 unchanged maps and the
  existing additive transaction. Seven focused regressions pass; a read-only
  selection of the retained 823200 witness supplies 125 episodes and 19
  supported personal histories. NiFi must complete that first game before
  widening to the remaining 25. NiFi subsequently completed **10/26 games**,
  adding **11,588 triples**, with no failed terminal records at the check.
  The first game preserved all 37,640 base triples and added 1,420. The worker
  remains active; affected SQL publication is pending. These promotion counts
  do not change the last verified dashboard population reported above.

- Help Without Advancing no longer requires every other runner's contribution
  to be known when its binary answer is already certain. NiFi reuses the same
  progress reducer on complete per-runner segments, retaining B1 and full/scoped
  PA resolution admission. Known batter progress excludes that PA from Help's
  denominator; known teammate help with a known nonadvancing batter supplies a
  positive observation. Unknown eligibility remains withheld. This also permits
  certain non-empty classifications while leaving reach and TFS incomplete.
  The retained SQL case 823580 / PA 55 now gives Daulton Varsho a complete season
  Help average of **7/184** (14/368), with 526 official PAs and no missing Help
  games. Four focused checks cover the exact denominator, unresolved negatives,
  admission rejection, unchanged-partition reuse and publication round trips.
  The new player projection awaits NiFi; it does not yet change the live count
  of two qualified season cards. No source acquisition or RDF change is needed.

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
  These are source-owned checks over unchanged RDF. The 13:19 SQL publication
  includes the earlier scoped receipts; the season still has only two qualified cards. Other games remain wholly withheld. For example,
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
  short wait. The October 1 repair above replaces the final global source-change
  veto with per-game read locks and captured-version publication.
- NiFi recorded a transient Windows access denial replacing `progress.json`
  on the next attempt. Atomic serving metadata writes now retry short-lived
  sharing errors while preserving the previous complete file. Persistent
  failures still stop the operation. The diagnostic file watcher was stopped.

The complete earlier diagnosis and dated build history are retained in the
[September 23 history](../archive/operational-history/2026-09-23/METRIC-READINESS.md).
The [operational delivery record](../infra/OPERATIONS-IMPROVEMENTS.md) describes
worker ownership; [build reuse](BUILD-REUSE.md) describes invalidation.

## Remaining work after the September 29 selected-range check

The 15:00 Eastern live full-season request still timed out after 30 seconds;
the 14:03 SQL publication remained current. Its replacement was refreshing
inputs. The source snapshot alone took 597 seconds. A bounded inventory profile
found most sampled time in file opens, and the in-process hash cache reopened
even unchanged artifacts, discarded all entries when full, and did not survive
the next NiFi invocation. The SQL owner now retains those byte hashes with the
existing file-identity checks and bounded individual eviction. Focused tests
cover reuse, replacement, deletion, invalid caches and concurrent promotion.
This is a build-time optimization awaiting deployment, not evidence of a new
publication, faster live response or additional populated cards.

The admission worker's fallback previously depended on a retired local RDF
export even when a retained quarantined response and the promoted graph were
available. Its independent six-profile graph check was reached only as part of
the individual batting check. These are now separate execution paths: the
existing profiles can read the existing graph without repeating the batting
check, acquisition, RML or promotion. A September 29 diagnosis found 38 deferred
games with retained raw witnesses; this is a repair-candidate count, not 38
admissions. A spot check confirmed unchecked count/boundary/defense profiles in
822753 and 823302, while 822918 already had explicit withheld independent checks
that must not be retried as missing evidence. Focused regressions preserve
withheld outcomes, the separate source identities and the final promotion check.
NiFi exercised this path for 822753 at 14:44 Eastern: count, boundary and defense
remain explicitly withheld by their existing constraints. The retired export
no longer prevents that diagnosis; it did not supply missing facts. SQL consumes
the resulting receipts on its next update.

The same worker also prematurely treated a successful single stage as completion
of the entire game. A `refreshed` result now continues on the next bounded tick,
allowing batting, independent profile and individual-PA checks to finish in
dependency order. Completed checks are reused. The two-failure retry allowance
counts actual failures rather than memory deferrals or successful stages, and
resets for a newer promotion. Focused regressions exercise the complete handoff,
final quiescence, memory deferral and retry limits without running ingestion.

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
averages need the full relevant act/agent population. Defensive Acts counts
distinct acts, including overlap; it does not require chronological order.
The existing D1 contract admits selected performances, not all performances on
every contact play. Review player rates still need a reconciled mechanism,
affected-player census and (for dependence) eligible unreviewed outcomes. The
retained diagnostic review inventory is not that graph contract. These gaps
cannot be closed by converting unknowns to zero or by using a smaller percentile
reference. Any required RDF addition must be separately scoped to the missing
facts and reviewed under the existing RML/identity rules.

### Specific remaining batting, count and review evidence

The September 21-27 B1 conformance failures for games 823327 / PA 46,
823489 / PA 6, 824301 / PA 40, 824302 / PA 17 and 824866 / PA 42 share one
precise mismatch: the retained source census expects `StrikeoutProcess` for
`strikeout_double_play`, while the promoted result is typed only as
`BaseballInstitutionalProcess`. The existing B1 reports reject the result
membership and affected player's PA count. This is mapping coverage debt;
there is source evidence. It is not repaired by inventing a statistical PA
in SQL or typing a composite whole from one of its parts. Other interrupted
turns in those games remain distinct from official completed PAs.

The accepted [K1 repair](../archive/design-records/mlb-game-strikeout-double-play/README.md)
proposes the existing Double Play classification of the combined result with
its two existing Out Processes as process parts. The 823327 / PA 46 graph
already contains both out identities. K1 requests only the five named source
responses and selected additive RML facts because those raw inputs are retired.
The September 30 narrow-repair approval and targeted-acquisition answer authorize
implementation. The K1 selector, one-map RML delta, existing-referent SHACL,
five-game NiFi worker and corrected B1 Double Play expectation are implemented.
Four focused scope/identity checks and two retained-proof compatibility checks
pass. Unrelated completed evidence retains its original outcomes and producer
identities. Live graph additions and subsequent dashboard population are separate
delivery steps; these checks alone do not populate a card.

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

The [W1 selection package](../archive/design-records/mlb-game-zero-pitch-walk-prefix/README.md)
was explicitly accepted and pushed on September 29 before implementation.
The shared selector now accepts a verified count-neutral pinch-runner replacement
or mound visit before the four VB records. Game 822864 / PA 54 selects the batter's
one award joined to actual terminal index 5. A reconciled replacement witness
can be used while its zero-episode incoming personal history remains withheld.
Unknown prefixes, movement, count changes and unreconciled replacements fail.

NiFi's source-owned `Add Approved W1 Awards` worker runs the seven existing
award maps and four dependency maps accepted in W2, limited to the same selected
PA/runner/resolution identities. It posts missing triples into the existing game graph. It validates
the award's existing referents, preserves the base graph, and rebuilds only that
game's derived query index under the existing recoverable transaction. The
reviewed game runs first; bounded retained-input inventory then finds other W1
cases. No API acquisition, pitches, judgments, histories or whole-game RML rerun
is involved. Exact prior proof versions remain usable with their original
outcomes, graph/source hashes and validation artifacts. A new promotion requires
new checks. W1's initial attempt identified eight missing dependency triples.
The [W2 dependency package](../archive/design-records/mlb-game-w1-award-dependencies/README.md)
was explicitly accepted and pushed separately before implementation. On September
29 at **14:23 Eastern**, NiFi completed run `072c4ee30da64ee3aa04f9d0ab824798` for
game 822864 / PA 54 / runner row 0. Both selected-award and scoped authoritative
SHACL reports conform. It added exactly **23 triples: 15 award facts and eight
dependencies**, preserving all 27,823 base triples. The resulting graph has
27,846 triples and its refreshed query index has 7,757. The owning worker emitted
the promoted-game event for SQL; no subsequent SQL or leaderboard improvement
is claimed yet. Eight focused worker/selector checks passed. The retained
response supports the facts; this was mapping coverage debt. The failed staging
manifest is kept distinct from the original promoted graph/index identities.
The worker now scopes unchanged authoritative constraints to the selected facts;
it does not declare unrelated old counted-foul or stasis failures repaired.

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
| Defensive Acts | Implemented; population gated | Complete act/agent admission and independent roster proof; overlapping distinct acts count separately |
| Defenders Involved | Implemented; population gated | Complete act/agent admission and independent roster proof |
| Scoring History Length | Implemented conditionally | Every counted scoring history, source run/roster proof and selected schedule |
| Run Contributors | Implemented conditionally | Same complete scoring histories with supported contribution ownership |
| Replay Overturn Rate | Unfinished as a player producer | Pitch-review affected-player extraction and SQL retention implemented; other subjects, mechanisms, complete population and qualification remain |
| Outcomes Changed by Review | Unfinished | Complete eligible never-reviewed decisions, decision-time legal availability, operative outcomes, affected players and separate mechanisms |
| PAQ with Tie-Breakers | Implemented; defensive population gated | Admitted contribution, two-strike and defensive inputs; complete separate season references and selected participation |

The approved display remains a selected-period player average, except Empty
Games, which is a game count with no appearance minimum. Rate and average
batting qualification is 3.1 PA per team game,
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
