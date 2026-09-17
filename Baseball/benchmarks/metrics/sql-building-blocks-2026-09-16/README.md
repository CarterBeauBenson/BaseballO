# SQL metric building blocks: bounded developer proof

The read-only check used the already promoted graph for game **823585**, with
its current promotion-bound admission proofs. It issued the canonical evidence
SELECT once, projected its results into an isolated in-memory database, and
compared the existing evidence reader with the indexed-input reader.

The [retained result](result.json) records graph, promotion, implementation,
query and normalized-evidence hashes. All **20 metric responses matched
exactly**, excluding the new diagnostic `buildingBlockCoverage` field. All
per-game results and five input families also passed their SQL round trips.

| Measurement | Result |
| --- | ---: |
| Normalized graph bindings | 1,568 |
| Compact scope facts | 340 |
| Projected input observations | 79 |
| Compact metric results | 20 |
| Existing evidence reader | 676.928 ms |
| Stored-input reader | 48.688 ms |

This single sequential measurement is approximately 13.9 times faster. It is
not a full-season benchmark, HTTP timing, production build or leaderboard
readiness claim. Both reader timings exclude acquisition and materialization.
The larger fixture suite separately exercises complete positive populations,
two-game pooling, missing/corrupt observations and prepared season ranks.

Current batting and scoring-run proofs were admitted. Runner resolution,
pitch counts, PA boundaries and defense remained withheld under the current
promoted proof implementations. Progress projection retained 79 observations
and three unresolved observations. The test deliberately supplied no independent
schedule admission, so it did not establish a complete public date range.
These limitations are preserved in the result, not repaired by assuming that
missing inputs are zero.

The reusable developer command is `tests/prove_metric_building_blocks.py`.
It does not run acquisition, mapping, graph promotion or the routine corpus
workflow. NiFi owns builds and publication of the new stored-input reader.
