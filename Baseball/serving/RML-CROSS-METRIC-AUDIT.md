# Entire RML repair set: cross-metric audit

October 12, 2026. Expanded after the user clarified that the requested scope
was the entire RML repair set, not only Empty Games. Mapping/reader code is
unchanged from `27fdb3c6`; inventory was captured at `1ccaa23d`. This audit
changes no metric meanings, source scope, admissions or product code.

**The complete RML repair set supplies useful fact improvements for all nineteen
public metrics.** Seventeen have conditional player producers connected to those
facts. Both review metrics have relevant mapped/query evidence but unfinished
public player integration. This does not mean all nineteen are populated or
that every historical game has received every applicable repair.

The earlier “thirteen of eighteen” answer described only the Empty Games work.
It understated the broader reuse: counted-foul/count-award repairs support
Two-Strike Extension, D1 supports both defensive cards, and M2 supplies review
evidence for the review metrics. Those older repairs are included here.

## Entire executable mapping inventory

The [captured inventory](../benchmarks/metrics/rml-cross-metric-inventory-2026-10-12.json)
enumerates all seven registered source modules: **565 triple maps and 175
logical sources**. The MLB-game manifest covers all 417 unique game maps across
73 review patterns; none is unlisted and no listed name is absent. Some maps
participate in more than one pattern. This is a coverage inventory, not a new
semantic validation or a certificate of full provider-field coverage.

| Source module | Triple maps | Logical sources | Relationship to the nineteen metrics |
| --- | ---: | ---: | --- |
| MLB game | 417 | 126 | Direct source of the current metric evidence, game rosters, labels and schedule scope |
| MLB people | 45 | 17 | Separate Person authority, dispositions and measurements; current metric queries do not require this module |
| MLB venues | 34 | 8 | Separate venue/field authority; geometry and venue measurements are not inputs to these nineteen formulas |
| MLB transactions | 30 | 11 | Separate personnel/role-transition evidence; current metrics do not use transactions to infer game participation |
| MLB leagues | 21 | 6 | Separate league/season authority; current metric selection uses promoted game facts |
| MLB teams | 10 | 4 | Separate Team authority; current metric rosters/exposure come from game facts |
| MLB divisions | 8 | 3 | Separate Division authority; no direct scoring dependency |

The [source-scope catalog](../sparql/source-scope-catalog.json) explicitly makes
the metric evidence queries single-source `mlb-game`, followed by derived
calculation. The six other modules' repairs are useful to their own authority
products; treating them as prerequisites for these metrics would introduce an
unnecessary coupling. No rerun of those modules is recommended.

## How the full set of repairs carries through

This covers generic mapping/context corrections and their execution fixes, not
just the game IDs used as witnesses. Accepted decisions and current selectors
take precedence over historical future-tense descriptions in archived reviews.

