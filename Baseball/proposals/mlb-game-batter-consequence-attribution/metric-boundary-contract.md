# TFS boundary and completeness contract

This document separates accepted metric choices from remaining graph and
contribution decisions. It does not authorize metric execution or RDF changes.

The user's current [nested-site location direction](boundary-temporal-vocabulary.md)
preserves the existing Base Site within a larger Site in which the runner is
located. The Relational Quality candidate is withdrawn. Exact larger-Site
identity, time qualification and source support remain to be reviewed.

## Accepted choices

- PAQ-2: 0–100 percentile display; eligible MLB regular-season PAs in the
  selected season; exact rational arithmetic with display-only rounding.
  [Decision](../../archive/design-records/paq-2-release-defaults/decision.json).
- TFS: charge erosion to evidenced stranded runners when the attributed
  consequence ends the inning. Do not also assign those runners an out or
  destruction. [Decision](../../archive/design-records/tfs-inning-ending-erosion/decision.json).
- Exclude safe progress from reached-on-error and fielder's-choice
  consequences from TFS progress and Empty Game positive-contribution
  qualification. Retain actual safe states, attributed outs and erosion.
  [Decision](../../archive/design-records/tfs-error-fc-progress-exclusion/decision.json).
- For an evidenced continuous batter-attributed path ending in an out, use
  the original start and terminal outcome. Intermediate safe advances retain
  no progress credit. First to second, then out trying for third gives zero
  progress and destruction of `1/3` for that participant.
  [Decision](../../archive/design-records/tfs-continuous-path-terminal-out/decision.json).
- The [boundary-association direction](../../archive/design-records/baserunner-boundary-association/decision.json)
  is accepted: distinguish base association at an evidenced Game boundary
  from continuously standing on the Base or an evidenced persistence interval.
  The user's required-contact clarification remains explicit; it does not
  establish an individual touch. Exact ontology terms remain under review.
- The [contact-evidence clarification](../../archive/design-records/baserunner-association-contact-evidence/decision.json)
  is also accepted: supported recognized base association may be represented
  while the particular touching process remains unknown. Missing touch
  evidence is neither a missed touch nor proof against that association.

## Proposed evaluation order

1. Identify the particular consequence, its positive attribution evidence
   and the contribution policy. Contact-play parthood is structural evidence;
   it is not a blanket credit rule. Walk/HBP award-completion links retain
   their accepted bounded meaning.
2. Identify all relevant participants and the immediate boundary before
   the consequence. Use the first evidenced act in each admitted participant
   path, not the PA-start stasis after an intervening independent event.
3. Establish a complete set of operative resolutions and their ordering.
   Separate distinct outcomes from multiple descriptions of the same outcome.
   A PA result, a runner resolution and an Out Judgment may describe one
   counted out; counting all three as outs is invalid.
4. Coalesce only paths whose continuity is evidenced and reviewed. Compute
   one start/end result for that continuous participant consequence. A shared
   runner or row adjacency is insufficient. Independent events form separate
   consequences and do not enter the batter's progress or attributed-out total.
   The terminal-out scoring treatment is now accepted separately; the evidence
   and identity criteria for forming the path remain unresolved.
5. Classify the participant as safe at an evidenced base, counted scored,
   counted out, or positively evidenced unchanged/stranded. Unknown is a
   separate admission failure. Scored and out participants do not receive
   erosion as surviving/stranded runners.
6. Apply the supplied TFS formula using the pre-consequence out count and
   distinct attributed counted outs. Preserve exact fractions and supporting
   graph IRIs. A count of mapped links is not evidence of full coverage.

This is a proposed evaluation contract, not executable Python decision logic.
Accepted graph constraints will belong in source SHACL; calculations and
analytical admission will belong in reviewed SPARQL and equivalent SQL.

## Exact example checks

The non-inning-ending examples below restate the user's supplied metric
specification. They assume complete attribution/state evidence; the table is
not a claim that those facts are already queryable for every source record.

