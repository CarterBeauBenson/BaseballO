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

## Backend PA-mean reducer and participation inventory

Suite 2.0.15 adds `summarize_batting_players` for the accepted PA-mean metrics.
It requires an independent expected observation census, complete PA scores,
official PA totals and independently established applicable team-game exposure.
Missing, extra, conflicting, partial or differently scoped score rows cannot
produce a player population. Exact duplicates are idempotent. Official PA
credit is not inferred from the number of metric observations. Zero-official-PA
players remain ineligible for batting summaries. Empty Games and non-PA means
are outside this reducer.

The mean is the exact sum of individual scores divided by their count, with
the sum/count retained for the public projection. Qualification uses the
separate official total and the complete team-game list, including missed
games, team changes and distinct games in a doubleheader. The reducer consumes
those independently admitted inputs; it does not invent their graph paths.
The existing server remains the owner of qualification and ranking.

The canonical evidence query now extracts actual PA/Batter Act/realized
Batter Role/bearer links, including PAs without a resolved bearer. Every live
result retains `coverage.battingParticipation`: per-player observed PA counts,
unassigned PAs and ambiguous PAs. These are participation observations, not
official totals. Both official-credit and team-exposure verification flags
remain false until owning source contracts can establish them.

The [real-game proof](../benchmarks/metrics/batting-participation-2026-09-15/README.md)
checks 77 observations for 20 players through Jena and SQL and compares their
counts with the immutable boxscore. A separate real interrupted-turn example
shows why count equality cannot become a general attribution policy.

The PA-mean reducer is implemented and tested, including direct Python output
through the JavaScript qualification code. **It is not called by a live scoring
adapter yet:** complete PA scores, official-credit membership and applicable
team-game exposure remain prerequisites. No qualified real-player leaderboard
is produced by this change, and no HTTP caller can provide these facts.

Suite 2.0.16 additionally transports existing adjudicated batting-result
Process/Act/Decision/Record paths and game realization of team-context Player
Roles. It preserves missing team contexts and does not infer membership from
a role's mere existence or from adjacent games. The
[real-game context proof](../benchmarks/metrics/batting-context-2026-09-15/README.md)
finds all 52 source roster pairs, including 32 players with no batting result.
The basic exposure path therefore exists. Conditional use for qualification
was accepted in [B1](../archive/design-records/batting-leaderboard-admission/README.md)
on 2026-09-15. Implementation must still establish its game and population proofs. The new `player_team_game` evidence grain
is derived SQL/query structure, not an RDF predicate or a public role metric.

Validation: 36 component Node tests and nine serving tests, including exact
mean arithmetic, unreduced empty-game counts, SQL round trips, visibility,
eligibility, and SQL/RDF response projection. Browser verification checks the
19-card dashboard, selected-period average captions, and count-only Empty
Games example alongside the existing automatic-load and stale-request checks.

## B1 qualification implementation ? 2026-09-15

Suite 2.0.17 adds the accepted conditional qualification adapter. NiFi now
reconciles official PA credit and full game rosters in the source SHACL stage,
retains promotion-bound proof hashes, and captures independent schedule
coverage. SQL counts remain projections of the canonical RDF query, including
zero-PA roster members and distinct game/team pairs. Missing games or dates
cannot lower the minimum. See the [real source/graph/SQL proof](../benchmarks/metrics/batting-admission-2026-09-15/README.md).

This closed B1's implementation gate. The subsequent
[B2 contact continuation decision](../archive/design-records/contact-play-continuation-membership/README.md)
is also accepted and implemented. Qualified counts alone are not metric scores:
complete supported populations are still required for player rankings. See
[current readiness](../serving/METRIC-READINESS.md) for the remaining inputs and
publication status.