| Repaired family | Reusable RDF or execution result | Metric reach and boundary |
| --- | --- | --- |
| Real act/result/record separation; swing versus bunt; completed versus administrative PA selection | Distinct actual acts, adjudicated results, source records and consistent PA inventory | Underlies all nineteen; nominal pitch/trajectory categories and deferred measurements are not new score inputs |
| Q4 actual batter participation, P1 actual pitcher participation, EG4 official PA decisions | Actual performers remain separate from official statistical credit; persistent roles are reused | Batting qualification, contribution/progress, count histories and affected review subjects; actual-pitcher repair is primarily identity correctness, not a new pitcher score |
| M1/M3/M4 and F4-F8 counted-foul repairs; Q5 automatic balls/strikes | Operative counted strikes and awards without inventing delivered pitches | Direct to Two-Strike Extension and the count dimension of PAQ with Tie-Breakers; count completeness and full references remain necessary |
| M2 affirmed reviews and reviewed-result identity corrections | Original/operative decisions, particular review acts and supported subjects; no duplicated counted result | Both review kernels and their subject extraction; does not supply the complete never-reviewed eligible population or public player integration |
| A1/B2 contact containment and continuation repairs | Exact contact-member resolutions, distinct from independent running episodes | Reach, Help, Mix, contribution/loss/erosion, Empty Games/damage, run contributors and contribution percentiles; membership alone is not positive credit |
| Origin/base-resolution links; W1-W5 intentional/ordinary/automatic walk and HBP awards; W2 dependencies | Explicit movement endpoints, actual award-to-act links and forced chains | Most offensive readers and scoring histories; unrelated advances remain separate and no blanket batting credit follows from a PA label |
| C1/C2 histories and boundaries, C3 anchors, H-series/H4 review selections, O1 overlaps, walk-off closure | Personal membership, replacement/placement anchors, termination and independently supported boundaries | Both run metrics, coalescence, contribution, erosion and situation-adjusted PAQ; placement adjudication is not a fabricated running act or physical occupancy assertion |
| PB/WP institutional attribution, BK1 balks, D2 defensive-indifference running, supported noncontact advances | Actual independent runner acts with final outcomes and adjudications | Mix, Empty Games, damage/contribution components and run contributors; no stolen-base statistic or batter benefit is inferred from independent advancement |
| K1 strikeout double plays and EG6 sacrifice-fly compounds | One accepted PA result with exact distinct out parts; canonical batting classification | Official PA counts, out/damage attribution, contribution ranks and Empty Games; strategy-dependent allocation still needs its accepted evidence |
| D1 named field/throw/catch/tag acts, compact groundout/relay corrections and local Q6 selection | Distinct supported performances, agents and persistent Fielder Roles survive independent source issues | Direct to Defensive Acts, Defenders Involved and defensive PAQ tie-breaker; a counted out or assist alone cannot certify all acts |
| EG5 primary/secondary error associations and explicit RBI decisions; EG6 refinements | Operative scoring classifications attached to exact affected records/resolutions | Direct to Empty Games; shared evidence is available to other offense readers, whose credit rules must be applied explicitly |
| T1 reversed-clock isolation and corrected terminal-event selection | Independently supported facts survive unreliable times; supported game endpoints are accurate | Avoids broad rejection across families; timing-dependent histories/count order remain withheld when timing is unsupported |
| Q6 incomplete-source and Q7 zero-episode isolation; scoped admission and proof compatibility | Local facts and valid prior proofs are preserved without relabeling missing totals or histories | All families benefit from narrower failure scope; an Empty Games proof cannot certify a numeric or complete defensive population |
| Execution snapshots, UTF-8 reads, optional adjudicator handling, retry/request identity, additive idempotency and retained quarantine evidence | Mapper inputs/outputs retain the correct identity, exact execution provenance and bounded recovery | Reliability across all seven modules; these fixes do not themselves calculate or populate a metric |

Evidence anchors: [mapping contract](../sources/mlb-game/mapping/README.md),
[M1-M4 implementation](../sources/mlb-game/review/metric-mapping-completion.md),
[D1 implementation](../sources/mlb-game/review/defensive-acts.md),
[broader repair/execution audit](../sources/mlb-game/review/rml-audit-2026-10-03.md),
and [exact compatibility records](../sources/mlb-game/pipeline/context-proof-compatibility.json).
The captured inventory also lists the 44 accepted `mlb-game-*` review records;
other shared decisions, such as C1/C2 and defensive act-count meaning, retain
their separate accepted records.

## What the retained serving evidence establishes

These are read-only counts from the same immutable, pre-EG6 publications used
for the UI baseline below. They are **whole-game admission counts**, not fresh
validations, numbers of broken mappings, or limits on individual player results.
Per-PA/player evidence can support additional results. Issue counts overlap.

| Admission product | Fully admitted games / 2,429 | Recorded remaining limits |
| --- | ---: | --- |
| Runner resolutions | 2,426 | Three source reconciliation/boundary cases |
| Scoring-run census | 2,427 | Two games with incomplete source totals/plays; this census alone does not complete every personal scoring history |
| Official batting PA census | 2,289 | 67 missing/stale proofs, 52 graph-conformance refusals, and source/result/participation cases |
| Pitch/count history | 1,741 | 240 missing/stale proofs; recorded termination, pitch order, count mapping and nonpitch-count issues |
| Runner start boundaries | 1,242 | Administrative-boundary/zero-episode/history/time cases, 227 missing/stale proofs and 24 graph-conformance refusals |
| Complete defensive game population | 0 | 669 missing/stale proofs; partial act inventories and graph-conformance refusals in the rest |

Defense is not empty RDF. Across **1,196 graph-conforming game proofs**, the
retained evidence reports **61,911 selected defensive acts** and **20,745
complete contact plays** out of **130,393 inventoried contact plays** in those
games. Of those game proofs, 1,194 also reconcile at the source level but still
withhold the whole-game population. Current serving requires that population
before building defensive player averages. The audit does not infer missing
provider evidence from this refusal or claim that the partial acts cover every
play. Inspect the exact unresolved play requirements before requesting more RML.

