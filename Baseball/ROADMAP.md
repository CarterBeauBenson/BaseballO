# BaseballO roadmap

This is the ordered continuation plan. Current metric gaps and the last verified
publication are in [metric readiness](serving/METRIC-READINESS.md). Runtime
queues and build progress belong to NiFi's owner records, not this work queue.
The [previous roadmap](archive/operational-history/2026-09-23/ROADMAP.md) is
retained as history; its completed setup tasks and superseded design questions
are not instructions to repeat that work.

## Fixed architecture and scope

```text
Authorized source ingestion: API -> RML -> source SHACL -> authoritative Fuseki
Metric serving: existing RDF -> SPARQL and calculations in NiFi -> prepared SQL -> UI
```

Authoritative RDF is persistent. Reviewed game query indexes and SQL products
are derived and replaceable. Seven detachable MLB source modules own acquisition,
validation, promotion, retry, quarantine and provenance. Cross-source work begins
at the triple store. The dashboard's SQL owner is independent of source ingestion,
the legacy report builder and authority SQL.

On October 9 the user approved [independent offense and defense publication](archive/design-records/dashboard-offense-defense-isolation/README.md).
The same Dashboard SQL owner now schedules offense, defense, combined metrics
and other metrics separately, sharing the existing working store and memory
lease. Each family publishes an immutable prepared snapshot; the dashboard
combines those snapshots with their own freshness. A defensive exception does
not roll back, delay, or relabel offensive results. Actual runner outcomes remain
offensive dependencies, and this isolation does not resolve pending EG2–EG5
decisions or count previously incomplete players as complete.

Metric, performance and UI work starts from existing promoted RDF. A missing
input is a precisely recorded gap. An approved source addition preserves unrelated
RDF; a full RDF rebuild requires explicit authorization. The September 17 batch's
permission is not a standing rebuild instruction.

## 1. Complete the nineteen metrics: execution plan

Updated October 8, 2026. Empty Games is the sole primary delivery milestone
until its complete player population reaches the UI. The execution sequence
below replaces the earlier immediate-work list; prior versions remain in Git.
[Metric readiness](serving/METRIC-READINESS.md) retains
publication measurements. [The gap register](sparql/metrics/gap-register.json),
accepted decisions, and the presentation/qualification contracts retain the
metric meanings. This update changes the plan, not runtime behavior or semantics.

### Starting point and finish line

| Layer | Last observed state | What this establishes |
| --- | --- | --- |
| Promoted RDF | 2,454 active games; the published 2026 regular-season selection contains all 2,429 games | Game presence does not establish complete player classifications |
| NiFi repairs, October 9 at 03:35 UTC | Game 823412's D2 dependency repair completed with two added triples | A successful repair receipt does not establish complete metric attribution |
| Dashboard build, October 9 at 19:17 UTC | `20261009T190302Z-dashboard-offense-27ccb0b5` published | All four families now have independent publications |
| Published dashboard, October 9 at 15:17 Eastern | 520 complete Empty Games players, 142 incomplete; 153 unresolved player-games across 139 games | Unchanged from the 12:14 UTC publication; zero is still the finish line |
| Integration | Seventeen conditional player producers; two unfinished review player integrations | Finishing the repair queue alone cannot finish all nineteen cards |

The finish line is **nineteen working public metrics over the complete applicable
full-season populations**, with automatic top fives, player names, correct
selected-range values and usable full rankings/details. Every applicable
observation must be accounted for. Known zero, inapplicable, no qualifiers and
unknown are different states. A real empty qualifying population needs evidence;
placeholders or smaller passing subsets do not satisfy completion.

Preserve the settled presentation:

- Default to the full regular season; respect an explicitly selected date range.
- Pool accepted observation sums and denominators for period averages/rates.
  Empty Games is a count, with every eligible player's supported total, including
  zero, and no appearance minimum. Do not average game averages.
- Batting averages/rates retain the nearest whole-number 3.1 PA per team game
  minimum; other metrics use [their accepted participation policies](web/leaderboard-qualification.json).
  Apply qualification to complete selected-range exposure, including team changes.
- Contribution Mix retains its pooled channel calculation. Exact arithmetic is
  rounded only for display where applicable; its logarithmic entropy is approximate.
