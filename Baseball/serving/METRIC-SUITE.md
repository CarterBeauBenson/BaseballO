# Graph-native metric suite

This suite implements 20 metric calculations. It is separate from PAQ-1 and
the existing Empty Game Explorer queries. The canonical catalog and shared
availability requirements are `sparql/metrics/metric-catalog.json` and
`sparql/metrics/gap-register.json`.

## Calculation contract

The kernels in `sparql/serving/metric-kernels/` consume **admitted SPARQL
bindings**, not MLB JSON or source event labels. They are derived SQL-serving
calculations, registered as such in `sparql/source-scope-catalog.json`.
`scripts/generate_metric_suite.py --check` detects drift from their generator.
The `authoritativeQuery` catalog field identifies the canonical calculation
query; it does not claim that an empty VALUES template extracts source facts.

`serving/metric_suite.py` validates identities, executes the kernels and
retains rational numerators and denominators as arbitrary-precision decimal
strings. Fractions are reduced before persistence. Sorting and tie comparison
use exact rational arithmetic; display rounding is the last step. SPARQL
uses integer cross multiplication for percentile comparisons.

| Metric | Implemented calculation |
| --- | --- |
| TFS | Sum retained progress minus direct destruction and opportunity erosion. |
| PAQ-2 | Exact TFS midrank in the complete season reference population. |
| PAQ-A | Same percentile calculation within the declared immediate pre-consequence base/out cohort. |
| Offensive Reach | Number of distinct trajectories receiving positive attributed progress. |
| Hidden Help Rate | Other-runner progress while batter progress is zero / PAs with zero batter progress. |
| Rally Kill Rate | PAs directly putting an existing runner out / PAs beginning with a runner. |
| Rally Kill Severity | Existing-runner destruction / PAs beginning with a runner. |
| Opportunity Erosion | Mean PA erosion; individual erosion is also a TFS component. |
| Empty Game Rate | Complete player-games with at least one PA and no qualifying positive episode / games with at least one PA. |
| Empty Game Damage | Sum of the magnitudes of negative PA and admitted independent episode scores in an Empty Game. |
| Contribution Path Diversity | Three-channel normalized Shannon entropy counting each positive play once per channel, plus exact counts and breadth. |
| Recovery Quality | Midrank of nonterminal pitches after the first two-strike state, within the admitted two-strike reference cohort. |
| Defensive Resolution Depth | Longest path in the admitted defensive precedence DAG, counting intentional acts. |
| Defender Breadth | Distinct agents in that defensive structure. |
| Run Construction Depth | Distinct state-changing episodes on the admitted scoring trajectory. |
| Run Construction Breadth | Distinct offensive players supporting that trajectory, including the scoring runner. |
| Adjudication Volatility | Reversed / explicitly resolved reviews in the declared mapped population. |
| Review Dependence Rate | Review-dependent operative outcomes / eligible operative outcomes. |
| Role Realization Breadth | Batter, Baserunner, Pitcher and Fielder kinds actually realized in the game; generic parents excluded. |
| PAQ-2.1 | Exact lexicographic percentile of TFS, Recovery Quality, then defensive depth, within the applicable population. |

For ordinal state `s` and safe terminal state `e`, retained progress is
`(e-s)/(4-s)` when positive and credited. Direct destruction is `1/(4-s)`.
Surviving-runner erosion is `attributedOuts / ((4-e)*(3-outsBefore))`.
The third out charges the remaining opportunity of stranded runners, without
inventing an additional out. Scored and directly out paths receive no survivor
erosion. Ordinals HOME=0, bases=1/2/3 and SCORE=4 are calculation states, not
new spatial assertions. All primitive TFS fractions fit a denominator of 36.

The accepted contact exclusions remove error/FC **progress credit**; they do
not remove the actual shared-play terminal state from erosion. Independent
advances may supply terminal context but are not batter progress. Only
attributed distinct outs enter the erosion factor. A continuous path ending
in an out retains no intermediate progress. The original start determines
destruction, rather than the last intermediate base.

