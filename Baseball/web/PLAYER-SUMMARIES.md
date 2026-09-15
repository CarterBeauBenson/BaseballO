# Selected-period player summaries

The accepted [player attribution decisions](../archive/design-records/player-metric-presentation-2026-09-15/user-decision.md)
and [selected-range defaults](../archive/design-records/player-metric-presentation-2026-09-15/selected-range-defaults.md)
govern the public display. The backend retains 20 calculation definitions; the
public catalog, dashboard responses, and examples expose 19. Role-realization
breadth stays in backend computation and evidence.

Every public player headline defaults to a mean over eligible observations in
the selected period, except Empty Games, which is a game count. Single-game
highs and yearly totals are deferred. Individual event evidence retains its
event scope; a supported isolated play cannot become a player mean.

## Trusted serving input

Existing `playerPopulationComplete`, per-row `completeParticipation`, exact
date scope, canonical player identity and qualification gates remain required.
The backend must additionally supply each row's `aggregate`:

```json
{"kind":"mean","sum":{"numerator":"25","denominator":"12"},"count":25}
```

The server computes and reduces the exact mean, here 1/12. A legacy `value`
alone is insufficient: the server must not accidentally display a total as an
average. The count is the number of eligible observations for that metric,
not necessarily the player's official PA count. Percentile observations are
the accepted individual-event percentiles. Rate observations retain their
eligible-event denominator; daily percentages must not be averaged equally.

For Empty Games:

```json
{"kind":"count","count":4,"eligibleGames":8}
```

The player display is 4 games. The backend Empty Game Rate calculation still
returns 1/2, with explicit `components.emptyGames=4` and `eligibleGames=8` retained
through SQL. Public result projection uses those counts, never the reduced
fraction's numerator. The public unit is `games`; `technicalUnit` retains the
backend unit. Missing counts withhold the public result. Zero-PA games remain
excluded under the accepted eligibility rule.

The public examples apply this same count projection. Backend examples retain
the rate calculation for regression checks. Public SQL and RDF responses use
the same projection, and caller-supplied aggregate evidence remains forbidden.

These contracts do not produce missing player populations. Complete source
evidence and non-batting numerical participation thresholds are still required
before their leaderboards can be populated. Existing NiFi fingerprint checks
control materialization after reducer changes; no source freeze is refreshed.

Validation: 36 component Node tests and nine serving tests, including exact
mean arithmetic, unreduced empty-game counts, SQL round trips, visibility,
eligibility, and SQL/RDF response projection. Browser verification checks the
19-card dashboard, selected-period average captions, and count-only Empty
Games example alongside the existing automatic-load and stale-request checks.
