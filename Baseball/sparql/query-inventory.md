# SPARQL query inventory

This inventory records what each of the 48 canned queries counts or discovers
after the granular RML event-pattern revision. `Aligned` means the query uses
the full mapped pattern described here; it does not mean that result totals
have yet been accepted as a baseball statistic.

| Family | Query | Counted or returned entity | Required evidence and principal joins | Filters or dimensions | Status |
| --- | --- | --- | --- | --- | --- |
| Root | `hits-by-season.rq` | Distinct hit result and game | Specific hit class + `HitJudgmentAct`; result to plate appearance to game | Season | Aligned |
| Root | `hits-by-season-and-venue.rq` | Distinct hit result | Hit pattern; plate appearance to game; game to field/site/venue | Season, venue | Aligned |
| Root | `hits-by-player-and-season.rq` | Distinct hit result | Hit pattern; `BatterAct` participant; plate appearance to game | Season, player | Aligned |
| Root | `hits-by-player-and-venue.rq` | Distinct hit result | Hit pattern; batter; plate appearance to game and venue | Season, player, venue | Aligned |
| Root | `hit-types-by-season.rq` | Distinct hit result | Specific hit class mapped to label + `HitJudgmentAct` | Season, hit type | Aligned |
| Root | `hits-by-game.rq` | Distinct hit result | Hit pattern; plate appearance containment; game venue | Game | Aligned |
| Root | `empty-games-prototype.rq` | Candidate player/game pair | Batter participation plus reviewed contribution patterns; 17-result completeness gate | Player, game | Aligned prototype |
| Batting | `outcomes-by-season.rq` | Distinct PA result | Generic result + one of 17 specific classes + adjudication; PA to game | Season, outcome | Aligned |
| Batting | `outcomes-by-player.rq` | Distinct PA result | Outcome pattern + `BatterAct` participant | Player, outcome | Aligned |
| Batting | `plate-appearances-by-player-and-season.rq` | Distinct plate appearance | `BatterAct` participant; PA containment to game | Season, player | Aligned |
| Batting | `home-runs-by-player-and-venue.rq` | Distinct home-run result | `HomeRunProcess` + `HitJudgmentAct`; batter; game venue | Player, venue | Aligned |
| Batting | `extra-base-hits-by-player.rq` | Distinct result | Double/triple/home-run class + `HitJudgmentAct`; batter | Player | Aligned |
| Batting | `total-bases-by-player-and-season.rq` | Sum of class weights | Hit class + `HitJudgmentAct`; batter; PA to game | Season, player | Aligned |
| Batting | `multi-hit-games.rq` | Distinct hit result per player/game | Hit pattern; batter; PA containment | Game, player; HAVING >= 2 | Aligned |
| Batting | `three-true-outcomes-by-player.rq` | Distinct result | Home run/walk/strikeout class + adjudication; batter | Player | Aligned |
| Batting | `hitless-games-by-player.rq` | Distinct participating game | Batter participation with no hit-pattern result for that player/game | Player | Aligned |
| Pitching | `pitches-by-pitcher-and-season.rq` | Distinct `PitchAct` | Pitcher participant; pitch precedes `PitchBallMotionProcess`; PA to game | Season, pitcher | Pattern aligned; RML join coverage limited |
| Pitching | `pitches-by-pitcher-and-venue.rq` | Distinct `PitchAct` | Pitch pattern; enclosing game and venue | Pitcher, venue | Pattern aligned; RML join coverage limited |
| Pitching | `pitch-summary-by-pitcher.rq` | Distinct pitch/call processes | Pitch pattern; shared event record joins pitch to ball/strike process and judgment | Pitcher | Pattern aligned; RML join coverage limited |
| Pitching | `balls-and-strikes-by-pitcher.rq` | Distinct call process | Shared event record; ball, strike, or foul-tip judgment pattern | Pitcher, call type | Pattern aligned; RML join coverage limited |
| Pitching | `pitches-per-plate-appearance.rq` | Distinct pitch and PA | Pitch pattern; pitch specifically depends on plate appearance | Pitcher | Pattern aligned; RML join coverage limited |
| Pitching | `swings-by-batter.rq` | Distinct `SwingAct` | Batter participant | Player | Pattern aligned; RML join coverage limited |
| Pitching | `batted-balls-by-batter-and-venue.rq` | Distinct batted-ball motion | Swing/bunt precedes contact; contact precedes motion; batter; game venue | Player, venue | Pattern aligned; RML join coverage limited |
| Baserunning | `events-by-player.rq` | Distinct runner resolution | Runner participant + out/safe/run judgment; shared source record supplies event label | Player, event type | Aligned |
| Baserunning | `outs-by-player.rq` | Distinct out resolution | `RunnerResolutionProcess` + `OutProcess` + `OutJudgmentAct`; participant | Player | Aligned |
| Baserunning | `resolutions-by-season.rq` | Distinct runner resolution | Run/out/safe class paired with corresponding judgment; game time | Season, resolution | Aligned |
| Baserunning | `runs-by-player-and-season.rq` | Distinct run resolution | `RunProcess` + `RunJudgmentAct`; participant; game time | Season, player | Aligned |
| Baserunning | `runs-by-season-and-venue.rq` | Distinct run resolution | Run pattern; enclosing game and venue | Season, venue | Aligned |
| Baserunning | `stolen-bases-by-player.rq` | Distinct stolen-base resolution | `StolenBaseProcess` + `StolenBaseJudgmentAct`; participant | Player | Aligned |
| Games | `games-by-season-and-venue.rq` | Distinct game | Game start; game to field/site/venue | Season, venue | Aligned |
| Games | `games-by-team-and-season.rq` | Distinct game | Team bears contextual home/away role realized in game | Season, team | Aligned |
| Games | `home-away-games-by-team.rq` | Distinct game | Contextual role class and realization in game | Team, side | Aligned |
| Games | `matchups-by-season.rq` | Distinct game | Home and away team roles both realized in game | Season, matchup | Aligned |
| Games | `umpire-assignments.rq` | Distinct game | Person bears umpire role realized in game | Umpire | Aligned |
| Games | `official-scorer-assignments.rq` | Distinct game | Person bears scorer role realized in game | Official scorer | Aligned |
| Games | `game-timeline.rq` | Game timestamps | Timestamp describes game and designates its boundary instant; maximum mapped end value is the current terminal-time convention | Game | Aligned; source-specific end selection limited |
| Options | `available-seasons.rq` | Distinct year | Loaded game start | Season | Aligned |
| Options | `available-venues.rq` | Distinct venue | Game to field/site/venue | Venue | Aligned |
| Options | `available-players.rq` | Distinct batter | `BatterAct` participant | Player | Aligned |
| Options | `available-hit-types.rq` | Distinct hit label | Hit class + `HitJudgmentAct` | Hit type | Aligned |
| Options | `available-games.rq` | Distinct game | Game start and venue | Game | Aligned |
| Options | `available-pitchers.rq` | Distinct pitcher | Pitcher participant; pitch precedes ball motion | Pitcher | Pattern aligned; RML join coverage limited |
| Options | `available-baserunners.rq` | Distinct runner | Runner resolution participant + run/out/safe judgment | Player | Aligned |
| Options | `available-teams.rq` | Distinct team | Home/away role realized in a game | Team | Aligned |
| Options | `available-umpires.rq` | Distinct umpire | Umpire role realized in a game | Umpire | Aligned |
| Options | `available-official-scorers.rq` | Distinct scorer | Scorer role realized in a game | Official scorer | Aligned |
| Options | `available-batting-outcomes.rq` | Distinct outcome label | One of 17 result classes + generic adjudication | Outcome | Aligned |
| Options | `available-baserunning-events.rq` | Distinct source event label | Runner resolution + run/out/safe judgment + shared source record | Event type | Aligned |

## Shared counting rules

- Count the domain individual named in the third column, not every record,
  act, process, judgment, decision, or call generated from the same source
  event.
- Use `COUNT(DISTINCT ...)` across joins that can expose more than one evidence
  individual.
- Derive season from the mapped first-pitch/game-start timestamp until the
  source season field is mapped.
- Treat runner-record-to-plate-appearance attribution as unavailable; do not
  invent that join in a query.
- Do not accept pitching totals until the selected RML processor's nested
  pitch-to-play joins cover all pitch events. The fixture currently exposes
  only terminal matching events through those joins.