- Percentile displays are 0-100 and use the complete eligible selected-season
  regular-season reference through the reporting cutoff, not the displayed subset.
- Traditional replay and ball/strike challenges stay separate. Role Realization
  Breadth stays backend-only; the public target is nineteen cards.

### Delivery order

**Empty Games is the first end-to-end milestone.** Finish its eligibility,
classification, prepared SQL and live card/details before making another metric
the primary delivery task. While NiFi executes that work, independent engineering
on the remaining families can proceed. Do not turn a healthy queue into a reason
to stop work or make all nineteen wait for a season-wide audit.

| Milestone | Work | User-visible exit | Dependencies |
| --- | --- | --- | --- |
| 1. Empty Games | M0-M2 and M9 | All eligible players, including zero totals, appear with correct full-season counts and matching details | Its own eligibility/classification evidence; no exact PA total needed just to establish positive eligibility |
| 2. Other progress metrics | M2 and M9 | Offensive Reach, Help Without Advancing and Contribution Mix populated | Complete metric-specific PA/channel inputs and applicable qualification |
| 3. Contribution and damage | M3 and M9 | Plate Appearance Contribution, Runner Out Rate, Runner Loss per PA, Scoring Opportunity Lost and Empty Game Damage populated | Supported boundaries, outcomes and attribution; damage additionally needs Empty Game classification |
| 4. Scoring histories | M4 and M9 | Scoring History Length and Run Contributors populated | Supported personal scoring histories; breadth additionally needs contributors |
| 5. Standalone percentile families | M5, applicable M8 and M9 | Plate Appearance Quality, Situation-Adjusted PAQ and Two-Strike Extension Rank populated | First two need contribution inputs; extension needs count histories and can finish independently |
| 6. Defensive family | M6, remaining M8 and M9 | Defensive Acts, Defenders Involved and PAQ with Tie-Breakers populated | Tie-breakers additionally need contribution and two-strike inputs |
| 7. Review family | M7 and M9 | Replay Overturn Rate and Outcomes Changed by Review populated, with separate mechanisms | Player-linked review/decision populations; independent of contribution and defense |
| 8. Complete dashboard | M9 across all nineteen | Full-season and custom-range cards, rankings and details agree and respond promptly | All seven family milestones delivered |

Milestones 4, the extension part of 5, 6 and 7 have independent engineering
paths. Their placement is delivery priority, not a dependency on unrelated
families. Publish each supported improvement through the existing owner; partial
publication is progress, while the affected milestone remains open. Keep the
existing single heavy-worker lease and memory reserve: this plan does not add
parallel heavy processes or change the ingestion topology.

### Empty Games: complete population execution plan

Deliver one complete metric before switching the primary task. Empty Games
requires supported offensive eligibility and whether the player made any
accepted positive batting or independent-running contribution during that game.
Its public value is the number of eligible games classified as empty, including
a displayed total of zero. There is no PA minimum or rate denominator.

Use the existing source/admission owners, prepared player tables, dashboard
builder and UI. No new pipeline, database, aggregate validation gate or corpus
RDF rebuild is part of this plan. F9, defensive completeness, damage weights,
percentile references and review-card implementation are not prerequisites.
Fix a shared component only when an actual Empty Game exclusion depends on it.

**October 9 execution correction:** use the entire published remainder as the
work population and a shared defect/selector as the unit of implementation.
Fix and exercise each generic rule once, then let NiFi find every matching
authorized occurrence. Individual games are witnesses and execution batches,
not separate design tasks. Do not close a category from one successful example.
The existing dashboard owner emits the grouped remainder after publication;
the existing source owner caches a grouped work list for each publication and
implementation. This adds no validation gate or new pipeline topology.

The 19:17 UTC offense publication has 520 complete eligible players and 142 incomplete
players, spanning 153 player-games in 139 games. The entire approved existing-
pattern repair scope has been examined: 316 candidate games no longer contain
their original exclusions; 139 still do, and none currently has an unapplied
approved selector. This does not authorize rerunning those 139 games or treating
them as complete. Fix retained-reader dependencies independently; the prepared
EG2-EG5 source/meaning decisions were explicitly accepted on October 9;
implementation is now authorized through the existing owners.

