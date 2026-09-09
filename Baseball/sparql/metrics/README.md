# Graph-native metrics roadmap

## Current implementation

The complete 20-metric calculation suite is now implemented with exact
arithmetic, SQL products, a read-only API and an Explorer page at `/metrics`.
See the [implementation report](../../serving/METRIC-SUITE-IMPLEMENTATION.md)
and [calculation contract](../../serving/METRIC-SUITE.md). The
[batch review](../../proposals/graph-native-metric-suite-batch-review/README.md)
collects all remaining shared gaps. The implementation is authorized by the
user's later request to implement every metric now and review the gaps together.

The checklist below remains the broader **production semantic admission**
roadmap. Its unchecked source and release gates do not mean the new arithmetic
software is absent. The current live adapter supports only explicitly resolved
mapped review volatility; other metrics report unavailable with named gaps.

## Original production roadmap

Status: accepted implementation direction and release defaults; remaining
attribution, before-state and completeness semantics are under review.

BaseballO will rebuild its offensive analytics around connected baseball
processes rather than weighted outcome checklists. The foundational analytical
object is the batter-attributed consequence structure of a plate appearance:
which offensive trajectories progressed, completed, remained active, eroded,
or were destroyed.

This roadmap does not approve a new ontology term, object property, identity
policy, RML assertion, or SHACL constraint. Those changes remain subject to the
repository's semantic review sequence.

## Target metric architecture

- Trajectory Fulfillment Score (TFS) is the foundational plate-appearance
  consequence measure.
- PAQ-2 is a league-relative percentile derived from TFS.
- PAQ-A compares a plate appearance with others beginning in the same occupied
  base and out state.
- Offensive Reach, Hidden Help, Rally Kill, Opportunity Erosion, Empty Games,
  and Contribution Path Diversity reuse the same attributed-consequence grain.
- Canonical analytical meaning remains in version-controlled SPARQL and metric
  contracts over authoritative RDF.
- SQLite contains rebuildable reusable facts and metric results for ordinary
  Explorer use. It is not semantic authority.
- Every public metric retains a human-readable explanation path to the
  supporting processes, judgments, decisions, and source records.
- PAQ-1.0 remains frozen and reproducible as a historical experimental metric.

## Execution checklist

### 0. Preserve the current baseline

- [ ] Freeze PAQ-1.0 without changing its existing query or meaning.
- [ ] Preserve its current SQL and UI behavior while PAQ-2 is developed.
- [ ] Capture representative PAQ-1 result and performance evidence.
- [ ] Introduce PAQ-2 under a distinct version and route.

### 1. Review the attribution contract

- [x] Inventory current RDF paths for Batter Acts, Plate Appearances,
  Batted-Ball Play Processes, runner resolutions, start states, destinations,
  outs, judgments, decisions, and replay reviews.
- [x] Express the accepted contact-play and award slices through existing
  BFO/CCO relations, episodes and decisions, without new object properties.
- [x] Draft a source-independent Mermaid proposal before changing RML.
- [ ] Distinguish batter-linked consequences from independent steals, caught
  stealing, pickoffs, balks, wild pitches, passed balls, and defensive
  indifference occurring during the same plate appearance.
- [ ] Cover batted-ball consequences and non-contact results such as walks,
  hit-by-pitch, and interference.
- [ ] Represent terminal runner destination and attributable out count through
  explicit RDF paths.
- [ ] Preserve original and operative decisions when replay changes a result.
- [ ] Obtain explicit ontologist review of the resulting graph pattern.

The [attribution review package](../../proposals/mlb-game-batter-consequence-attribution/README.md)
contains the static evidence inventory and reviewed diagrams. Immediate
consequence-boundary state, continuity and operative adjudication remain
unresolved. The original shortcut relations were withdrawn on 2026-09-09.