The source repair record also distinguishes correct promotion from subsequent
consumer admission. Missing/stale proofs must be handled in their owning
evidence layer; they are not evidence that RDF should be regenerated.

## Remaining broad-scope findings

### Implementation follow-through, October 12

These are published engineering changes, not claims of delivered population.
The active NiFi build captures its own immutable release; later commits enter a
subsequent publication.

- A1 is repaired in the final player projection: EG6 classifications replace
  the older PA positives, and Help cannot restore rejected error credit.
  Distinct supported steals and later contact advances do not acquire a new
  whole-PA history requirement merely because the binary reader is invoked.
- A3 is repaired in the shared progress, contribution and run-contributor
  readers. They consume the actual contact/award actor and collapse only
  identical physical movements. Recovery separately consumes official PA
  credit; that credit never transfers the underlying acts.
- Count admission recognizes delivered pitchouts, intentional balls,
  reconciled sacrifice-fly double plays and adjudicated catcher interference.
  Successful earlier proofs retain their original provenance. F9 remains
  pending, and these reader fixes do not supply missing mapped strikes.
- A failed check against a later revised source response no longer displaces
  the retained census for the source revision that produced the graph. The
  diagnosed 822678 PA 55 passes its existing boundary constraints with that
  original census and unchanged RDF.
- Complete per-PA boundary and resolution admissions can complete contribution
  inputs and their season references. A whole-game refusal no longer overrides
  an otherwise exhaustive set of successful scoped checks. Missing individual
  checks, count histories and defensive inputs still prevent completeness.
- Repeated metric arithmetic now reuses prepared SPARQL formulas. Text-query
  comparison covers exact fractions, large percentile inputs, nulls and
  independent concurrent populations. No scores or source facts are cached by
  this optimization.
- A complete no-out resolution census supplies zero out-driven erosion without
  requiring a positive progress weight. Excluded safe batting results likewise
  have zero contribution without an invented contact/award attribution;
  unresolved comparison states and channels remain unresolved.
- Runner Out Rate and Runner Loss per PA use their own prepared observations.
  Complete no-out turns still require known runner-on-base eligibility. A
  directly contact-attributed existing-runner out can establish occurrence
  without claiming its unknown path weight. The rate may resolve while the
  weighted loss remains withheld.
- Contribution Mix accepts a player's complete team offensive census. It still
  includes teammates' and interrupted turns, preserves running uncertainty and
  rejects the called-game Empty Games-only exception for numeric products.
- Player projection no longer repeats the contribution calculations already
  prepared in that same family build. Known no-out turns also retain zero
  independent damage without resolving their unknown positive running values.

