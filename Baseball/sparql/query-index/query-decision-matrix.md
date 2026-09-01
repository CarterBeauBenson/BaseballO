# Query-index decision matrix

This matrix classifies the 51 authoritative canned queries against query-index
contract version 1. `Index-ready` means the current shortcut graph contains all
facts and dimensions needed to express the same result shape. It does not mean
the canonical query has been migrated or that performance has been proven at
scale.

The accepted performance corpus contains the eight completed 2026-08-03 games
and excludes development fixture `566279`. All nineteen representative indexed
companions return exact corpus row sets. Sixteen reviewed pairs improve by
1.509x to 1923.986x at the median. Three measured pairs remain on the
authoritative route by explicit review.

## Summary

| Classification | Count | Meaning |
| --- | ---: | --- |
| Index-ready | 49 | Contract version 1 can express the complete result shape; equivalence and benchmarks are still required before migration |
| Hybrid | 0 | No current query has a reviewed split execution plan |
| Authoritative | 2 | Required completeness or temporal evidence is intentionally absent from the dehydrated graph |

## Measured migration evidence

These nineteen pairs have exact results across all eight accepted corpus graphs.
`Auto indexed` means the reviewed command-line runner selects that companion
after freshness checks. It is not a silent switch of the canonical query or UI
compiler.

| Representative pair | Median speedup | Decision |
| --- | ---: | --- |
| `hits-by-season` | 799.406x | Auto indexed |
| `hits-by-player-and-venue` | 236.932x | Auto indexed |
| `outcomes-by-player` | 2.648x | Auto indexed |
| `outcomes-by-season` | 1923.986x | Auto indexed |
| `plate-appearances-by-player-and-season` | 55.668x | Auto indexed |
| `three-true-outcomes-by-player` | 1.783x | Auto indexed |
| `extra-base-hits-by-player` | 1.795x | Auto indexed |
| `home-runs-by-player-and-venue` | 1.509x | Auto indexed |
| `multi-hit-games` | 17.472x | Auto indexed |
| `total-bases-by-player-and-season` | 432.406x | Auto indexed |
| `hitless-games-by-player` | 8.118x | Auto indexed; completeness-guarded negative semantics |
| `pitches-by-pitcher-and-venue` | 2.217x | Auto indexed |
| `pitch-summary-by-pitcher` | 4.369x | Auto indexed |
| `batted-balls-by-batter-and-venue` | 3.387x | Auto indexed |
| `events-by-player` | 4.416x | Auto indexed |
| `runs-by-season-and-venue` | 205.897x | Auto indexed |
| `games-by-team-and-season` | 17.498x | Auto authoritative; reviewed conservative route |
| `umpire-assignments` | 1.164x | Auto authoritative |
| `available-players` | 1.021x | Auto authoritative |

Direct TDB2 execution captures corroborate the shape reduction: the new
season-hit pair drops from 15 to 4 TDB2 quad patterns, the player/venue hit pair
drops from 24 to 8, and the runs pair drops from 20 to 7. The normalized logs retain the first execution section and are
evidence about planning behavior, not a substitute for the timing samples.

## All canned queries

