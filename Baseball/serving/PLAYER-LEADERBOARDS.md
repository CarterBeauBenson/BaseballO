# Player leaderboards

The [accepted display and qualification decision](../archive/design-records/metric-leaderboard-qualification-2026-09-14/user-decision.md)
requires names and metric values for the top five qualified players, automatic
loading on page entry and date changes, and a complete list on card selection.

The page loads its restored date selection once after the catalog arrives.
Range changes immediately invalidate old scores/downloads and cancel requests;
400 ms of quiet input starts one shared refresh. Invalid or reversed custom
dates wait for correction. Card selection reuses that response.

The server's `playerLeaderboard` presentation adapter applies the accepted
batting minimum: nearest whole number of `31 * teamGames / 10`, with half
values rounded upward. This gives 3 PA for one team game, 16 for five, 22 for
seven and 502 for 162. The denominator is the player's applicable team-game
exposure throughout the selected range, including games the player missed;
it must not be replaced with games in which the player appeared. Incomplete
schedule/team exposure cannot lower the minimum.

The server sorts qualifying player scores by exact integer cross multiplication.
Metrics whose existing catalog says higher is worse use ascending order;
others use descending order, explicitly labeled. Equal exact values share
a competition rank; player IRI deterministically orders ties. Cards show at
most five rows, and the full list preserves all qualified players. Rounding
is only for display. A one-PA high score is excluded even on a one-game day.

## Serving interface and admission boundary

`playerLeaderboard` consumes only trusted serving results. It does not read
source payloads, infer completeness, average partial plays, or calculate a
new player score. The HTTP request allowlist still rejects evidence,
`playerResults`, arbitrary graphs and completeness declarations.

An admitted adapter must supply `playerPopulationComplete: true` and a
`playerResults` array for the complete applicable player score population.
Each row must carry the metric ID, player IRI, available exact metric value,
matching start/end dates and game set, complete participation evidence, PA
count and team-game count. Optional `playerLabel` is display text only.
Rows must be unique by player. Missing, conflicting or out-of-scope evidence
withholds the ranking. These interface flags serialize an independently
established admission result; setting a flag is not an admission procedure.
Complete reference populations remain required for PAQ before this display
minimum is applied.

The normalized `leaderboard` output contains qualification policy, status,
message, gap codes and every ranked row. Qualification removes low-PA rows
only after complete scores and participation have been admitted. An empty
qualified population is distinct from unavailable player scores. Current
individual Walk/HBP and run-history results remain inspectable separately.

## Still blocked

This release implements qualification and presentation, **not live player
score production**. The existing metric adapters do not yet emit the complete
`playerResults` interface. Consequently the current live cards have no player
leaders; they explain that complete player scores are unavailable. The
isolated seven-player browser fixture is a UI test, not live baseball data.

1. Complete player aggregates and their full applicable game/PA/run populations
   must be supplied through the accepted source-to-SQL lifecycle. Partial award
   consequences and nine of thirteen scoring histories do not qualify.
2. Complete selected-period participation and team-game exposure must be
   established, including absent games and applicable multi-team history.
   Missing graphs cannot silently shrink qualification denominators.
3. Exact non-batting participation thresholds are still unspecified. The
   user approved role-specific minima, not particular numbers. Running,
   defensive, mixed-role and review cards remain withheld at that boundary.
4. A review-population ratio does not assign a score to a player. Any missing
   player attribution or aggregation policy for non-player metric grains
   needs its own explicit decision; the card layout does not authorize it.

No ontology, RML, SHACL, metric kernel, semantic-freeze pin or reference
population was changed. Source-proof recovery and corpus refresh remain
separate prerequisites described in [production readiness](../infra/PRODUCTION-READINESS.md).