The user has since approved implementing the targeted fix. Its concrete A1
contact-play parthood slice is
[accepted separately](../../archive/design-records/mlb-game-batted-runner-resolution-containment/README.md)
and implemented as a bounded RML addition with source SHACL. The
[final award/origin decision](../../archive/design-records/runner-award-origin-final-decision/README.md)
retains episode/agent and safe-decision paths, replaces directives with causal
and normative relations, and supplies act-specific origin designations.
These resolve the two named modeling gaps; whole-trajectory completeness and
other live metric prerequisites remain independently gated.

The reviewed pattern must answer:

1. Which runner resolutions follow from the batter-linked result?
2. Which runner resolutions occurred independently during the same plate
   appearance?
3. What state did each affected offensive participant occupy immediately
   before the consequence?
4. Did each participant finish safe at a base, score, become out, or remain
   unchanged?
5. How many outs were created by the batter-attributed consequence?
6. Which offensive trajectories remained active afterward?

### 2. Extend and prove the MLB-game graph

- [x] Implement the approved contact-play, episode, safe-decision, award and
  segment-origin MLB-game RML additions.
- [x] Translate those accepted graph contracts into MLB-game SHACL.
- [x] Keep TFS and PAQ out of authoritative source RML.
- [ ] Add fixtures for every required attribution and trajectory edge case.
- [x] Run a local one-game RML, SHACL, and semantic inspection proof of the
  accepted slices (game 823016; evidence linked below).
- [ ] Complete a NiFi-owned one-game proof through graph-pair promotion and
  serving materialization using the corrected mapping.
- [ ] Run a small diverse-game proof before historical reconstruction.
- [ ] Reacquire historical payloads transiently through NiFi and replace graph
  pairs only after their new versions validate.

The [local proof evidence](../../archive/design-records/runner-award-origin-final-decision/implementation.md)
establishes the admitted graph slices, not complete trajectory scoring. The
bounded [NiFi submission for game 566279](../../archive/design-records/runner-award-origin-final-decision/nifi-proof-submission.json)
was accepted on 2026-09-09. NiFi owns its execution and reports success or
quarantine asynchronously. Submission alone does not check off promotion,
materialization or release.

The subsequent [NiFi stage observation](../../archive/design-records/runner-award-origin-final-decision/nifi-proof-observation.json)
confirms SHACL success and graph-pair promotion for that game; serving
completion remains unverified. Suite 2.0.2 now preserves the accepted movement
bindings in SQL and reports their observed coverage through the API and
metrics page. Its [live query proof](../../archive/design-records/runner-award-origin-final-decision/metric-serving-evidence.json)
has 113 movement pairs, with exact canonical-query row equivalence. This
closes the serving evidence integration task, not the open completeness gates.

### 3. Build one reusable trajectory grain

- [ ] Produce one plate-appearance consequence row.
- [ ] Produce one affected-participant row per plate appearance.
- [ ] Retain participant identity and batter-versus-existing-runner status.
- [ ] Retain start state, terminal state, progress, destruction, alive-after
  status, attributable outs, and opportunity erosion.
- [ ] Retain supporting process and source-record IRIs.
- [ ] Retain metric, source-scope, completeness, contribution-policy, and
  reference-population versions.
- [ ] Do not reduce the serving product to final rendered scores.

### 4. Implement canonical metric contracts

- [ ] `trajectory-fulfillment-score.rq`
- [ ] `offensive-reach.rq`
- [ ] `hidden-help-rate.rq`
- [ ] `rally-kill-rate.rq`
- [ ] `opportunity-erosion.rq`
- [ ] `paq-2-core.rq`
- [ ] `paq-a.rq`
- [ ] `empty-game-damage.rq`
- [ ] `contribution-path-diversity.rq`
- [ ] `adjudication-volatility.rq`
- [ ] `review-dependence-rate.rq`
- [ ] Add every query to the metric catalog and source-scope catalog.
- [ ] Treat incomplete or unknown consequences as unknown, never as zero.

### 5. Extend the SQL serving layer

