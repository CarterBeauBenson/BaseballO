# Player leaderboard display and qualification

On September 14, 2026, the user requested that every dashboard card show
players' names and metric scores, automatically for the selected date range,
with a top-five preview and a fuller view on clicking the card. The user
explicitly rejected a one-appearance player leading merely because that
appearance was a home run.

The assistant asked:

> For the automatic batting minimum, use 3.1 plate appearances per team game
> in the selected range, rounded to the nearest whole PA (3 for one game,
> 22 for seven)? This adapts MLB's qualification approach to the dashboard.

The user answered: **Use that automatic minimum**.

The assistant also asked:

> A PA minimum would exclude most pitchers from defensive and review
> leaderboards. Should those cards use role-appropriate participation
> minimums, with the precise criteria documented before ranking?

The user answered: **Use role-appropriate minimums**.

This is a player-leaderboard display filter. It does not change metric
formulas, PAQ reference populations, source completeness requirements, or
the eligibility of a zero-PA runner for the independent running metrics.
It authorizes no ontology terms, object properties, or source mappings.

The numerical batting minimum is accepted. Specific non-batting minimums
and player attribution for population-level review metrics are not decided
by the second answer. They remain gaps, and must be resolved before those
player rankings can be populated. Supported individual play/run scores
alone do not establish a complete player aggregate.

The MLB reference is the [rate-stat qualification glossary](https://www.mlb.com/glossary/standard-stats/rate-stats-qualifiers).
Applying the rule to an arbitrary selected period is this dashboard's
accepted policy, not a claim that MLB defines these new leaderboards.