| Family | Query | Classification | Index facts or reason |
| --- | --- | --- | --- |
| Root | `hits-by-season.rq` | Index-ready | `HitFact`, `GameFact` |
| Root | `hits-by-season-and-venue.rq` | Index-ready | `HitFact`, `GameFact` |
| Root | `hits-by-player-and-season.rq` | Index-ready | `HitFact`, `GameFact` |
| Root | `hits-by-player-and-venue.rq` | Index-ready | `HitFact`, `GameFact`, labels |
| Root | `hit-types-by-season.rq` | Index-ready | `HitFact.hitType`, `GameFact` |
| Root | `hits-by-game.rq` | Index-ready | `HitFact`, `GameFact` |
| Root | `empty-games-prototype.rq` | Authoritative | Negative classification and the reviewed world-side result-class completeness gate must inspect the full participation/result graph; omitted shortcut facts cannot prove absence |
| Batting | `outcomes-by-season.rq` | Index-ready | `PlateAppearanceResultFact`, `GameFact` |
| Batting | `outcomes-by-player.rq` | Index-ready | `PlateAppearanceResultFact` |
| Batting | `plate-appearances-by-player-and-season.rq` | Index-ready | `PlateAppearanceFact`, `GameFact` |
| Batting | `home-runs-by-player-and-venue.rq` | Index-ready | `HitFact.hitType`, venue |
| Batting | `extra-base-hits-by-player.rq` | Index-ready | `HitFact.hitType` |
| Batting | `total-bases-by-player-and-season.rq` | Index-ready | `HitFact.hitType`, `GameFact` |
| Batting | `multi-hit-games.rq` | Index-ready | `HitFact.agent`, game |
| Batting | `three-true-outcomes-by-player.rq` | Index-ready | `PlateAppearanceResultFact.outcomeClass` |
| Batting | `hitless-games-by-player.rq` | Index-ready | `PlateAppearanceFact` plus absence of `HitFact` within a graph accepted only after complete index-build equivalence |
| Pitching | `pitches-by-pitcher-and-season.rq` | Index-ready | `PitchFact`, `GameFact` |
| Pitching | `pitches-by-pitcher-and-venue.rq` | Index-ready | `PitchFact` |
| Pitching | `pitch-summary-by-pitcher.rq` | Index-ready | `PitchFact`, `PitchCallFact` |
| Pitching | `pitch-types-by-pitcher.rq` | Index-ready | Current reviewed pitch classification on `PitchFact` |
| Pitching | `balls-and-strikes-by-pitcher.rq` | Index-ready | `PitchCallFact.callType` |
| Pitching | `pitches-per-plate-appearance.rq` | Index-ready | `PitchFact.plateAppearance` |
| Pitching | `swings-by-batter.rq` | Index-ready | `BattingActFact.battingActType` |
| Pitching | `batted-balls-by-batter-and-venue.rq` | Index-ready | `ContactFact.battedBall`, agent, venue |
| Pitching | `batted-ball-trajectories.rq` | Index-ready | Current reviewed trajectory classification on `ContactFact` |
| Baserunning | `events-by-player.rq` | Index-ready | `RunnerResolutionFact.sourceEventType` |
| Baserunning | `outs-by-player.rq` | Index-ready | `RunnerResolutionFact.resolutionClass` |
| Baserunning | `resolutions-by-season.rq` | Index-ready | `RunnerResolutionFact`, `GameFact` |
| Baserunning | `runs-by-player-and-season.rq` | Index-ready | `RunnerResolutionFact`, `GameFact` |
| Baserunning | `runs-by-season-and-venue.rq` | Index-ready | `RunnerResolutionFact`, `GameFact` |
| Baserunning | `stolen-bases-by-player.rq` | Index-ready | `StolenBaseFact` |
| Games | `games-by-season-and-venue.rq` | Index-ready | `GameFact` |
| Games | `games-by-season-phase.rq` | Index-ready | `GameFact.seasonPhase` |
| Games | `games-by-team-and-season.rq` | Index-ready | `AssignmentFact`, `GameFact` |
| Games | `home-away-games-by-team.rq` | Index-ready | `AssignmentFact.assignmentType` |
| Games | `matchups-by-season.rq` | Index-ready | Home/away `AssignmentFact`, `GameFact` |
| Games | `umpire-assignments.rq` | Index-ready | `AssignmentFact` with `idx:Umpire` |
| Games | `official-scorer-assignments.rq` | Index-ready | `AssignmentFact` with `idx:OfficialScorer` |
| Games | `game-timeline.rq` | Authoritative | Contract version 1 stores game start but deliberately omits terminal timestamp/boundary evidence |
| Options | `available-seasons.rq` | Index-ready | `GameFact.season` |
| Options | `available-venues.rq` | Index-ready | `GameFact.venue`, labels |
| Options | `available-players.rq` | Index-ready | `PlateAppearanceFact.agent`, labels |
| Options | `available-hit-types.rq` | Index-ready | `HitFact.hitType` |
| Options | `available-games.rq` | Index-ready | `GameFact` |
| Options | `available-pitchers.rq` | Index-ready | `PitchFact.agent`, labels |
| Options | `available-baserunners.rq` | Index-ready | `RunnerResolutionFact.agent`, labels |
| Options | `available-teams.rq` | Index-ready | `AssignmentFact` home/away types |
| Options | `available-umpires.rq` | Index-ready | `AssignmentFact` umpire type |
| Options | `available-official-scorers.rq` | Index-ready | `AssignmentFact` scorer type |
| Options | `available-batting-outcomes.rq` | Index-ready | `PlateAppearanceResultFact.sourceEventType` |
| Options | `available-baserunning-events.rq` | Index-ready | `RunnerResolutionFact.sourceEventType` |

## Migration rule

An `Index-ready` row may move only after an indexed companion returns the same
distinct bindings and aggregates as its authoritative query for every accepted
fixture. Negative queries such as `hitless-games-by-player.rq` additionally
depend on the build-time whole-index equivalence gate; missing facts cannot be
interpreted as meaningful absence.