- [ ] Preserve the existing PAQ-1 serving columns for compatibility.
- [ ] Add versioned offensive-trajectory facts.
- [ ] Add versioned plate-appearance metric facts.
- [ ] Add normalized metric evidence sufficient for a `Why?` explanation.
- [ ] Add reference-population and percentile facts.
- [ ] Add indexes for plate appearance, player, game, season, state, and metric
  version.
- [ ] Recompute season percentile rankings from persisted trajectory facts
  after new games arrive rather than rereading every historical RDF graph.
- [ ] Promote only immutable validated serving builds.

The intended nightly sequence is:

```text
promoted game graphs
-> per-game trajectory SPARQL
-> reusable SQL facts
-> season-wide percentile refresh
-> validation
-> immutable serving-build promotion
```

### 6. Prove equivalence and preserve evidence

- [ ] Verify all mandatory trajectory fixtures and expected TFS values.
- [ ] Compare authoritative RDF and indexed RDF wherever an index is used.
- [ ] Compare canonical metric results and candidate SQL.
- [ ] Test ties, midranks, incomplete games, unknown result classes, replay
  changes, forced advances, and independent runner events.
- [ ] Benchmark authoritative SPARQL, indexed RDF, and SQL.
- [ ] Admit each Explorer route independently.
- [ ] Keep live SPARQL available as the research and fail-open path.

### 7. Release PAQ-2 as the first visible slice

- [ ] Show individual plate appearances.
- [ ] Show player mean and median PAQ.
- [ ] Show PAQ-A, top-quartile rate, bottom-quartile rate, and distribution.
- [ ] Support game, bounded stretch, and season views.
- [ ] Support a minimum-plate-appearance threshold for rankings.
- [ ] Link aggregate results to individual plate appearances.
- [ ] Render a human-readable `Why?` explanation from persisted evidence.
- [ ] Move the route to SQL only after end-to-end equivalence succeeds.

### 8. Expand after the vertical slice

- [ ] Empty Game Rate and Empty Game Damage.
- [ ] Offensive Reach.
- [ ] Hidden Help Rate.
- [ ] Rally Kill Rate and Rally Kill Severity.
- [ ] Contribution Path Diversity.
- [ ] Adjudication Volatility and Review Dependence Rate.

Later work remains gated by additional authoritative evidence:

- exact pitch-count state before Recovery Quality and PAQ-2.1;
- accepted fielding-act identity before Resolution Depth and Defender Breadth;
- cross-plate-appearance runner continuity before Run Construction Depth and
  Run Construction Breadth.

## Accepted metric policies

The user accepted these choices on 2026-09-08:

- [PAQ-2 defaults](paq-2-release-defaults.json): 0–100 percentile display;
  eligible MLB regular-season plate appearances in the selected season;
  exact fractions internally and display-only rounding. PAQ-1 remains unchanged.
- [Inning-ending erosion](tfs-inning-ending-policy.json): include evidenced
  stranded runners. Third-base runner, two outs, batter strikeout gives
  `-1/4 - 1 = -5/4`, without inventing another out for the stranded runner.
- [Error/FC exclusion](contact-progress-policy.json): exclude that safe
  progress from TFS and Empty Game qualification. Preserve actual safe states,
  attributed outs and erosion. The zero-out FC example is now `-4/9`.

The [boundary contract](../../proposals/mlb-game-batter-consequence-attribution/metric-boundary-contract.md)
records exact examples, remaining cases and population safeguards. The
[final origin policy](trajectory-origin-policy.json) uses movement segment
designations and gives the PA batter metric HOME=0. No preceding stasis or
shared ending/beginning instant is required. Existing-runner PA-start fallback
requires positive support for the act beginning there without intervening
same-runner movement; it is never reconstructed from missing records.

## Evidence audit and remaining release gate

[runner-location-evidence.rq](runner-location-evidence.rq) inventories the
existing PA-start Stasis, temporal anchors and explicit location links. Four
focused tests verify that it preserves missing times and separate PA contexts.
It does not turn entity-existence times into location-validity times or infer
a later consequence state from PA-start evidence.

