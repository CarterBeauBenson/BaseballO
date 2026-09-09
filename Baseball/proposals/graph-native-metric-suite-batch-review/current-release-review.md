# Current metric release review — 2026-09-09

**Answer update:** [the September 9 decisions](../../archive/design-records/metric-suite-gap-answers-2026-09-09/decision.json)
settle questions 1–6, 8 and 9. The subsequent
[continuity decision](../../archive/design-records/metric-suite-gap-answers-2026-09-09/continuity-decision.json)
settles question 7's verified complete-history evidence criterion. The user
subsequently accepted C1's personal Process and C2's analytical boundary
projection. All nine policy answers and C1/C2 are recorded; they do not
establish complete live evidence.

The [C1/C2 decision](../../archive/design-records/runner-continuity-boundary-projection/review.json)
is implemented in source SHACL, whole/episode evidence extraction, and an
admitted-history SPARQL boundary projection. The evidence query retains
existing episode, judgment, decision, origin-record and personal-whole IRIs
through SQL. The [source contract](../../sources/mlb-game/review/runner-continuity-source-contract.md)
records the first unpassed gate: verified complete real histories with
supported lifetime and evaluation boundaries. Current raw rows do not satisfy
that gate merely by being adjacent or marked complete.

The software request covers all 20 metric calculations, serving integration,
and one consolidated account of unresolved gaps. The formulas and routes are
implemented. **Complete-population results for nineteen metrics remain gated.**
TFS now exposes a bounded loaded Walk/HBP consequence, with real game 823016
producing exact 25/12. This does not admit a complete PA score or a reference
population. The [current serving contract](../../serving/METRIC-SUITE.md#first-live-award-consequence)
records that result and its limits. Per-game coverage identifies missing
bindings; a bounded refresh of the demonstration day and its prerequisite
proof has been submitted to NiFi. These are operational submissions, not
new semantic decisions or proof that the remaining evidence gaps are closed.
This document identifies the remaining work without reopening settled policy
or treating successful arithmetic as source admission.

The [live route audit](../../benchmarks/metric-suite-route-audit-2026-09-09.json)
exercises all 20 HTTP routes over 15 promoted games on 2026-08-25. Each response
includes coverage for 1,567 observed movement pairs. Adjudication Volatility is
13/23 over explicitly resolved mapped reviews; the other responses retain
their named blockers and null values. An empty selection returns zero evidence
rows and no score. These are real Explorer requests, not injected score inputs.

## Settled decisions that require no further vote

The [final award/origin decision](../../archive/design-records/runner-award-origin-final-decision/user-decision.md)
supersedes the withdrawn four-property and event-directive approaches.
Walk/HBP causation and applicable rule requirements, act-specific origin
designations, and batter metric HOME=0 are implemented. Game 566279 has passed
NiFi source SHACL and graph-pair promotion with these patterns. Origin evidence
does not require a preceding stasis or prove subsequent continuity.

The September 8 decisions also remain settled: exact arithmetic and 0–100
midranks; the season/cutoff target population; actual-end-state erosion;
stranded-runner erosion on the third out; error/FC progress exclusion;
independent running credited to the runner; one positive play per channel;
one-PA Empty Game eligibility; four defensive acts in the stated example;
personal trajectories ending on score, out, replacement or inning end; both
offensive contributors in the run-construction example; four realized role
kinds; and separate PAQ-2.1 applicability handling.

No new object property, replacement index predicate, ontology class, axiom,
or identity policy is proposed or approved by this review. Existing pinned
review artifacts remain historical evidence. Their obsolete relation examples
must be read with the final correction above.

## Seven remaining work packages

These are shared dependencies, not seven new metric formulas. The rightmost
column distinguishes work Codex can implement after the model is settled from
the evidence or semantic decision that cannot be manufactured by code.

| Package | Concrete unresolved case | Needed to close it |
| --- | --- | --- |
| B1 — Complete consequences and boundary state | Runner on third, one out, batter strikes out: identifying the batter's origin does not identify whether the runner remains, scores independently, or is out. | A reviewed graph contract for the complete relevant participant set, positive actual end states, stranded runners and pre-consequence out count. Missing runner rows cannot establish unchanged state. Existing larger-Site identity and time-qualified location remain an ontology question where physical location is asserted; they are not prerequisites for every origin designation. |
| B2 — Personal continuity and contribution identity | One runner advances safely and is then out; a steal precedes a single; a pinch runner replaces the original runner. | The verified complete-history criterion is accepted: same person, compatible endpoints, all intervening events accounted for, and no intervening terminal boundary. C1/C2 are accepted and their conformance/projection components are implemented. Source reconciliation and admitted whole creation remain pending. Preserve separate attributed and independent contribution episodes; matching identifiers or adjacent rows alone are insufficient. |
| B3 — Operative outcomes and corrections | A strikeout with an uncaught third strike; a replay changes a specific safe/out decision; an appeal changes the operative inning-ending result. | Identify each distinct operative resolution and the correction that affects it. Reconcile duplicate descriptions of one out. A PA-level review flag or a strikeout/scorer code is insufficient. Encode the reviewed outcome contract in the owning source SHACL and analytical query. |
| B4 — Completed populations and eligibility | An unfinished batting turn produces no PA; a mid-turn substitution can separate the acting batter from statistical PA attribution; a season has missing games. | Complete eligible game/PA membership and reconciliation through the accepted cutoff, plus the scoped eligibility policy for uncommon substitutions. Ordinary display filters cannot alter the reference population. Census/reconciliation mechanics are engineering after the graph contract is reviewed. |
| B5 — Exact pitch and defensive process evidence | A count changes without a pitch; a rundown repeats throws although official credits list one assist. | Operative ordered count-state evidence, pitch/non-pitch distinction and termination; distinct intentional field/throw/catch/tag acts, agents and supported precedence. Credit lists do not establish a complete act sequence. Some data may require additional source evidence; no new source lane is authorized by this package. |
| B6 — Accepted choices awaiting evidence | PAQ-A uses the immediate pre-consequence state; independent marginal gains are 1/3, 1/2 and 1; review dependence uses all review-eligible decisions, separated by mechanism. | The choices below are settled. Complete admitted inputs still depend on B1–B4; these choices do not authorize new ontology vocabulary. |
| B7 — Deferred extensions | Speed might help explain an error; catcher interference may benefit the batter without batter achievement. | Retain the accepted error/FC exclusion and the user's interference deferral. A speed threshold or causal-credit rule requires a separate explicit decision with evidence. These extensions need not be invented to implement the already accepted policy. |

### Three metric choices, subsequently answered

1. **PAQ-A comparison boundary.** Choose PA-start base/out state or the state
   immediately before the batter consequence. Example: a runner steals second
   before the batter's single. PA-start compares the PA with first-base starts;
   the immediate boundary compares it with second-base starts. Both preserve
   the accepted independent-credit exclusion and actual-end-state erosion.
   **Accepted answer:** use the immediate pre-consequence state.
2. **Positive independent running.** Specify the increasing marginal values
   for the base transitions being scored and whether positive running remains
   a separate reported quantity or combines with accepted damage in a net
   score. Additive scoring must give the same value to the same supported path
   regardless of source-row segmentation. No empirical Speed or run-expectancy
   interpretation follows from selecting these weights. Negative damage is
   already defined; it does not need a new formula decision.
   **Accepted answer:** marginal weights 1/3, 1/2 and 1; report advancement,
   damage and their net together.
3. **Review-dependence denominator.** Select the distinct institutional outcome
   categories in the denominator and whether the population is all such
   outcomes or only season-eligible reviewable outcomes. The numerator must
   still identify the particular operative outcome depending on a review.
   Research already includes conditional fair/foul and fan-interference
   eligibility; the 2026 ABS mechanism cannot silently enter an older replay
   population. This choice does not change AV's existing mapped-review scope.
   **Accepted answer:** all review-eligible decisions, including never-reviewed
   decisions; traditional replay and ball/strike challenges reported separately.
   Exact outcome-category scope and eligibility evidence remain unresolved.

### Coverage of all 21 register codes

| Gap code | Owning package or dependency |
| --- | --- |
| ATTRIBUTION | B1/B2; B7 for optional error-speed and deferred interference extensions |
| BOUNDARY_STATE | B1 |
| PATH_IDENTITY | B2 |
| OPERATIVE_OUTS | B3, with B1/B2 for attribution |
| COMPLETENESS | B1/B3/B4 and the relevant process census in B5 |
| TFS | B1–B3; no separate formula vote |
| REFERENCE_POPULATION | B4 |
| PAQ_A_STATE | B6 choice 1, then B1 evidence |
| OFFENSIVE_ELIGIBILITY | B4 plus complete positive-contribution evidence |
| INDEPENDENT_EPISODES | B2 |
| INDEPENDENT_SCORE | B6 choice 2; accepted damage still requires B1/B2 evidence |
| CHANNEL_EPISODES | B2; the one-play-per-channel unit is settled |
| EXACT_PITCH_COUNTS | B5 |
| DEFENSIVE_ACTS | B5 |
| DEFENSIVE_ORDER | B5 |
| RUN_CONTINUITY | B2/B3 |
| SUPPORT_ATTRIBUTION | B2 |
| OPERATIVE_REVIEW | B3 |
| OUTCOME_POPULATION | B6 choice 3, then B3/B4 evidence |
| ROLE_POPULATION | B5 plus complete game-scoped realization evidence; no new role kinds |
| PAQ21_ELIGIBILITY | B4/B5 plus admitted TFS; the known-inapplicable policy is settled |

## Engineering and deployment status

The complete arithmetic suite and exact SQL persistence have focused tests.
The current serving pass additionally fixes the browser fallback's missing
movement query, checks full Python/JavaScript query equivalence, prevents an
empty scope from scanning the corpus, and makes Explorer startup detect a
changed metric query builder. All 20 HTTP routes have been exercised with
the actual reducer and authoritative data.

The NiFi one-game proof has promoted the corrected graph pair. Whole-corpus
SQL completion is a separate operational gate. Recorded retries included a
metric implementation changing during a build and a graph count changing
after a build's initial snapshot. Those are valid rejection conditions, not
permission to weaken consistency checks. NiFi owns the current build and its
retry/quarantine outcome; the Explorer's tested authoritative fallback serves
the same metric contract in the meantime.

After a named modeling decision is accepted, Codex owns the corresponding
mapping coverage, source SHACL, graph-to-calculation adapter, fixtures and
serving implementation. It must not ask for approval of each engineering
file. A new class, relation or identity policy would require its own explicit
review before executable implementation. Neither a general “continue” nor
approval of one of the three numerical choices supplies that approval.