Midrank is `100*(2*lower+ties-1)/(2*(N-1))`; N below two is unavailable.
Every tied value has the same rank. PAQ-A requires explicit cohort identity.
The reference is fixed before a player/display filter is applied. A season
coverage gap cannot be solved by ranking just the covered games.
The in-progress-season cutoff includes all eligible completed PAs through the
reporting cutoff. `paq21_population` excludes known inapplicable recovery or
defensive dimensions. Unknown applicability blocks reference completeness;
missing applicable dimensions remain unavailable. Neither affects ordinary
PAQ-2 eligibility by itself.
`player_paq` returns exact mean, median, the whole value distribution and
inclusive top (>=75) / bottom (<=25) quartile rates. `summarize` provides exact
complete-population means; with threshold 2 it also provides the
multi-trajectory rate for Offensive Reach. Use it on Empty Game Damage
values only for the admitted Empty Game population.

CPD retains exact rational channel proportions and the expression
`-sum(p*ln(p))/ln(3)`. Its logarithmic value is explicitly approximate;
it is not presented as an exact rational. Defensive longest paths and entropy
use reducers on the canonical SPARQL rows because SPARQL 1.1 has no portable
longest-path or logarithm operator.

Empty denominators, incomplete aggregates, incomplete cohorts, conflicting
identities, cyclic paths and missing outcomes never become zero. Exact
duplicate identities are coalesced; conflicting observations are rejected.
Inputs to the pure kernels are an engineering interface, not a source
admission mechanism. The HTTP API cannot accept facts or completeness flags.

`batch-release-policy.json` records the named September 8 decisions.
`empty_game_eligible` requires a complete PA count of at least one; zero-PA
runners remain eligible for independent baserunning metrics.
`independent_runner_damage` returns a positive damage magnitude, comprising
direct runner destruction plus surviving-teammate erosion. First and third,
zero outs, first caught stealing with third unchanged gives 2/3. The separate contribution helper implements the subsequently accepted positive weights and net score.
`empty_game_damage` consumes signed episode scores, so a positive damage
magnitude must be negated if supplied as a damage-only episode score.
Positive running weights are now accepted; speed-based error attribution remains open.

## RDF, SQL and API

`sparql/metrics/suite-evidence.rq` inventories existing PA, batted-play, run,
realized-role and replay structures within explicitly selected promoted game
graphs. The current adapter admits AV only over fully linked, explicitly
resolved mapped replay reviews. Unsupported dispositions are counted as
unresolved and excluded from that stated denominator. Conflicting original,
operative or disposition assertions make the result unavailable. It does not
infer official accuracy or claim a complete league-wide review population.

The other live adapters report their shared gap codes and observed evidence
coverage. They do not create zero-filled player or PA rankings. The complete
arithmetic implementations remain available for admitted fixtures while
those source semantics await the consolidated review.

Suite version 2.0.2 composes that inventory with the accepted
`sparql/metrics/runner-movement-evidence.rq`, scoped to the same explicit game
graphs. It preserves each act/resolution pair, PA, runner, origin designation,
safe destination, causal award, required rule and source-record binding in the
existing SQL evidence table. The canonical movement query is reused directly;
there is no additional RDF predicate or source mapping.

`coverage.runnerMovements` counts observed pairs and the presence of those
paths. It separately counts pairs with one, multiple or no metric-origin
values. Multiple bindings remain visible, and duplicate rows cannot inflate
pair counts. One bound value is an inventory fact, not a completeness or
attribution certificate. Counts of missing bindings describe query evidence,
not a runner's physical absence. The metrics page summarizes these counts;
the full coverage object remains in downloadable results. No trajectory
coalescence, unsupported unchanged-runner state, or new score is inferred.

`metric-suite-schema.sql` adds disposable evidence, result and manifest
tables to the existing serving build. Each game receives all 20 status/result
records. Values, evidence and serialized results have exact preservation
checks and fingerprints. Repeating a game replaces its own partition.
Selection pools resolved review counts, rather than averaging game rates.
The schema contains no proposal vocabulary.

The existing `scripts/pipeline/materialize-serving-layer.py`, invoked by the
MLB-game NiFi materialize stage, owns routine computation. Its immutable build
and atomic promotion rules still apply. The suite fingerprint is recorded
in build evidence and the serving pointer. A stale or incomplete build is
rejected by `query-serving-layer.py`. No new source lane, acquisition schedule
or topology is introduced. This implementation does not run a manual corpus
build or wait on healthy asynchronous source proofs.

The Explorer exposes `/metrics`, `GET /api/metrics/catalog`, and
`POST /api/metrics/query`. The latter accepts only `metricId`, `gameSet` and
`dateScope`. It uses validated SQL when available and falls back to scoped
authoritative SPARQL with the same reducer. The fallback reads existing RDF
on user request; it never acquires or transforms source payloads. The UI shows
exact values, definitions, coverage, supporting evidence, unavailable reasons
and downloadable results and gaps. Server-calculated scope/provenance remain
attached to the result. The existing temporary game-set provenance dependency
is a declared coverage limitation and does not admit a PAQ season cohort.