A2's numerical error-step allocation awaits the explicit
[M1 decision](../proposals/metric-error-step-credit/README.md). A4 remains an
operating constraint. [P1's overlapping pitch intervals](../proposals/metric-count-overlapping-intervals/README.md)
also await a named decision. Defense, review populations and remaining history/count
coverage still have independent work. The detailed probes below are the dated
audit findings that motivated these changes, not a claim that fixed defects
remain in the current implementation.

Bounded follow-through also confirmed remaining graph/source gaps independently
of the SQL reader:

- In 824385 PA 35, the retained original B1 census expects the accepted compound
  Double Play classification. The promoted result has its institutional-process
  type and adjudication/record links, but lacks that classification. The player's
  official-PA check consequently fails. A different known positive can already
  settle Empty Games; it cannot supply that missing PA to an average.
- In 822685, scoring episode 17/2 and its Run Process exist, but the queried C1
  personal-history whole does not contain that episode. Retained raw inputs were
  not available for this game or the sampled 822732/822754 history gaps. These
  are not repaired by changing a SQL join or extending EG1's authorized inventory.
- The retained original 822753 response records PA 49's terminal ball from
  21:52:44.346 to 21:52:35.327 UTC. T1 correctly supplies neither invalid bound.
  C1 currently withholds the affected half's histories. Distinguishing missing
  internal timing from independently supported whole-history endpoints would
  require a concrete source-selection review; P1's overlapping-pitch proposal
  does not authorize using an inverted interval.

These examples identify generic ownership and evidence boundaries, not a new
game-by-game repair queue. The pending F9/M1/P1 decisions do not by themselves
certify all nineteen populations. Defensive act/agent completeness and review
mechanism/eligible-decision populations remain separate as described below.

1. **Count repairs help materially, but do not finish the two-strike population.**
   [F9](../proposals/mlb-game-counted-foul-edge-completion/README.md) remains an
   under-review, unimplemented selection package for five strikes in four
   games. It is not included in the implemented-fix total. Separately,
   the earlier `RECOVERY_BATTER_ASSIGNMENT` defect has been corrected by
   consuming EG4 official credit. None of this requires redoing successful F4-F8.
2. **Defensive mapping and complete defensive statistics are separate.** D1
   corrections feed the right four act types into the shared query, and the
   current metric counts distinct acts without requiring strict chronology.
   Complete act/agent coverage is still necessary. The source selector's
   local Q6 isolation does not yet make the serving whole-game gate local.
3. **Review mappings are reusable but do not implement review populations.**
   M2 supplies supported decisions and query subjects. The existing public
   player route still returns `REVIEW_PLAYER_POPULATION`; legal eligibility,
   never-reviewed decisions and mechanism separation remain distinct work.
   H-series review-neutral history repairs should not be mistaken for new
   original-call, review-mechanism or subject assertions.
4. **Coverage documentation has stale blanket statements.**
   `mapping-coverage.yaml` still lists `deferred.fielding_acts` broadly even
   though its execution-context inventory, executable D1 maps and current
   mapping README describe implemented subsets. Use exact accepted subsets;
   neither that old label nor a successful mapper run proves complete coverage.
   This audit leaves the source contract unchanged and records the discrepancy.
5. **Reader delivery must be measured separately from RML success.** A1/A3
   are implemented; A2 and the remaining A5 populations stay open. The next
   published player products determine the actual population gain.

The full-scope recommendation is to consume the existing repaired RDF through
metric-specific readers, refresh only affected evidence/derived products, and
group actual remaining source gaps by generic selector. Do not replace the
RML, expand the Empty Games repair queue into an unauthorized corpus run, or
make all seven source modules prerequisites for the dashboard.

## Empty Games and EG6 sub-audit

The findings below retain the initial bounded reader probes and all nineteen
baseline card counts. **Their reuse column describes the Empty Games/EG6 fixes
only**, not the broader mapping repairs documented above. In that narrower
scope, thirteen other metrics benefit substantially, Two-Strike Extension has
a limited census benefit, and the four defense/review metrics need their own
already-described mapping and serving work.

## Evidence and limits

- Traced source selection, SPARQL, calculation readers, prepared player products,
  publication and the public dashboard response for all nineteen metrics.
- Captured the [prepared full-season dashboard summary](../benchmarks/metrics/empty-game-cross-metric-audit-2026-10-12.json)
  at 13:15 UTC: all 2,429 regular-season games present; five populated
  leaderboards and no complete metric population. Empty Games has 631 of 662
  eligible hitters. These family releases **predate EG6 implementation**;
  their counts are a baseline, not measured EG6 gains.
- Exercised bounded synthetic cases through actual calculation functions using
  existing fixture builders. These establish reader behavior, not source
  admission or the number of affected live players.
- Checked the 33-game retained pre-EG6 diagnostic sample for completed progress
  positives contradicted by the new scoring reader; found none. Newly added
  contact/error memberships were not in that sample. It cannot establish the
  absence of the reproduced defect after those additions.
- Read existing published SQL. No API reacquisition, RML rerun, RDF modification,
  season recalculation or new validation gate was part of this audit.

## Reuse by metric

“Qualified” is the count of ranked player rows returned by the full-season API,
before the UI takes its top five. Empty Games has no appearance minimum.

| Public metric | Qualified baseline | Reusable work | Remaining dependency or reader work |
| --- | ---: | --- | --- |
| Empty Games | 631 | Direct target: eligibility, binary credit, actual actor, scoped census and additions | Correct conflicting-reader integration below; publish and measure completed repairs |
| Offensive Reach | 3 | Contact membership, personal paths and actual contact identity | Older progress reader ignores error-step decisions and rejects multiple batters |
| Help Without Advancing | 10 | Same progress inputs; existing projection isolates relevant runners | Binary-help fallback calls that same older progress reader |
| Contribution Mix | 0 | Independent advances and separate channels | Older attribution; whole-game resolution admission still required |
| Plate Appearance Contribution | 0 | Outcomes, contact paths, awards, endpoints and PA census | Numeric attribution/boundary reader; error-step and substituted-actor alignment |
| Runner Out Rate | 0 | Same inputs, including contact-linked terminal outs | Still depends on the complete numeric contribution record |
| Runner Loss per PA | 0 | Exact existing-runner outs and starting bases | Same shared contribution dependency |
| Scoring Opportunity Lost | 0 | Actual end states, independent scoring and stranding | Attributed outs and relevant boundaries, beyond binary positive evidence |
| Empty Game Damage | 0 | Directly reuses Empty Games classification and negative outcomes | Complete negative PA values and applicable independent-running damage |
| Scoring History Length | 196 | C1 membership and endpoints; already tolerates duplicate batter joins | Complete scoring histories and scoring-run census |
| Run Contributors | 10 | Same histories, independent running and actual actor evidence | Still uses generic PA batter bindings; substituted joins and error attribution |
| Plate Appearance Quality | 0 | Corrected contributions enter season reference | Complete accepted season reference |
| Situation-Adjusted PAQ | 0 | Same contributions plus runner boundaries | Immediate comparison states and complete reference |
| PAQ with Tie-Breakers | 0 | Contribution component and official PA census | Applicable two-strike/defensive components and its own reference |
| Two-Strike Extension Rank | 0 | Limited: PA census and canonical compound result | EG6 adds no pitch/count history; complete reference remains separate |
| Defensive Acts | 0 | Shared operational isolation and roster bookkeeping | Complete defensive-act inventory and player population are separate |
| Defenders Involved | 0 | Same operational benefit | Complete supported defensive agents and player population |
| Replay Overturn Rate | 0 | Shared publication/SQL infrastructure | Public player integration remains unfinished |
| Outcomes Changed by Review | 0 | Shared publication/SQL infrastructure | Integration and eligible-decision populations per mechanism |

The thirteen substantive reuse cases are the rows from Offensive Reach through
PAQ with Tie-Breakers. Two-Strike Extension is the limited case. The last four
need separate metric work. Backend-only Roles Played is outside the public 19.

## Findings

### A1 — High: final Empty Games projection can restore rejected credit

`player_ranges.empty_scoring_inputs` correctly rejects an adjudicated error
step under EG6A. But `project` first accepts positives from
`metric_suite.batting_progress_evidence`, then unions the new reader's positives
into them. A new zero cannot remove an old false positive.

Bounded reproduction: an eligible batter makes a contact out; another runner
advances second to third on an explicitly adjudicated error in that contact
play; no RBI or other positive exists. The real calculation functions return:

| Stage | Observed result |
| --- | --- |
| General progress | `reach=1`, positive `batter_other` channel |
| EG6 binary scoring | No positive or possible-positive players |
| Final Empty Games player record | Complete, `count=0`; EG6A requires `count=1` for this fixture |

This is a confirmed integration defect, not another semantic decision. It also
affects Empty Game Damage eligibility. Correct attribution per PA/step; preserve
independent positives in other PAs and explicit eligible RBI. A player-wide
subtraction would be wrong. The binary-help fallback must not restore the same
rejected credit through a second route.

Owners: [player_ranges.py](player_ranges.py), `empty_scoring_inputs`,
`binary_help_inputs`, `project`; [metric_suite.py](metric_suite.py),
`batting_progress_evidence`.

### A2 — High: physical contact membership is still used as analytical credit

EG6C correctly adds complete contact membership, including error-classified
segments. Several readers treat the contact link as positive attribution without
consuming `secondaryError`, `errorJudgment` or `errorDecision`:

- `batting_progress_evidence`: Reach, Help and Contribution Mix.
- `contribution_game_inputs`: contribution, runner-loss/opportunity values,
  damage inputs and contribution-based percentiles.
- `run_construction_evidence` for breadth: contributor ownership.

A bounded numeric probe accepts the error-classified second-to-third step with
`creditProgress=True`; its full PA score is `-1/12`. Thus the numeric consumer
has not adopted EG6A. EG6A approved an **Empty Games binary** rule and no numeric
weights. This audit does not silently extend it to every metric or invent a
replacement numeric value.

Reconcile these consumers with their accepted policies before claiming that
newly populated values are correct. Reuse physical state, adjudication and actor
extraction; preserve each metric's attribution/magnitude rules. Do not remove
correct RDF contact membership to work around an analytical reader.

### A3 — Medium: actual-batter evidence stops at Empty Games

The [movement query](../sparql/metrics/runner-movement-evidence.rq) supplies
`contactBatter` from the actual swing/bunt and contact. EG6 consumes it; older
progress, contribution and breadth readers do not.

For a bounded substituted-turn example with two actual batter bindings and an
explicit contact owner, Empty Games identifies the replacement's positive.
General progress returns `AMBIGUOUS_BATTING_CONTRIBUTOR`. Scoring History Length
computes one episode, while Run Contributors returns `CONFLICTING_SEGMENT_STATE`
for the same physical scoring history.

Separate official PA credit, actual contact/award ownership and physical runner
state. Collapse only genuine join duplicates. Do not ask RML to repeat an actor
assertion already returned by the query, or transfer an act to the officially
credited player merely to obtain one player per PA.

### A4 — High for planning: the repair queue is not an all-metric inventory

Generic selectors live in the ordinary source context for matching future
games. Historical repair discovery intentionally iterates the approved EG
inventory and selects only still-excluded Empty Games players. A game with a
known positive for every hitter can leave that queue while exact contribution
or another metric remains unresolved.

**Zero Empty Games exclusions cannot certify all legacy mappings or metric
inputs.** Diagnose each family's existing prepared unresolved products by shared
reader/selector cause. Read RDF first; preserve each source repair's authorized
scope. This audit does not expand EG1 into a season-wide RML run.

Owner: [targeted-empty-game-addition.py](../sources/mlb-game/pipeline/targeted-empty-game-addition.py),
`outstanding` and `repair_plan`.

### A5 — Completeness remains more broadly coupled in other readers

Empty Games can use a known positive to prove “not empty” and can use scoped
resolution evidence. These shortcuts cannot substitute for complete averages:

- Contribution Mix still requires the admitted whole-game resolution census.
- All four contribution-based player measures require complete contribution
  inputs; Runner Out Rate has no separate minimal out-only projection.
- Defensive construction starts from a whole-game admission; a failed game
  input can exclude its entire roster. Zero displayed defenders does not by
  itself establish absent API evidence. Defensive evidence diagnosis is a
  separate task from this dependency audit.
- All four percentile products require their complete accepted references.
  The captured SQL has only a one-game recovery reference through March 25,
  which cannot serve the full selected season; PAQ reference products are
  absent from the captured offense/combined publications.
- The public range query explicitly returns `REVIEW_PLAYER_POPULATION` for
  both review metrics. Offensive repairs cannot finish that integration.

Reuse the engineering pattern of isolating a metric's supported required
observations. Diagnose the actual failing input/admission first; do not weaken
completeness or introduce another global gate. Owners: `project`,
`contribution_game_inputs`, `defensive_game_inputs`, `season_rank_players`,
and [player_range_query.py](player_range_query.py).

## Confirmed reusable boundaries

- C1 histories, B2 membership, independent-running types, award links, scoring
  decisions and PA census corrections remain shared RDF facts. No new object
  properties are needed to consume them.
- Sacrifice-fly double-play canonicalization does not inherently lose an out.
  A bounded complete-contact probe returns two attributed outs, one existing
  runner out and contribution `5/12`. The separate noncontact strategy branch
  is not evidence of a regression. Source cases still need normal admission.
- Called-final `emptyGameStatus` does not upgrade general resolution admission.
  Numeric readers still require ordinary admitted status. Damage may reuse
  Empty Games eligibility but still needs numeric inputs.
- EG3's uncaught-third-strike home entry is a binary running positive. It does
  not establish a numeric weight or automatically settle channel metrics.
- Independent family publication and reuse of unchanged query answers apply
  across families. Changed RDF is re-queried; retained answers keep original
  query provenance. These improvements do not certify complete scores.
- Keep settled minima: every eligible Empty Games count, including zero;
  participation minima for rates/averages and other applicable measures.

`rankingCoverage.completePlayers` includes roster records with no applicable
observation. It is not a scored/qualified hitter count. The captured contribution
response has 878 complete roster records but only 54 actual player results and
zero qualified rows. Report scored and qualified counts for delivery progress.

## Recommended execution order

1. Correct A1 in the final Empty Games projector and exercise that final record,
   including an independent positive in another PA. Keep Empty Games primary.
2. Address A2/A3 in shared readers before claiming cross-metric correctness.
   Separate physical paths, actual actors and metric-specific credit rather
   than introducing another set of per-card repair functions.
3. Use metric-scoped inputs where justified for progress, contribution and
   histories. Diagnose their remainders independently of the Empty Games queue.
4. Prepare full-season percentile references when their inputs are complete.
   Keep two-strike work independent of defense; retain the combined metric's
   real defensive dependency.
5. Complete defensive and review work through their existing separate owners.

NiFi owns targeted execution and derived publication. Completion means correct
named-player results in full-season and selected-range UI responses. No reliable
additional-player forecast is possible before those publications exist.
