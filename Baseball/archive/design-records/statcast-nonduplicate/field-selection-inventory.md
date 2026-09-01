# Field selection inventory

## Classification contract

- **already supplied**: the MLB games source contains the same identifier,
  observation, classification, or measurement; exclude from Statcast mapping;
- **deterministically derivable**: calculate from retained authoritative facts
  under a versioned algorithm; exclude the provider column;
- **identity/join-only**: may support transient matching but does not license a
  world assertion;
- **genuinely additional**: not supplied or deterministically recoverable from
  MLB games and eligible for semantic review;
- **unresolved**: apparent overlap or additional value whose semantics are not
  sufficiently established; stop the field;
- **deprecated**: explicitly retired by the provider; exclude.

The table accounts for 113 unique documented field semantics. `pitcher` and
`fielder_2` are each documented twice but listed once. The second `vy0`
heading is recorded as `vz0` because its official description is explicitly
the z-dimensional velocity.

| Field | Classification | MLB or derivation evidence | Statcast disposition |
|---|---|---|---|
| `pitch_type` | already supplied | `playEvents[*].details.type.code` | exclude |
| `game_date` | already supplied | `gameData.datetime.officialDate` | exclude |
| `release_speed` | unresolved | MLB has `pitchData.startSpeed`, but record-level equivalence to the documented PitchFX-adjusted/Statcast release-velocity eras is unproved | stop and compare |
| `release_pos_x` | unresolved | MLB has trajectory `x0`, velocity, acceleration, and extension, but exact release-plane reconstruction is unproved | stop and compare |
| `release_pos_z` | unresolved | MLB has trajectory `z0`, velocity, acceleration, and extension, but exact release-plane reconstruction is unproved | stop and compare |
| `player_name` | already supplied | player and matchup names; MLB ID remains identity | exclude |
| `batter` | already supplied | `matchup.batter.id` | exclude |
| `pitcher` | already supplied | `matchup.pitcher.id` | exclude |
| `events` | already supplied | plate-appearance `result.event` and `result.eventType` | exclude |
| `description` | already supplied | pitch-event `details.description` | exclude |
| `spin_dir` | deprecated | official CSV documentation marks retired tracking field | exclude |
| `spin_rate_deprecated` | deprecated | replaced by `release_spin` | exclude |
| `break_angle_deprecated` | deprecated | official CSV documentation marks retired tracking field | exclude |
| `break_length_deprecated` | deprecated | official CSV documentation marks retired tracking field | exclude |
| `zone` | already supplied | `pitchData.zone` | exclude |
| `des` | already supplied | plate-appearance `result.description` | exclude |
| `game_type` | already supplied | `gameData.game.type` | exclude |
| `stand` | already supplied | `matchup.batSide.code` | exclude |
| `p_throws` | already supplied | `matchup.pitchHand.code` | exclude |
| `home_team` | already supplied | `gameData.teams.home` | exclude |
| `away_team` | already supplied | `gameData.teams.away` | exclude |
| `type` | already supplied | pitch result code and `isBall`/`isStrike`/`isInPlay` flags | exclude |
| `hit_location` | already supplied | `hitData.location` | exclude |
| `bb_type` | already supplied | `hitData.trajectory` | exclude |
| `balls` | deterministically derivable | ordered pitch-event counts; CSV is pre-pitch while feed count timing must be normalized | derive after equivalence fixture |
| `strikes` | deterministically derivable | ordered pitch-event counts; CSV is pre-pitch while feed count timing must be normalized | derive after equivalence fixture |
| `game_year` | already supplied | game season and official date | exclude |
| `pfx_x` | unresolved | MLB `pitchData.coordinates.pfxX`; likely unit conversion, sign convention unproved | stop and compare |
| `pfx_z` | unresolved | MLB `pitchData.coordinates.pfxZ`; likely unit conversion, sign convention unproved | stop and compare |
| `plate_x` | unresolved | MLB `pitchData.coordinates.pX`; front/middle-of-plate era convention must match | stop and compare |
| `plate_z` | unresolved | MLB `pitchData.coordinates.pZ`; front/middle-of-plate era convention must match | stop and compare |
| `on_3b` | deterministically derivable | ordered runner movements and plate-appearance start state | derive |
| `on_2b` | deterministically derivable | ordered runner movements and plate-appearance start state | derive |
| `on_1b` | deterministically derivable | ordered runner movements and plate-appearance start state | derive |
| `outs_when_up` | deterministically derivable | ordered outs and plate-appearance start context | derive |
| `inning` | already supplied | `allPlays[*].about.inning` | exclude |
| `inning_topbot` | already supplied | `allPlays[*].about.halfInning` | exclude |
| `hc_x` | already supplied | `hitData.coordinates.coordX` | exclude |
| `hc_y` | already supplied | `hitData.coordinates.coordY` | exclude |
| `tfs_deprecated` | deprecated | official CSV documentation marks retired tracking field | exclude |
| `tfs_zulu_deprecated` | deprecated | official CSV documentation marks retired tracking field | exclude |
| `fielder_2` | deterministically derivable | catcher lineup and substitution timeline; exact pitch-time reconstruction needs fixture validation | derive after validation |
| `umpire` | deprecated | official CSV documentation marks retired tracking field | exclude |
| `sv_id` | identity/join-only | documented as non-unique within a game; MLB `playId` and structural identity are authoritative | transient matching only |
| `vx0` | already supplied | `pitchData.coordinates.vX0` at y=50 | exclude |
| `vy0` | already supplied | `pitchData.coordinates.vY0` at y=50 | exclude |
| `vz0` | already supplied | `pitchData.coordinates.vZ0` at y=50; CSV page mislabels heading | exclude |
| `ax` | already supplied | `pitchData.coordinates.aX` | exclude |
| `ay` | already supplied | `pitchData.coordinates.aY` | exclude |
| `az` | already supplied | `pitchData.coordinates.aZ` | exclude |
| `sz_top` | already supplied | `pitchData.strikeZoneTop`; retain operator/ABS era | exclude |
| `sz_bot` | already supplied | `pitchData.strikeZoneBottom`; retain operator/ABS era | exclude |
| `hit_distance` | already supplied | `hitData.totalDistance` | exclude |
| `launch_speed` | already supplied | `hitData.launchSpeed`; distinguish tracked from estimated values | exclude |
| `launch_angle` | already supplied | `hitData.launchAngle`; distinguish tracked from estimated values | exclude |
| `effective_speed` | unresolved | official docs derive it from speed and extension; exact average-extension reference/version is absent | stop pending algorithm evidence |
| `release_spin` | already supplied | `pitchData.breaks.spinRate` | exclude |
| `release_extension` | already supplied | `pitchData.extension` | exclude |
| `game_pk` | already supplied | root `gamePk` / `gameData.game.pk` | exclude |
| `fielder_3` | deterministically derivable | first-base lineup and substitution timeline | derive after validation |
| `fielder_4` | deterministically derivable | second-base lineup and substitution timeline | derive after validation |
| `fielder_5` | deterministically derivable | third-base lineup and substitution timeline | derive after validation |
| `fielder_6` | deterministically derivable | shortstop lineup and substitution timeline | derive after validation |
| `fielder_7` | deterministically derivable | left-field lineup and substitution timeline | derive after validation |
| `fielder_8` | deterministically derivable | center-field lineup and substitution timeline | derive after validation |
| `fielder_9` | deterministically derivable | right-field lineup and substitution timeline | derive after validation |
| `release_pos_y` | unresolved | extension plus field geometry may determine release y, but origin and release-plane convention are unproved | stop and compare |
| `estimated_ba_using_speedangle` | genuinely additional | provider probability from comparable batted balls; 2019+ model may also use sprint speed | retain for review |
| `estimated_woba_using_speedangle` | genuinely additional | provider expected weighted outcome based on a modeled outcome distribution | retain for review |
| `woba_value` | deterministically derivable | actual result plus versioned seasonal wOBA weight | derive |
| `woba_denom` | deterministically derivable | actual result plus versioned wOBA denominator rule | derive |
| `babip_value` | deterministically derivable | actual result and BABIP inclusion rule | derive |
| `iso_value` | deterministically derivable | actual result and total-base rule | derive |
| `launch_speed_angle` | unresolved | launch speed and angle are MLB facts, but only the Barrel subset has an official rule captured here; the full six-value scheme is not determined | exclude field; review a separate Barrel-only derivation |
| `at_bat_number` | deterministically derivable | `about.atBatIndex` plus documented one-based convention | derive |
| `pitch_number` | already supplied | `playEvents[*].pitchNumber` | exclude |
| `pitch_name` | already supplied | `playEvents[*].details.type.description` | exclude |
| `home_score` | deterministically derivable | ordered scoring events; construct pre-pitch state | derive |
| `away_score` | deterministically derivable | ordered scoring events; construct pre-pitch state | derive |
| `bat_score` | deterministically derivable | pre-pitch home/away score plus batting side | derive |
| `fld_score` | deterministically derivable | pre-pitch home/away score plus fielding side | derive |
| `post_home_score` | deterministically derivable | ordered scoring events after pitch | derive |
| `post_away_score` | deterministically derivable | ordered scoring events after pitch | derive |
| `post_bat_score` | deterministically derivable | post-pitch scores plus batting side | derive |
| `if_fielding_alignment` | genuinely additional | provider nominal classification of an actual infield configuration whose player-Site spatial structure is not yet modeled | retain as evidence; block ontology/RML |
| `of_fielding_alignment` | genuinely additional | provider nominal classification of an actual outfield configuration whose player-Site spatial structure is not yet modeled | retain as evidence; block ontology/RML |
| `spin_axis` | unresolved | MLB `pitchData.breaks.spinDirection`; 2D X-Z reference convention must be proved equal | stop and compare |
| `delta_home_win_exp` | deterministically derivable | difference between retained before/after home-win expectancy at PA boundary | derive after expectancy semantics |
| `delta_run_exp` | genuinely additional | provider run-expectancy model output; no equivalent MLB game field | retain for review |
| `hyper_speed` | deterministically derivable | official rule is maximum of 88 mph and launch speed | derive |
| `home_score_diff` | deterministically derivable | home score minus away score | derive |
| `bat_score_diff` | deterministically derivable | batting score minus fielding score | derive |
| `home_win_exp` | genuinely additional | provider probability model output; no equivalent MLB game field | retain for review |
| `bat_win_exp` | deterministically derivable | home-win expectancy plus batting side | derive |
| `age_pit_legacy` | deterministically derivable | pitcher birth date and June 30 reference date | derive |
| `age_bat_legacy` | deterministically derivable | batter birth date and June 30 reference date | derive |
| `age_pit` | deterministically derivable | pitcher birth date and December 31 reference date | derive |
| `age_bat` | deterministically derivable | batter birth date and December 31 reference date | derive |
| `n_thruorder_pitcher` | deterministically derivable | ordered plate appearances and pitcher tenure | derive |
| `n_priorpa_thisgame_player_at_bat` | deterministically derivable | ordered prior plate appearances for batter in game | derive |
| `pitcher_days_since_prev_game` | deterministically derivable | player appearances and game dates | derive |
| `batter_days_since_prev_game` | deterministically derivable | player appearances and game dates | derive |
| `pitcher_days_until_next_game` | deterministically derivable | player appearances and game dates; future-relative analytic | derive |
| `batter_days_until_next_game` | deterministically derivable | player appearances and game dates; future-relative analytic | derive |
| `api_break_z_with_gravity` | unresolved | a retained trajectory may determine it only after the gravity-inclusive reference convention is established | stop pending convention evidence |
| `api_break_x_arm` | unresolved | a retained horizontal break and pitcher handedness may determine it only after the arm-side convention is established | stop pending convention evidence |
| `api_break_x_batter_in` | unresolved | a retained horizontal break and batter side may determine it only after the batter-relative convention is established | stop pending convention evidence |
| `arm_angle` | genuinely additional | shoulder-to-ball line relative to ground at release | retain for review |
| `attack_angle` | genuinely additional | vertical sweet-spot motion direction relative to ground at contact/path intercept | retain as evidence; block pending accepted motion-profile connection and geometry |
| `attack_direction` | genuinely additional | horizontal sweet-spot motion direction relative to home-to-center direction | retain as evidence; block pending accepted motion-profile connection and geometry |
| `swing_path_tilt` | genuinely additional | orientation of fitted final-40-ms swing path relative to ground | retain as evidence; block pending accepted motion-profile connection and fitted-path semantics |
| `intercept_ball_minus_batter_pos_x_inches` | unresolved | nonduplicative provider X component, but subtraction name, distance prose, target Fiat Points, origin, and sign convention do not yet agree | stop |
| `intercept_ball_minus_batter_pos_y_inches` | unresolved | nonduplicative provider Y component, but subtraction name, distance prose, target Fiat Points, origin, and sign convention do not yet agree | stop |

## Count check

| Final bucket | Count |
|---|---:|
| already supplied | 38 |
| deterministically derivable | 41 |
| unresolved | 16 |
| deprecated | 7 |
| identity/join-only | 1 |
| genuinely additional | 10 |
| **total** | **113** |

Uncertainty does not promote a field into the additional set. Release speed,
effective speed, the full six-value `launch_speed_angle` scheme, three API
break conventions, and both signed intercept components remain unresolved and
cannot enter RML.