The [continuous-path terminal-out policy](continuous-path-terminal-out-policy.json)
is also accepted: once continuity and attribution are evidenced, an out ends
the path without retained intermediate progress, and destruction uses its
original start. The boundary-association modeling direction is recorded in the
[active review](../../proposals/mlb-game-batter-consequence-attribution/boundary-state-evidence.md).
The [shared-play erosion convention](shared-play-erosion-policy.json) is now
accepted for non-inning-ending plays with complete end states and no independent
outs. It uses actual end state as erosion context without crediting independent
progress. Other ambiguous cases remain unknown. Fifteen complete hypothetical
examples pass the [exact SPARQL arithmetic regressions](../../tests/fixtures/metrics/README.md);
production graph admission and scoring remain gated.

[runner-movement-evidence.rq](runner-movement-evidence.rq) exposes individual
act/resolution pairs using explicit Base Code Identifiers, with source-record,
contact-play, causal award and source-origin designation paths. Nine regression
tests cover separate movements, unknown values, graph/PA scope, conflicting
codes, no continuity fallback, normative requirements and batter metric HOME. These
are reviewable evidence rows; they are not scored or coalesced trajectories.

The [boundary evidence review](../../proposals/mlb-game-batter-consequence-attribution/boundary-state-evidence.md)
adds concrete unchanged-runner and inning-ending examples. The current
[location design](../../proposals/mlb-game-batter-consequence-attribution/boundary-temporal-vocabulary.md)
preserves the existing Base Site inside a larger Site in which the runner is
located. Larger-Site identity, temporal qualification and source completeness
remain necessary before those cases can contribute to erosion. The Quality
candidate is withdrawn and Mermaid diagrams are unchanged.

[attribution-evidence.rq](attribution-evidence.rq) audits explicit resolution,
runner, destination, baserunning-origin, contact-play and award links in the owning MLB-game
authoritative graphs. It is covered by the source-scope catalog and three
focused regression tests. Zero link counts describe graph coverage, not zero
real-world contribution. This audit neither calculates a metric nor certifies
that a PA is eligible.

Immediate-before state, unchanged-participant evidence, continuity, operative
out/replay identity and full attribution/completeness still block metric
execution. A selectively covered subset cannot silently replace the accepted
league reference population. No executable TFS/PAQ-2 scoring query or serving
route is released yet.

## Final award and origin decision (2026-09-09)

The final user decision replaces event-specific award directives with
Walk/HBP **is cause of** the particular Baserunning Act and the applicable
Baseball Rule **requires** that act. Existing runners require positive source
force evidence (`r_adv_force`), exact next-base completion and same-event
identity. Reviewed/ambiguous PAs and unverified rule editions are withheld by
the current conservative source selection.

`BaserunningSegmentOriginDesignation` is about the act, designates the Base
from `movement.start`, and is part of its source record. `originBase` is not
substituted for start. No stasis, physical location, shared boundary or runner
continuity is inferred. The metric supplies HOME=0 for the PA batter. Existing
runners use their act's designation first; PA-start fallback requires positive
act-start and no-intervening-movement evidence, otherwise origin is unavailable.
The current source does not manufacture that fallback completeness evidence.

The source maps the verified 2019 and 2026 Official Baseball Rule editions.
Other editions do not acquire rule-dependent assertions until verified. This
is field coverage, not a new semantic gap or a reason to stop unrelated ingestion.

`metric_suite.trajectories(..., batter=...)` applies the admitted origin policy;
its input is graph evidence, not raw MLB JSON. The existing already-coalesced
input interface remains available. Missing or conflicting origin evidence is
unavailable. Exact TFS arithmetic and other metric eligibility gates remain.

Previously promoted graphs require normal NiFi replacement before the new
paths appear. This code change does not silently rewrite promoted RDF.