The batch review is [here](../proposals/graph-native-metric-suite-batch-review/README.md).

## September 9 accepted policy implementation

The [named answers](../archive/design-records/metric-suite-gap-answers-2026-09-09/decision.json)
are reflected in the executable policy and catalog. `paq_a_population` forms
cohorts from an admitted immediate pre-consequence base/out state, its evidence
and a declared reference population. A PA-start state after an intervening steal
cannot substitute. Missing boundary evidence prevents population admission.
The lower-level percentile kernel still consumes already admitted cohort keys.

`independent_runner_contribution` takes one already complete, coalesced episode,
using the same participant/out-state contract as the accepted damage helper.
Its canonical SPARQL component adds 1/3 for first-to-second, 1/2 for
second-to-third, and 1 for third-to-home. A direct first-to-third path and its
supported segment sum both yield 5/6. Results retain advancement, damage and
net = advancement minus damage as exact fractions. The existing terminal-out
policy remains: a coalesced path ending out keeps no intermediate advancement.
The helper does not infer continuity or accept raw source segments as a path.
This is a calculation component of the suite, not a newly admitted live metric.

`review_dependence_by_mechanism` receives one declared population per call and
keeps traditional replay and ball/strike challenges separate. Every eligible
outcome enters its mechanism's denominator, including unreviewed outcomes;
the numerator requires supported operative review dependence. Its internal
`reviewDependent` flag is passed to the older kernel column named `reviewed`;
a review's mere presence must not populate that flag. Unknown eligibility or
dependence blocks the affected mechanism, and incomplete populations remain
unavailable. Outcome categories and season-specific eligibility still require
a reviewed source contract.

Supported safe end-state association need not assert physical location or a
stasis. A supported final operative outcome need not have its original call
available for ordinary trajectory scoring. Official statistical PA attribution
and actual consequence contributors remain separate. These are accepted policy
requirements; no new RDF representation or source admission is inferred.
The subsequent [explicit continuity acceptance](../archive/design-records/metric-suite-gap-answers-2026-09-09/continuity-decision.json)
settles question 7: an independently verified complete intervening history can
establish continuity for the same person with compatible endpoints and all
events accounted for, provided no replacement, out, score or inning ending
breaks the trajectory. Separate contribution episodes remain separate. Matching
identifiers or adjacent rows alone are insufficient. C1/C2 subsequently accept the graph representation and projection described
below. Source reconciliation remains pending, so the current helpers continue
to require admitted histories and do not join raw source segments.

The next evidence extraction increment retains `episode`, `safeJudgment`,
`safeDecision` and `originRecord` from the canonical movement query through
SQL storage. Those fields are IRI-validated. Coverage reports the observed
supporting paths without asserting population completeness; conflicting
episode assertions remain separate evidence rows for the same act/resolution
pair. An unrelated record or decision about a different resolution cannot
supply the missing support.

That evidence extraction increment passed twenty-two focused Python
query/serving tests and eight browser/API/compiler tests.

## Accepted C1/C2 implementation

The [C1/C2 decision](../archive/design-records/runner-continuity-boundary-projection/review.json)
was published before implementation. The source's personal Process SHACL
contract enforces the accepted whole/episode pattern using existing relations.
`trajectory`, `trajectoryHalf` and `trajectoryInterval` now survive evidence
extraction and SQL; coverage counts observed bindings without certifying them
as complete histories.

`project_runner_boundary` executes the canonical `runner-boundary-projection`
SPARQL component. It selects a supported safe base at the independently
supported boundary only if the admitted history supplies no later or
ambiguously concurrent state-changing/unknown event that defeats it. State
change, terminal outcomes and unresolved review evidence prevent stale-state
projection. A supported newer safe outcome supplies the new state. The
returned base is analytical and receives no RDF predicate or contribution
credit. The complete-history flag is internal input admission, never a public
API option or a conclusion drawn from mapped row counts.

The [source contract](../sources/mlb-game/review/runner-continuity-source-contract.md)
documents the required real-history evidence. No complete-history adapter or
personal-whole RML source is fabricated from the existing incomplete evidence.
Live dependent metrics therefore remain gated. C1/C2 themselves are accepted.
