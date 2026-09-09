# One review for the new metric suite

The user requested all metric calculations and supporting software now, with
the remaining gaps collected for one subsequent review. That software scope
is recorded in the [implementation decision](../../archive/design-records/graph-native-metrics-implementation-scope/decision.json).
Named answers are now recorded in the
[batch decisions](../../archive/design-records/metric-suite-batch-answers-2026-09-08/decision.json)
and [clarifications](../../archive/design-records/metric-suite-batch-answers-2026-09-08/clarifications.json).
Those records accept the stated meanings, not the remaining ontology or
source-evidence prerequisites.

The [canonical gap register](../../sparql/metrics/gap-register.json) contains
21 shared requirements. Its identifiers are calculation availability codes,
not ontology terms. The [metric catalog](../../sparql/metrics/metric-catalog.json)
maps each of the 20 metrics to its requirements. The Explorer presents the
same register and allows one download of the whole review.

## Decisions settled on September 8

- Empty Games require at least one PA. Zero-PA runners remain eligible for
  baserunning metrics.
- Independent advances on steals, wild pitches, passed balls and balks belong
  to the runner. Independent damage includes direct destruction and surviving
  teammate erosion. Increasing positive base values are wanted; weights remain
  to be selected.
- CPD counts a positive play once per channel, regardless of beneficiary count.
- Reference populations include eligible completed season PAs through the
  reporting cutoff, with complete coverage required.
- Field, throw, catch and tag count as four intentional acts.
- Personal runner trajectories end on score, out, replacement or inning end;
  replacement begins a different person's trajectory.
- Run Construction Breadth includes the scoring runner's own contributions.
- Role Realization Breadth counts the four realized Batter, Baserunner, Pitcher
  and Fielder kinds, excluding generic parents.
- Known inapplicable recovery/defensive dimensions exclude a PA from PAQ-2.1;
  unknown applicability cannot be silently excluded. PAQ-2 remains separate.
- Actual-end-state erosion is retained. Third base, one out, strikeout plus
  passed-ball score gives batter TFS -1/4 without batter progress credit.

The calculation policy lives in
[`batch-release-policy.json`](../../sparql/metrics/batch-release-policy.json).
The [research note](research-leads-speed-replay.md) covers coaching, public
running data, replay and the preliminary field-selection inventory.

The subsequent [web assessment of all 21 gaps](web-gap-assessment.md) resolves
12 factual research questions and identifies the remaining model, evidence and
metric choices for each gap. Several findings strengthen earlier answers;
none is misreported as a new live graph admission. Its
[machine-readable index](web-gap-assessment.json) is linked from the central
gap register. It also identifies why scoring credits cannot substitute for
actual outcomes or complete act sequences.

## Remaining review and evidence as a single batch

1. **Trajectory structure:** attribution, continuous-path identity, distinct
   operative outs, and complete participant/outcome coverage. Preserve the
   already accepted terminal-out, error/FC and shared-play erosion policies.
2. **Runner location and time:** identify the larger Site containing the
   existing base Site, and express the runner's location at the relevant
   boundary. The user rejected a Relational Quality account. Recognized
   safety, physical base contact, location and temporal persistence remain
   separate. No Mermaid change is proposed or made in this package.
3. **Populations:** evidence for accepted offensive eligibility, eligible season
   PAs and four role kinds; exact PAQ-A comparison state and replay denominator.
   A filtered or incomplete set cannot silently become the percentile
   reference population.
4. **Independent contributions:** evidence for independent running episode
   identity, attribution and accepted damage; exact increasing positive weights
   and any net score. CPD's one-play-per-channel unit is settled.
5. **Process structure:** exact ordered pitch counts for recovery, intentional
   defensive acts and precedence for depth, and continuous scoring paths
   with offensive support attribution across plate appearances.
6. **PAQ-2.1 eligibility:** graph evidence distinguishing known inapplicability
   from missing information, and complete applicable reference coverage.

Each register entry states the remaining question and accepted direction.
An open evidence prerequisite does not mean its policy answer is still open.
These are consolidated review items, not successive implementation stops.
Closing one shared requirement should close it for every dependent metric.

## Existing review and evidence

The [batter-consequence review](../mlb-game-batter-consequence-attribution/README.md)
continues to own the unresolved world-side model. Its
[boundary vocabulary analysis](../mlb-game-batter-consequence-attribution/boundary-temporal-vocabulary.md)
describes why timeless location plus separately dated entities does not
qualify the location assertion. This package links to that work rather than
creating a competing ontology or diagram.

Accepted partial implementations remain in the design archive:
[contact-play containment](../../archive/design-records/mlb-game-batted-runner-resolution-containment/README.md),
[runner-resolution and award links](../../archive/design-records/mlb-game-resolution-award-links/README.md),
and [baserunning origin](../../archive/design-records/mlb-game-baserunning-origin/README.md).
The evidence queries under `sparql/metrics/` expose those graph facts without
treating their presence as proof that an entire consequence is complete.

The existing checked-in MLB payloads remain evidence for the owning source
lane. They are not metric inputs. Wider history, exact count coverage and
omitted authoritative fields are source coverage debt where applicable;
they do not justify duplicating another provider's fields.

## What is implemented, and what review will unlock

All 20 calculation kernels, exact arithmetic, percentile/cohort reducers,
player summaries, evidence extraction, SQL persistence, read-only API and
Explorer presentation are implemented. Focused synthetic admitted-evidence
tests exercise every metric through SQL. See the
[implementation and validation report](../../serving/METRIC-SUITE-IMPLEMENTATION.md).

Live metric admission is deliberately narrower. Adjudication Volatility can
describe explicitly resolved mapped reviews using existing graph structure.
The other 19 metrics return unavailable with their register identifiers;
their graph-to-calculation adapters require the decisions above. Complete
software arithmetic does not establish complete or valid source evidence.

After this batch is resolved, record the named accepted decisions, implement
the world-side identity/ontology changes actually required, update the owning
RML and SHACL, prove a one-record/one-game fixture, and let NiFi execute bounded
promotion and serving materialization. No raw rewrite, wholesale RML rebuild,
or removal of previously promoted RDF is required by the metric software.

The review record stays draft, with no invented approval or pinned mutable
artifacts. No new terms or Mermaid artifacts are declared here.
