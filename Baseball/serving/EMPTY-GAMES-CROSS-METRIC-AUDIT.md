# Empty Games fixes: cross-metric audit

October 12, 2026. Code inspected: `27fdb3c6`, including accepted EG6A/B/C and
the earlier Empty Games readers, targeted repairs and independent publications.
This audit changes no metric meanings, source scope, admissions or product code.

**Thirteen of the other eighteen public metrics can reuse substantial parts of
this work. One has a limited census benefit; four need separate metric work.**
Reuse does not establish completeness. The source repairs are more widely
applicable than the specialized Empty Games reader. Several consumers still
reject, or differently credit, the newly supported inputs.

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