**Approved implementation sequence (October 9):** EG3 binary running entry;
EG2 generic selection repairs (both implemented, NiFi publication pending);
EG4 official PA decisions; EG5 secondary error
and RBI decisions. Add focused regressions for each shared pattern, refresh
only its semantic pins, and publish the implementation. The existing EG1 owner
reopens matching unresolved player-games on its implementation fingerprint;
NiFi validates and promotes additions, then refreshes the affected offensive
products. Keep independent publication active and preserve all unrelated RDF.

| Order | Work and existing owner | Exit evidence |
| --- | --- | --- |
| EG-A. Publish the work already completed | Let the running Dashboard SQL build finish without restarting it. Read its full-season Empty Games result and compare excluded player/game identities with the October 6 baseline. Use current NiFi receipts to distinguish an unfixed case from a fix absent from the captured build. | New published build ID; displayed/excluded players; unresolved eligibility/classification counts and affected games. The old 879-row list is replaced by the new exact remainder. |
| EG-B. Finish eligibility | Admission evidence and `player_ranges.py:qualification/project`: consume current individual PA checks; repair stale handoffs and substitution/compound-result joins by shared cause. A verified eligible PA establishes positive eligibility without an exact PA total. A verified zero-PA game is ineligible. Unknown credit remains distinct from both. | Zero `OFFENSIVE_ELIGIBILITY` rows in the selected season. Each player's expected game membership agrees with independently established eligibility, including low-appearance players and team changes. |
| EG-C. Finish classification | Follow each remaining exclusion through existing RDF, attribution/movement SPARQL, retained SQL bindings and `player_ranges.py:project`. Correct missing joins or overbroad dependencies before selecting any source repair. One supported positive proves non-empty; proving empty requires the complete applicable batting and running inventory. Review `progress_census`, `empty_population` and resolution checks where an unrelated play still blocks a player. | Every eligible player-game is explicitly empty or non-empty; zero `COMPLETE_EMPTY_GAME_CLASSIFICATION` rows. Unresolved running in another batter's PA cannot be silently omitted, and an unrelated player's gap cannot erase a supported positive. |
| EG-D. Close actual missing-fact cases | NiFi's existing EG1 owner applies accepted BK1/W4/D2/W5 selections, skips cases resolved by the reader, retries repaired execution failures and adds only authorized missing facts/dependencies. Use the cases below, then group the exact remainder by cause. Preserve successful proofs and unrelated RDF. | Each affected case either disappears from the published exclusion set or has one precise remaining semantic/source issue. A successful or `already-present` worker receipt alone does not close it. |
| EG-E. Publish the corrected counts incrementally | The admission owner completes each repaired game's existing checks; Dashboard SQL refreshes its affected inputs/player products and dependent prepared ranges. Reuse compatible products. Where a shared calculation fingerprint or stage makes Empty Games wait for unrelated metric work, isolate that dependency within the existing builder. | Published SQL accounts for every expected eligible player-game exactly once; period counts are sums of those classifications. New receipts actually appear in the published snapshot. |
| EG-F. Deliver and verify the card and ranking | The live API and UI automatically load the full regular season, show named top-five results and open every eligible player's ranking/details. Exercise a short range, a custom cross-month range and an empty range using existing focused coverage. | Card, expanded ranking and details use the same build/range and agree with SQL. Zero totals and low-appearance players remain present, with no batting minimum applied. |

EG-B through EG-D are related work queues, not three season-wide passes. Finish
each shared cause across all affected cases, hand those games to the existing
owner, and continue independent causes while NiFi runs. EG-E is repeated after
productive batches; it is not held until the whole repair-status report clears.
The shared heavy-worker lease and memory reserve stay in place. Inspect NiFi
at a publication or recorded failure, not by continuously polling healthy work.

