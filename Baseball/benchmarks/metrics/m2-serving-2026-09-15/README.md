# M2 review serving proof

The [result](result.json) records the existing hash-pinned, source-validated
[M1/M2 game output](../m1-m2-mappings-2026-09-15/result.json) passing through
the canonical evidence query in Jena, the review reducer and an isolated SQL
database. It does not acquire data, remap the game or promote a serving build.

All three reviews in game 824315 reach the reducer: the existing play-level
review and both accepted M2 pitch reviews. Their original and operative
decision identities are retained. All three are affirmed, producing zero
reversals among three resolved reviews. The exact SQL and RDF results match.

The old query required a final-result-judgment record link and explicit generic
parent types. The new M2 graph instead scopes its operative review through the
counted Ball/Strike Process and asserts specific disposition types. The query
now follows both accepted contracts without depending on inferred triples.

Focused validation: 11 serving tests and 36 dashboard/API tests pass. Synthetic
regressions cover ball and strike reviews in the same PA, mixed dispositions,
duplicate scope paths, optional inferred parent types, missing containment,
unresolved disposition, exact SQL pooling and shared browser/Python query text.

This proves extraction and serving of explicitly resolved mapped reviews. It
does not admit affected-player qualification, a complete eligible unreviewed
population or a player leaderboard. NiFi retains ownership of source promotion
and refreshed serving materialization; live corpus completion is not asserted.

The focused check is `tests/prove_pitch_review_serving.py`, invoked with the
passed game RDF and installed Java/Jena. It checks the input against the prior
source proof's RDF hash before evaluating the query.
