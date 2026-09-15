# Implementation of the two follow-up choices

The accepted decision was committed and pushed as `fecdf87` before this code
was written. This file records engineering outcomes, not additional approval.

`serving/metric_suite.py::failed_hit_and_run_scores` routes a complete,
independently confirmed swinging-strikeout/runner-thrown-out consequence to the
batter. It retains the actual runner and both outcomes in evidence. No running
score is emitted for that same consequence; an empty running-score list is not
a zero-score episode that could inflate running qualification.

The first-and-third, one-out example yields destruction 1/4 + 1/3 and
third-base erosion 2 / ((4 - 3) * (3 - 1)) = 1. Batter TFS is consequently
-19/12 under the existing formula. If the other runner officially scored
before the boundary, the score is -7/12 with zero remaining erosion and no
positive batter credit. These are arithmetic consequences of the accepted
ownership decision, not claims that the user separately specified the numbers.

The helper accepts admitted analytical inputs only. It cannot confirm a
strategy from raw feed records. Unknown strategy, incomplete consequences,
missing participants and contradictory outcomes withhold the result or fail
input validation. No live adapter supplies this confirmation contract yet.

Contribution Mix qualification now uses batting OR independent running. The
two minima use complete selected-period team-game exposure. Distinct eligible
running episodes are supplied separately from the positive contribution
channels used by entropy. Zero-PA runners qualify through running; no minimum
is relaxed to fill five places. All other qualification rules are preserved.

The leaderboard also accepts the settled entropy representation: exact pooled
channel counts, approximate logarithmic value and ordering, no fabricated exact
fraction and no mean of daily entropy scores. Preview cards and expanded rows
display this representation and the qualifying participation branch.

Focused verification: six attribution tests, nine Contribution Mix tests,
the existing 39 metric UI/API tests, and 23 canonical metric tests pass. The tests cover exact erosion,
nonduplication, unknown evidence, immutable input, SQL round-trip, qualification
through each branch, separate denominators, full-season minima, incomplete
participation, channel symmetry, unrounded ordering, and agreement with the
canonical Python/SPARQL entropy calculation. An HTTP integration fixture
verifies both qualification routes through the dashboard endpoint and rejects
caller-supplied participation counts. It is synthetic test data, not a live
player population.

## Source investigation and remaining work

USA Baseball's batting guide describes a hitter's responsibility to put the
ball in play and advance the runner in its hit-and-run drill (PDF page 36).
This supports the distinction between a called offensive strategy and the
observed running result; assigning metric damage remains the user's decision.
[USA Baseball batting guide, hosted by Mountain Recreation](https://mountainrec.org/wp-content/uploads/2021/07/USA-Baseball-All-Batting.pdf#page=36).

Explicit confirmation can exist in reporting: Ned Yost directly confirmed
calling a hit-and-run in an MLB account.
[MLB's account](https://www.mlb.com/news/scoring-chance-lost-on-interference-call/c-84315294).
This is a research example of confirmation, not an admitted game input or a
new news-acquisition lane. It does not establish this turn's strikeout example.

A case-insensitive text search of the checked-in `data/raw/samples/` for
`hit[- ]and[- ]run|hitAndRun` found no matches. That narrow search does not
prove that all MLB sources lack confirmation, or that outcome evidence is
missing. Current graph queries have no admitted called-strategy projection.
Source sufficiency, representation and episode alignment therefore remain
unimplemented dependencies, separate from the now-settled damage ownership.

Live player score production, full source conformance and complete selected
populations remain unfinished. These changes do not populate the live
dashboard by themselves. No ontology, object property, RML, source SHACL,
semantic-freeze pin, pipeline topology or acquisition schedule was changed.
