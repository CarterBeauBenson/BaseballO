# Defensive and PAQ-2.1 serving integration

The existing-term defensive query now retains particular acts, actual agents,
persistent Fielder Roles and supported precedence. Hash-checked SQL inputs feed
participating-defender averages with independent selected-schedule and roster
proofs. Duplicate superclass types count once; separate throws remain separate.
Breadth does not require temporal order; depth does. Unknown plays stay in the
whole-play census and prevent partial player means.

PAQ with Tie-Breakers now has a SQL consumer. It joins admitted contribution,
recovery and defensive inputs by graph, game, PA and actual player; preserves
known inapplicability; rejects ambiguous multiple defensive resolutions; ranks
Recovery using all eligible season PAs; then calculates PAQ-2.1 percentiles
within its applicable reference before selected-date means. Exact fractions,
official PA qualification counts and missed-game exposure survive SQL.

These are tested consumers, not new live source producers. The NiFi materializer
does not yet supply a defensive source admission, so the live defensive and
dependent PAQ-2.1 population remains withheld. No ontology, RML, object property,
source identity policy, semantic freeze or acceptance status changed.

## Verification

Focused Python modules: `test_defensive_serving` (8), `test_paq21_serving` (7),
`test_metric_suite_serving` (11), `test_nonbatting_player_summaries` (7),
`test_paq21_player_summaries` (4), `test_metric_dashboard` (4),
`test_recovery_players` (4), owning-source `test_review_inventory` (4), and
`test_review_player_evidence` (7). The shared dashboard test now compares each
SQL card with the individual SQL request and explicitly rejects player results
without admission; a raw graph inventory is not equated with the admitted SQL
response. All 43 web metric-suite tests pass using pinned Node 24.21.0.
PowerShell parsing of the changed NiFi stage passes.

The [real-game Jena/SQL check](review-query.json) reuses the existing passed
822773 RDF and unchanged source. It preserves two affected batters exactly and
does not promote any corpus. The complete-source-defensive tests are synthetic
consumer fixtures and must not be mistaken for a real defensive admission.

The local UI liveness check returned 200; materialized readiness returned 503
during development. Its existing asynchronous NiFi recovery owns regeneration
and publication. No healthy-run polling or manual corpus materialization was
performed. This report does not claim that the dashboard is finished.

## Review source coverage found during integration

The [source inventory](review-inventory.json) keeps six review observations:
five provider-code `MJ` records and one `MO`. A pitch-only scan found four `MJ`
records; the fifth is `allPlays[15].reviewDetails`. It records the challenged
terminal strikeout with Carter Jensen as batter and Brandon Valenzuela as
reported challenger. These are different people. Three `MJ` overturns and two
affirmations reconcile with the reported final ABS counters in this fixture.
No undocumented provider code is translated into an RDF mechanism here.

The current canonical query finds three resolved RDF reviews, with affected
players supported for the two affirmed pitch reviews. The legacy terminal
review lacks the shared reviewed-motion subject path. Two event-level
overturns and the foul review remain outside that graph surface. M2 expressly
excluded event-level overturns and interpretation of undocumented mechanism
codes. Their presence in source does not authorize expanding that contract.

NiFi now retains this diagnostic inventory with source and implementation
hashes alongside its source checks and promotion evidence, before raw cleanup.
It neither changes source SHACL admission nor grants review-population
completeness. Repeated observations remain visible for identity reconciliation.

Official ABS eligibility requires an adverse called pitch, remaining challenge
capacity, and applicable operational conditions; final counters alone do not
establish each decision's eligibility.
[MLB's ABS definitions](https://baseballsavant.mlb.com/abs-metrics-documentation).

## Review boundary

[D1](../../../archive/design-records/mlb-game-defensive-acts/README.md) is the concrete draft
defensive mapping/identity package. The attempted retrospective acceptance
record was rejected by automatic review and removed. This draft records no
approval. [M3/M4](../../../archive/design-records/mlb-game-counted-foul-completion/README.md)
is still separately pending. Existing formulas, full-population requirements,
qualification minima and source ownership are unchanged.
