# Run depth segment-origin correction

Metric suite 2.0.11 uses the actual segment-origin designation when counting
state-changing episodes. The separate batter-consequence HOME=0 convention
continues to apply to its existing calculation scope. It cannot reset every
later segment during the batter's own PA to home.

Regression: reach first, stay at first during the same PA, then score later.
The depth is two, with three observed episodes. Further movement from first
to second still counts once. Conflicting or unidentified designated origins
withhold the result instead of falling back to HOME=0. Two personal histories
claiming the same counted Run cannot produce duplicate scores.

The adapter now returns an `unresolvedRuns` inventory and `runGapCounts`,
identifying each counted Run without a score and its specific evidence failure.
The dashboard retains those runs in the selected population and displays their
reasons. This does not admit incomplete histories or a partial player aggregate.

[The real-game result](result.json) was reproduced from the existing retained
31,717-triple proof RDF for game 566279 using the canonical Jena evidence query
and exact SQL round trip. Nine of thirteen observed runs remain supported;
Wilmer Flores retains depth 3/1. The four unresolved Run identities are now
explicit. No new acquisition, RML transformation, source promotion, vocabulary
or semantic approval was performed for this focused developer check.

NiFi's queued source recovery was updated to wait for the current SQL job to
become idle, then let the normal proof's materialization stage rebuild serving
with the corrected metric fingerprint. The obsolete build is not required to
promote. The existing RML, SHACL, promotion, materialization and cleanup proof
gate still controls the subsequent bounded August 25 refresh.

Full player leaderboards remain incomplete. This correction and exact missing-
run inventory do not supply the missing consequence-boundary, complete PA,
defensive or review populations.