| Case | Progress | Destruction | Erosion | TFS |
| --- | --- | --- | --- | --- |
| Bases-empty double | 1/2 | 0 | 0 | 1/2 |
| Double scoring a runner from second | 3/2 | 0 | 0 | 3/2 |
| Bases-loaded home run | 4 | 0 | 0 | 4 |
| Bases-empty ordinary out | 0 | 1/4 | 0 | -1/4 |
| Strikeout, runner third, one out | 0 | 1/4 | 1/2 | -3/4 |
| Strikeout, runner third, two outs — accepted clarification | 0 | 1/4 | 1 | -5/4 |
| Sacrifice fly scoring third, one out | 1 | 1/4 | 0 | 3/4 |
| Groundout advances second to third, zero outs | 1/2 | 1/4 | 1/3 | -1/12 |
| FC puts runner from first out; batter safe first; zero outs — accepted exclusion | 0 | 1/3 | 1/9 | -4/9 |
| GIDP, runner first, zero outs | 0 | 1/4 + 1/3 | 0 | -7/12 |

The FC row supersedes the supplied `-7/36`: the accepted exclusion removes
the batter's `1/4` progress without removing his actual safe end state from
the erosion calculation. A bases-empty reached-on-error consequence with
no outs and no other contribution can consequently have TFS zero; it must
still be distinguished from missing or incomplete evidence.

## Cases that still block a full score

| Case | Remaining decision/evidence |
| --- | --- |
| Steal then single advancing second to third | Origin link now has an accepted [relation](../../archive/design-records/mlb-game-baserunning-origin/baserunning-origin-review.md), with two real checked-in examples. Full participant/out completeness is still required. |
| Unchanged runner during a batter out | No runner row is not evidence of unchanged state. We need an explicit scoped boundary observation or a reviewed, proven complete transition contract. Do not mint a Safe Process just to create an unchanged row. |
| Third out with runners left on base | Erosion policy is accepted; identification of the actual stranded runners still needs positive/completeness evidence. |
| Simultaneous strikeout and wild-pitch advance | Actual shared-play end is accepted for erosion in the bounded non-inning-ending case with no independent outs. A reviewed common boundary and complete state/out evidence are still required; index equality alone is insufficient. |
| Strikeout versus uncaught third strike | A strikeout is not universally a counted out. A distinct supported Out Process and a reviewed link to that consequence are still required for attribution. |
| Error or FC contact progress | Safe progress is excluded by the accepted policy. Supporting contact-play links still do not settle which secondary advances belong to a different credited consequence. |
| Multiple rows, including safe advance followed by out | Original-start/terminal-out scoring is accepted for one evidenced continuous attributed path. Continuity and terminal-resolution identity still require review before rows can form that path. |
| Pinch runner | A different Person replaces the runner. Do not merge their paths through the career-persistent Baserunner Role or adjacency alone. |
| Review overturn | The operative decision must determine the particular resolution. An overturn flag does not identify that resolution or reconstruct the original decision. |
| Walk-off | No fabricated continuation or extra outs. Source truncation and the eligibility of other participants require review. |

## Population and ranking safeguards

The user has now accepted the [shared-play erosion rule](../../archive/design-records/tfs-shared-play-erosion/decision.json):
use the evidenced actual end state for erosion in the bounded non-inning-ending
shared play with independent safe advances/scoring and no independent outs.
Independent advances receive no batter progress credit, and only attributed
outs enter the numerator. This defines an evaluation boundary, not a temporal
order between overlapping events. Unknown evidence still withholds a score;
unresolved cases must remain explicit in coverage accounting.

Fifteen complete hypothetical policy examples now have exact SPARQL arithmetic
regressions in [the test fixture](../../tests/fixtures/metrics/README.md).
These checks do not establish admission of any source graph or release TFS.

The accepted reference population is a target population, not permission to
substitute whichever subset currently maps successfully. Before publication,
declare the exact eligibility contract and coverage denominator, missing-game
and missing-PA counts, source/graph versions, season and refresh boundary.
Missing outcomes are not zero; zero-row mapping failures do not disappear
from the coverage denominator.

The supplied midrank formula applies only for N greater than one. Ties must
remain ties at exact internal precision; rounded display values cannot set
rank order. N=0/N=1 behavior, display precision and minimum cohort thresholds
remain implementation-contract details to settle before public rankings.

The [graph-link audit](../../sparql/metrics/attribution-evidence.rq) is a
single-source diagnostic over accepted relations. It measures current link
coverage and never certifies eligibility or calculates TFS/PAQ-2.
