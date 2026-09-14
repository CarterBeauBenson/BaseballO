# Metric presentation verification — September 14, 2026

The [live SQL responses](live-sql-results.json) select regular-season games on
August 25, 2026 and require materialized serving. All three requests succeeded:

| Metric | Exact result | Scope |
| --- | --- | --- |
| TFS | 25/12 | Game 823016, PA source index 40, supported loaded-award consequence |
| Offensive Reach | 4/1 | The same four positively advanced trajectories |
| Adjudication Volatility | 13/23 | Explicitly resolved mapped reviews in the selected 15 games |

The metric response and exact values are unchanged by display annotation.
Existing game-graph labels identify Dylan Beavers and the other runners.
Labels are optional, scoped by graph and entity, and do not supply admission
or change any score. Conflicting or unavailable labels use explicit player IDs.

The [browser check](browser-checks.json) ran the actual page in an isolated
headless Chrome profile. It checked bookmarked dates, live player names and
exact TFS, partial-result labeling, late success and error responses after a
selection change, stale download prevention, and mobile horizontal overflow.
Screenshots were inspected at desktop and mobile widths:

- [Desktop result](desktop.png)
- [Mobile result](mobile.png)

Sixteen focused Node tests and two SPARQL source-scope tests also passed.
The browser harness is `web/tests/metrics-browser-smoke.ps1`; it uses the
running Explorer and the verified example, and does not drive ingestion.

Coverage in the SQL capture is 1,567 observed movements with runner/episode/
record bindings across all 15 games. This confirms the earlier bounded
refresh reached the demonstration day. It does not certify complete runner
histories or full-PA eligibility. Full-PA TFS, population rankings and the
other evidence-gated metrics remain unavailable where their inputs are missing.
