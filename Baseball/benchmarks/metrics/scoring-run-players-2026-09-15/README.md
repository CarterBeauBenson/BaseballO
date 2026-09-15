# Scoring-run player producer and refresh recovery

The existing whole-game RML/SHACL output for game 824087 was independently
checked with the new source-owned scoring-run admission profile. All seven
counted runs and 52 roster members reconcile; Jena SHACL conforms. The input
and RDF hashes match the earlier walk-off proof. No raw source was changed.

The new serving producer reconciles all selected games, the counted-run
population, C1 scoring histories and roster exposure before returning exact
scorer means. It is conditional: game 824087 still has incomplete histories
outside the supported walk-off half. A successful counted-run census cannot
turn those incomplete histories into player scores.

Focused checks passed: 8 new source/SHACL/player integration tests, 35 existing
run/metric/batting-serving tests, 40 dashboard/API tests and 29 NiFi recovery
tests. Counterexamples cover a missing or extra run, wrong scorer, missing
roster, zero runs, missing schedule/proof/history, exact means without PA
requirements, retained non-scoring game exposure and SQL proof corruption.

Recovery now preserves a fully completed obsolete proof and queues a current
proof through the existing NiFi processor. Missing completion, failed
conformance, quarantine and ambiguous dispatch do not license retries. No
healthy NiFi run was polled or manually resubmitted for this change.

The new admission runs in the existing source SHACL stage before promotion;
the materializer verifies promotion-bound evidence. NiFi owns the refresh.
This is implementation evidence, not a live dashboard completion claim.
