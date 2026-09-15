# Walk-off runner boundary: bounded proof

The existing question 8 acceptance was published in `b4d4f88`; its scoped
[record](../../../archive/design-records/walkoff-runner-boundary/review.json)
was pushed as `4c2c899` before implementation.

Game 824087, July 20, 2026, ends on a ninth-inning bunt with one actual out in
the half. The final half previously failed only the third-out termination
gate. Full source reconciliation now admits three histories: Josh Rojas
scores; Tyler Tolbert and Nick Loftin remain supported at second and first.
The latter two personal intervals end at the existing game-ending instant.
No additional out, score, advance, physical location or stasis is created.

Actual RMLMapper output for the final half passes the source C1 shape and
rejects foreign endpoints, missing timestamps, extra endpoints and invented
terminal outs. The canonical SPARQL query and SQL round trip preserve the two
game-ending boundaries. Rojas's complete scoring history yields exact **Run
Construction Depth 4**: the four separately supported 0-to-1, 1-to-2, 2-to-3
and 3-to-home advances. That individual result survives SQL; it does not
certify a complete player population or release a leaderboard.

The whole immutable game passes actual RMLMapper 8.1.0 and the complete Jena
authoritative source SHACL profile: **29,175 triples, 73 PAs, 73 Batter Acts,
267 pitches, seven personal histories and eleven episode memberships**.
Two histories end at the game boundary. The source-to-RDF inventory checks
pass, and SHACL reports zero violations. The [result](result.json) pins the
actual artifacts. This developer proof promoted no graph.

The home-run counterexample retains both counted scoring histories, including
the batter's. Final-state contradictions, inconsistent score transitions,
missing terminal identity/time and later events reject a proposed boundary.
Unresolved reviews and placed-runner entries still withhold their halves.
The existing official game endpoint is reused; a source timestamp is not
copied into an invented runner-motion duration.

Focused checks: five walk-off source/RML/SHACL/query/SQL tests, nine existing
history tests, three existing C1 conformance tests and thirty-nine metric
UI/API tests passed. The initial strict-RML optional-reference failure was
fixed with a source-filtered endpoint map. Selective PySHACL testing now targets
the C1 shape explicitly, and the constraint uses the existing asserted
Baseball Game Temporal Interval class. The full Jena profile independently
checks the complete graph. No failed proof was promoted or relabeled.

The existing NiFi lane owns promotion, corpus refresh and serving
materialization asynchronously. Daily acquisition remains enabled. Complete
count/defensive histories, eligibility and player/reference populations remain
separate implementation work.