The latest measured publication and subsequent fixes are recorded in
[metric readiness](serving/METRIC-READINESS.md#latest-measured-publication-october-9-at-1517-eastern).
NiFi refreshes these reader corrections from retained bindings without source
work or unrelated metric recalculation. Keep a running snapshot intact and
collect later changes in its next incremental publication; a code commit is
not delivered coverage.

Current remainder, grouped by cause:

| Case | Current diagnosis | Next action and closure condition |
| --- | --- | --- |
| SQL attribution and proof compatibility | Published fixes preserve admitted PA scopes, known positives across complete safe paths, and accepted exclusions in interference and substituted turns | NiFi refreshes affected retained products; verify the exact remaining player-games in published SQL. Do not repeat their source work. |
| Defensive indifference | 82 unresolved selected PAs contained these advances; [D2](archive/design-records/mlb-game-defensive-indifference-running/README.md) is accepted and implemented | NiFi applies targeted type additions and refreshes derived products. Verify the resulting player coverage; this diagnostic PA count is not a promised player gain. |
| Walks after reconciled reviews | [W5](archive/design-records/mlb-game-walk-after-reconciled-review/README.md) is accepted and implemented; 822714 received ten missing triples without removals | NiFi reopens matching still-excluded cases, completes admission and refreshes SQL. Confirm those players in the next publication. |
| Eight eligibility records | 822729/609280 has an unselected reviewed compound result; seven other identities involve substituted batting participation | EG2c and EG4 accepted October 9; implement official-credit and compound selection. Preserve actual participation; do not assign earlier acts to the replacement. Identities are in metric readiness. |
| Three `forced_balk` PAs | BK1 explicitly excludes this source code | Prepared EG2e selects only explicit disengagement violations using the existing balk pattern; accepted October 9; implementation pending. |
| Uncaught third strikes with WP/PB entry | Structured attribution exists, but first-base entry credit remains distinct from the occupied-base running weights | EG3 accepted October 9 for binary running credit only, without a batting benefit or scalar weight. |
| 822688, PA 67 | The sacrifice fly has a runner-level RBI credit for Conine; other error advances have no RBI credit | Prepared EG5b proposes a distinct scoring decision and binary credit under the existing result exclusions. Accepted October 9; implement the graph pattern before the SQL reader can use it. |
| Remaining error/contact/award paths | Source witnesses distinguish pickoff/throwing errors, interrupted contact plays and reviewed HBP awards | EG2a/d and EG5 accepted October 9; implement generic selectors and judgments. Existing accepted repairs remain with NiFi; avoid blanket reruns of successful EG1 cases. |

If an exact remaining case needs new semantics or falls outside named source
approval, prepare that concrete decision while continuing independent work.
Do not reopen settled minimums, classifications, attribution policy or ordinary
SHACL bookkeeping. Research source/rule uncertainty before asking the user.

**Empty Games is done only when:**

- All 2,429 expected 2026 regular-season games are accounted for at the current
  reporting cutoff, with complete schedule and roster coverage.
- The published result has zero unresolved eligibility rows, zero unresolved
  applicable classification rows and zero excluded players due to incomplete
  records. Its player population is marked complete.
- The ranking's player identities exactly match the established eligible
  population. Do not hardcode 281, 814, or any desired player total as the target;
  verified participation determines it. Players with no eligible games stay
  ineligible; eligible players with zero Empty Games remain visible.
- The full-season card and expanded ranking agree with the same SQL publication,
  including selected-range counts, zero values, ties and player names.
- Existing API/UI checks confirm automatic loading and range changes. Record
  first-load/warm timing against the existing five-/two-second targets; fix
  measured request overhead without delaying a correct coverage publication.

Record these outcomes in the existing [readiness document](serving/METRIC-READINESS.md).
Until then, milestone 1 remains open and is the next primary task on continuation.

The four counted-foul exceptions (823013, 823804, 824118 and 824744) have a prepared
[F9 repair](proposals/mlb-game-counted-foul-edge-completion/README.md) awaiting named
approval. They belong to the later count-history milestone; neither that review
nor the unfinished review metrics should hold this Empty Games plan open.

Already completed source work stays completed: the 849823/849825 replays,
823631's foul addition, W4's five-triple automatic-ball walk addition for 822834,
the selected history repairs, and the retired-input lifecycle correction. Inspect
their current handoffs if a consumer fails; do not rerun them merely because an
older roadmap said promotion was pending. Required source SHACL, the optional
processor deferral and all 05:00 acquisition schedules remain unchanged.

### M0. Find and repair the first failing component in each family

Trace the actual path from promoted RDF through SPARQL, bindings, calculation,
SQL, API and card. Review the path for each family as it is delivered; this is
part of the repair, not a new global validation gate. Existing queries may need
rewriting. Neither matching old SQL nor a generated kernel proves correctness.

| Component | Work to resolve in its existing owner |
| --- | --- |
| `sparql/metrics/suite-evidence.rq`; movement, attribution, location and pitch-count evidence queries | Correct source/graph scope, identities, optional joins, applicability and observation cardinality; no fixed IRI or game exceptions |
| `serving/metric_suite.py:evidence_query` and `normalize_bindings` | Confirm the executed query projects the needed fields, preserves unbound values and uses current promoted/indexed products |
| `scripts/generate_metric_suite.py`, generated metric kernels and runtime reducers | Match accepted equations, attribution, denominators, ties and exact arithmetic; repair the generator for generated-query changes |
| Existing admission handoff and build diagnostics | Separate an actual absent fact, obsolete proof, consumer defect and unpublished product; retain exact affected game/player/PA/run/decision identities |

Use recorded terminal evidence first. For an actual analytical defect, use a
small concrete promoted/retained example to follow referents -> bindings ->
inputs -> score. Fix joins that multiply or omit observations. Missing chronology
must not discard an accepted unordered count. Do not implement parallel semantic
validation in Python or infer completeness from the subset a query returned.

### M1-M6. Complete the existing player families

| Work | Existing component owners | Required repair and completion evidence |
| --- | --- | --- |
| M1. Eligibility and denominators | MLB admission evidence; `serving/player_ranges.py:qualification`; dashboard proof handoff | Read current individual/whole-game PA evidence. Preserve accepted substitutions and interrupted-turn decisions. Establish positive game eligibility separately from exact PA counts; exact counts remain required for affected rate denominators. Every applicable player-game has a supported disposition. |
| M2. Progress and channels | Attribution/movement SPARQL; `batting_progress_evidence`, `contact_progress_path`, `binary_help_inputs`; player projection | Resolve Empty Game classification and complete progress/channel inventories. A supported positive proves a game was not empty; absence of a positive requires the complete applicable inventory. Keep accepted error/FC exclusions, independent runner credit and one contribution per play/channel. Unknown progress is localized to affected players without shrinking their selected-range denominators. |
| M3. Contribution, outs and damage | Boundary/resolution owner; `runner_boundary_states`, `contribution_game_inputs`, `contribution_players` | Consume supported immediate origins, actual end states, operative outs and attribution. Use accepted overlap, placement/replacement, actual-end-state erosion and stranded-runner decisions. Include independent negative running once in Empty Game Damage. Do not infer a hit-and-run from a strikeout/caught-stealing pair alone. |
| M4. Scoring histories | Run SPARQL; personal-history reducers and player products | Account for every counted run and its personal history. Depth counts state-changing episodes; breadth counts distinct supported contributors including the scoring runner. An unknown contributor must not invalidate a known history length. |
| M5. Two-strike histories | Pitch/count SPARQL, count admission and recovery reducer | Consume current foul, review, substitution and automatic-count evidence. Separate non-applicable PAs from missing applicable histories. Count nonterminal extensions after the first two-strike state; do not invent timestamp order or require a physical pitch for an accepted adjudicated count change. |
| M6. Defense | Defensive admission, act/agent queries and player projection | Reconcile current D1/Q6 results with applicable full-population evidence. Count distinct field/throw/catch/tag acts and actual agents, once each at their accepted identity. Overlap is allowed; a catch also typed as fielding counts once. Defensive Acts does not require an ordered chain. Complete both defensive cards and the applicable PAQ tie-breaker input. |

For each family, diagnose source-proof compatibility before treating a withheld
whole-game status as missing RDF. Use supported scoped observations under their
accepted requirements. Correct SPARQL/SQL over existing facts first; genuinely
missing facts use only the already authorized additive scope that covers them.
A local successful addition does not certify an unrelated whole-game population.

### M7. Finish both review integrations

`player_ranges.py` and `player_range_query.py` still have a
`REVIEW_PLAYER_POPULATION` unavailable path. Existing `review_player_evidence`
and `summarize_review_players` reducers are not an end-to-end player product.

- Extract the reviewed decision/subject, affected player, mechanism, completion,
  initial and operative outcome from accepted RDF, including supported nonpitch
  subjects. The affected player is not automatically the challenger/final batter.
- Prepare Replay Overturn Rate from resolved reviews affecting that player.
  Prepare Outcomes Changed by Review from **all eligible decisions**, including
  never-reviewed ones, with supported decision-time eligibility and actual outcome
  dependence. The denominators are different; review occurrence is not reversal.
- Trace missing eligibility/availability fields through retained evidence before
  calling them source gaps. Research factual gaps using primary documentation;
  record any genuinely new semantic assumption for the user's decision.
- Persist player/game/mechanism numerators, denominators, applicability and
  unresolved counts. Wire both prepared readers, qualification, labels, card and
  detail routes. Keep traditional replay and ball/strike challenges separate.
- Replace the unavailable branches only once their producers supply supported
  results. Empty populations stay explicitly inapplicable/no qualifiers as
  justified; they must not be filled with invented zero rates.

### M8. Prepare all four season reference populations

| Metric | Required inputs | Delivery requirement |
| --- | --- | --- |
| Plate Appearance Quality | M1, M3 | Complete eligible season PA contributions and exact percentile ranks |
| Situation-Adjusted PAQ | M1, M3 and immediate base/out cohorts | Complete matching cohorts, accepted small-cohort behavior and exact ranks |
| Two-Strike Extension Rank | M1, M5 | Complete eligible two-strike population and extension ranks |
| PAQ with Tie-Breakers | M1, M3, M5, M6 | Complete separately applicable population; lexicographic contribution, recovery, then distinct defensive acts |

Owners: `serving/reference_products.py`, reference rank materialization and
Dashboard SQL. Prepare each reference as soon as its own inputs are complete.
Keep missing evidence, missing prepared products and a wrong cutoff/key distinct.
Use complete individual PA admissions where the existing contract supports them;
do not shrink the reference to passing games or the five displayed leaders.
NiFi stores ranks and player aggregation components for the season/cutoff.
Date-filter changes must not launch new season calculations.

### M9. Publish each family through SQL, API and the UI

M9 is part of every milestone, not work deferred until the last metric is coded.

| Layer / owner | Required result |
| --- | --- |
| `metric_blocks.py`, `player_ranges.py`, `reference_products.py` | Correct prepared game/player products, sums, observation counts, applicability, localized exclusions, and reference results |
| `scripts/pipeline/materialize-dashboard.py` and serving release owner | Incremental family/partition refresh; compatible immutable publication; failed candidates preserve the last usable pointer |
| `dashboard_display_label`, prepared ranges | Stored player names and correct full-season response; invalidate affected range caches when dependent inputs/calculations/references change |
| `player_range_query.py`, metric query builder and `web/server.mjs` | Overview and detail consume one compatible published snapshot; inclusive selected dates and exact aggregates agree; custom ranges use indexed filtering/lightweight pooling |
| `web/metrics.js` and presentation contracts | Automatic full-season load, nineteen cards, named top fives, full rankings on click, visible selected dates, values/units and understandable loading/error states |

Scope refreshes to their cause: extraction changes refresh affected bindings and
products; calculation changes reuse compatible retained bindings; proof/additive
RDF changes refresh their dependent products; label/UI changes preserve scoring.
A season-wide refresh of derived SQL does not authorize rebuilding season RDF.
No dashboard request may call SPARQL, reacquire source, reconstruct histories or
recalculate the season. Use existing tables/products rather than a second
serving implementation. Persist review mechanism data in the owning products.

The UI must refresh every card for the chosen range and prevent an old response
from overwriting a newer selection. Show the actual smaller population when
fewer than five qualify. Card selection opens all qualified players with matching
values, ties, dates, minimum/denominator explanation and existing download/detail
behavior. Counts retain zero totals and have no rate minimum. Keep role machinery
and repair implementation details out of the normal baseball-facing flow.

Use existing focused checks for the component changed and NiFi's existing stages.
At family publication, follow a corrected observation into published SQL and the
live response/detail; inspect browser behavior when its implementation changes.
At final delivery, exercise full season, a month/week, a custom cross-month range
and an empty range with existing browser/API smoke coverage. Include tied ranks,
team changes and zero versus unknown where relevant. No new aggregate gate or
GitHub validation pipeline is part of this roadmap.

Measure real first-load and warm responses. Retain the engineering targets of
at most five seconds first load and two seconds warm on this host; profile and
fix the measured bottleneck instead of raising a timeout. Record actual timings,
not just prepared-query timing. Correct partial publication must not wait for
unrelated performance optimization.

### Nineteen-card accountability

All rows remain open. "Partial" refers to the last recorded populated card,
not complete coverage; "no ranking" is not proof that its RDF is absent. All
rows include M0 diagnosis and M9 live delivery. Public names and IDs come from
[metric presentation](web/metric-presentation.json).

| Public metric | Stable ID | Published state | Work | Required selected-range result |
| --- | --- | --- | --- | --- |
| Empty Games | `empty-game-rate` | Partial | M1, M2 | Every eligible player's game count, including zero; no minimum |
| Offensive Reach | `offensive-reach` | Partial | M1, M2 | Average distinct credited runner histories per eligible PA |
| Help Without Advancing | `hidden-help-rate` | Partial | M1, M2 | Credited help rate among PAs with no batter progress |
| Contribution Mix | `contribution-path-diversity` | No ranking | M2 | Accepted diversity of pooled per-play channel counts |
| Plate Appearance Contribution | `tfs` | No ranking | M1, M3 | Mean accepted net contribution per PA |
| Runner Out Rate | `rally-kill-rate` | No ranking | M1, M3 | Rate among PAs starting with runners aboard |
| Runner Loss per PA | `rally-kill-severity` | No ranking | M1, M3 | Mean weighted existing-runner loss across applicable PAs, including zero-loss PAs |
| Scoring Opportunity Lost | `opportunity-erosion` | No ranking | M1, M3 | Mean attributed opportunity loss per eligible PA |
| Empty Game Damage | `empty-game-damage` | No ranking | M1, M2, M3 | Average complete damage per eligible Empty Game |
| Scoring History Length | `run-construction-depth` | Partial | M4 | Average state-changing episodes per scored run |
| Run Contributors | `run-construction-breadth` | Partial | M2 attribution, M4 | Average distinct supported contributors per scored run |
| Plate Appearance Quality | `paq-2` | No ranking | M1, M3, M8 | Average eligible PA percentiles from the complete season reference |
| Situation-Adjusted PAQ | `paq-a` | No ranking | M1, M3, M8 | Average eligible situation-adjusted PA percentiles |
| Two-Strike Extension Rank | `recovery-quality` | No ranking | M1, M5, M8 | Average eligible two-strike extension percentiles |
| Defensive Acts | `resolution-depth` | No ranking | M6 | Average distinct act count in complete plays where the player acted |
| Defenders Involved | `defender-breadth` | No ranking | M6 | Average distinct defender count in complete plays where the player acted |
| PAQ with Tie-Breakers | `paq-2.1` | No ranking | M1, M3, M5, M6, M8 | Average eligible lexicographic PA percentiles |
| Replay Overturn Rate | `adjudication-volatility` | Unfinished integration | M7 | Reversed/resolved player-linked reviews, separated by mechanism |
| Outcomes Changed by Review | `review-dependence-rate` | Unfinished integration | M7 | Review-dependent/eligible player-linked decisions, separated by mechanism |

### Progress, estimates and continuation

Update the existing readiness record after a publication with the build/code
identity, populated/complete card totals, complete and qualified player counts,
remaining applicable exclusions and their owners, and live range/detail results.
Use those outcomes to close the table above. Submitted jobs, passed unit tests,
repair counts and nonzero leaderboards are intermediate evidence only.

The earlier 18-30 hour estimate concerned queued repair processing, not full UI
delivery. Re-estimate from net remaining cases and the next published exclusion
counts; rechecks are not net progress. Do not attach a date to the full nineteen
until the remaining family defects and M7 integration work have been assessed.
One unsupported applicable observation keeps its metric and the overall goal
open, but must not stop independent supported products from publishing.

Proceed without another permission round on accepted SPARQL/SQL, operational
SHACL, proof consumption, incremental materialization and UI engineering. Reuse
named narrow RML approvals within their scope. New ontology terms, identity
policies or genuinely new semantic assumptions still require the user's named
decision; no new object properties. Preserve unrelated RDF, keep spring training,
exhibitions and WBC out of active work, and do not introduce a rebuild or a
raw-source-to-SQL shortcut. Publish completed engineering to `dev`, submit owning
NiFi work asynchronously and continue independent items.

## 2. Keep operation incremental and recoverable

The [September 24 skeptical review](serving/ARCHITECTURE-REVIEW.md) records the
repaired request-time RDF fallback, cross-product fallback and missing/corrupt
dashboard publication recovery. Its remaining engineering concerns are shared
report/dashboard imports and calculation fingerprints that invalidate more
game work than the changed metric requires. These are engineering boundaries,
not requests for new source ingestion or semantic review.

- Diagnose recorded source or serving failures from terminal evidence, repair
  their cause and use the owning bounded retry. Do not monitor healthy runs.
- Tune the existing current/repair/historical queue priorities and bounded
  workers from recorded timings and memory limits. Source SHACL already reuses
  one Jena load per game while retaining each profile's report.
- Keep dashboard, full-report, authority SQL, repository evidence and RDF recovery
  independent. Preserve the published product when its replacement fails.
- Complete the remaining recovery acceptance work in
  [production readiness](infra/PRODUCTION-READINESS.md) and
  [RDF recovery](infra/RDF-RECOVERY.md): real backup/export/restore evidence,
  recovery objectives and the remaining host/configuration recovery scope.
- Keep acquisition at 05:00 Eastern and the user-authorized 15-minute batch
  checker. NiFi owns the bounded repair timers; their recorded queue state,
  rather than an old roadmap snapshot, determines whether they have work.

The configured NiFi-port migration fix, shared provisioning helpers, authority
lock recovery and report checkpointing are implemented. Their old roadmap
entries are not open implementation tasks. See the
[operational delivery record](infra/OPERATIONS-IMPROVEMENTS.md).

## 3. Extend legacy Explorer SQL only when useful

The legacy Explorer is separate from `/metrics`. Its contract still admits
PAQ-1/Good At Bat and supporting options to SQL; other families retain their
existing SPARQL routes pending family-specific result equivalence.

- Complete a family's row, filter, aggregation and date-scope equivalence before
  admitting that family to SQL. Existing shared grains and all 56 static DSQ
  tables are implemented candidates, not universal route admission.
- Add fact-to-fact bridge modules only for a concrete supported question and
  prove its equivalence through the existing owner.
- Preserve RDF/SQL timing evidence at matching corpus fingerprints.
- Keep official date/game-type provenance explicit. Accepted season-phase RDF
  is already available as a fallback and consistency check; a wholly RDF-only
  historical classification still needs coverage/equivalence evidence.

## 4. Review source and ontology gaps independently

Use the single [proposal catalog](proposals/README.md) for remaining MLB field
coverage, temporal role histories and future-source decisions. Operationally
successful ingestion does not establish complete API mapping. Existing-field
coverage debt stays in its source lane; do not reacquire or remap a season
because a metric exposes one omitted case.

The ontologist owns classes, axioms, identity policies and genuinely new modeling
assumptions. New object properties are prohibited. Existing ontology curation
debt remains recorded in [governance](governance/README.md), including unresolved
structural findings; documentation cleanup does not settle those decisions.

Statcast's rejected implementation remains retired. Fresh field inventories and
review-only geometry/process-profile designs need explicit acceptance before a
new detachable module is implemented. Weather and travel/rest remain later,
separate source families.

## Working and publishing

Use `dev`, fetch before publishing, and commit and push completed in-scope work
under [AGENTS.md](../AGENTS.md). Git was reauthorized on September 8. Never push
directly to `main`, rewrite published history or restore GitHub validation
without explicit authorization.

Use only the smallest useful developer check for changed behavior. Documentation
changes require diff review and `git diff --check`. NiFi's separate Repository
Evidence observer owns aggregate validation. Continue independent authorized
work when a semantic gap blocks one source assertion; do not make the entire
project wait on it.
