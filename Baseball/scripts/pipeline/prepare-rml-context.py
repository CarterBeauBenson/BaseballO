#!/usr/bin/env python3
"""Create an isolated ancestor-aware JSON context for RMLMapper execution."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


SAFE_IRI_SEGMENT = re.compile(r"^[A-Za-z0-9._~-]+$")
CONTEXT_KEY = "_baseballO"
REVIEW_DESCRIPTION = re.compile(
    r"^(?P<initiator>.+?) (?P<action>challenged|reviewed) \((?P<review_type>[^)]+)\), call on the field was "
    r"(?P<status>confirmed|overturned|upheld):",
    re.IGNORECASE,
)
PITCH_DECISION_BY_CALL_CODE = {
    "B": "ball",
    "*B": "ball",
    "C": "strike",
}
BUNT_CALL_CODES = {"L", "M", "O"}
BUNT_TRAJECTORIES = {"bunt_grounder", "bunt_popup", "bunt_line_drive"}
ADMINISTRATIVE_EVENT_TYPES = {"game_advisory"}
PITCH_TYPE_CATEGORY_BY_CODE = {
    "FF": "FourSeamFastballPitchTypeICE",
    "SI": "SinkerPitchTypeICE",
    "FC": "CutterPitchTypeICE",
    "SL": "SliderPitchTypeICE",
    "ST": "SweeperPitchTypeICE",
    "SV": "SlurvePitchTypeICE",
    "CU": "CurveballPitchTypeICE",
    "KC": "KnuckleCurvePitchTypeICE",
    "CS": "SlowCurvePitchTypeICE",
    "CH": "ChangeupPitchTypeICE",
    "FS": "SplitterPitchTypeICE",
    "FO": "ForkballPitchTypeICE",
    "SC": "ScrewballPitchTypeICE",
    "KN": "KnuckleballPitchTypeICE",
    "EP": "EephusPitchTypeICE",
}
BATTED_TRAJECTORY_CATEGORY_BY_TOKEN = {
    "ground_ball": "GroundBallTrajectoryICE",
    "line_drive": "LineDriveTrajectoryICE",
    "fly_ball": "FlyBallTrajectoryICE",
    "popup": "PopUpTrajectoryICE",
}
SEASON_PHASE_BY_GAME_TYPE = {
    "S": ("preseason", "BaseballPreseasonPhase", "PreseasonSegmentTypeICE"),
    "R": ("regular-season", "BaseballRegularSeasonPhase", "RegularSeasonSegmentTypeICE"),
    "F": ("postseason", "BaseballPostseasonPhase", "PostseasonSegmentTypeICE"),
    "D": ("postseason", "BaseballPostseasonPhase", "PostseasonSegmentTypeICE"),
    "L": ("postseason", "BaseballPostseasonPhase", "PostseasonSegmentTypeICE"),
    "W": ("postseason", "BaseballPostseasonPhase", "PostseasonSegmentTypeICE"),
    "C": ("postseason", "BaseballPostseasonPhase", "PostseasonSegmentTypeICE"),
    "P": ("postseason", "BaseballPostseasonPhase", "PostseasonSegmentTypeICE"),
    "A": ("all-star", "BaseballAllStarPhase", "AllStarSegmentTypeICE"),
}
OUT_SAFE_REVIEW_TYPES = {
    "catch_or_drop",
    "force_play",
    "play_at_1st",
    "tag_play",
    "tag_up_play",
}


def require_numeric(value: object, label: str) -> str:
    rendered = str(value if value is not None else "")
    if not rendered.isdigit():
        raise ValueError(f"{label} must be a numeric identifier, got {value!r}")
    return rendered


def require_segment(value: object, label: str) -> str:
    rendered = str(value if value is not None else "")
    if not SAFE_IRI_SEGMENT.fullmatch(rendered):
        raise ValueError(f"{label} is not a safe IRI segment: {value!r}")
    return rendered


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    return parser.parse_args()


def unique_player_ids_by_name(document: dict[str, object]) -> dict[str, str]:
    candidates: dict[str, set[str]] = {}
    players = document.get("gameData", {}).get("players", {})
    for player in players.values():
        player_id = player.get("id")
        full_name = player.get("fullName")
        if player_id is None or not isinstance(full_name, str) or not full_name.strip():
            continue
        candidates.setdefault(full_name.strip().casefold(), set()).add(str(player_id))
    return {
        name: next(iter(player_ids))
        for name, player_ids in candidates.items()
        if len(player_ids) == 1
    }


def final_review_decision(
    review_type: str,
    play: dict[str, object],
    pitch_events: list[dict[str, object]],
) -> str | None:
    if review_type == "pitch_result":
        if not pitch_events:
            return None
        call_code = pitch_events[-1].get("details", {}).get("call", {}).get("code")
        return PITCH_DECISION_BY_CALL_CODE.get(str(call_code))

    if review_type not in OUT_SAFE_REVIEW_TYPES:
        return None

    runners = play.get("runners", [])
    if len(runners) != 1:
        return None
    is_out = runners[0].get("movement", {}).get("isOut")
    if is_out is True:
        return "out"
    if is_out is False:
        return "safe"
    return None


def main() -> None:
    args = parse_args()
    document = json.loads(args.source.read_text(encoding="utf-8"))
    if CONTEXT_KEY in document:
        raise ValueError(f"Source root already contains reserved key {CONTEXT_KEY!r}")

    plays = document.get("liveData", {}).get("plays", {}).get("allPlays", [])
    if not plays:
        raise ValueError("Source has no liveData.plays.allPlays records")

    status = document.get("gameData", {}).get("status", {})
    metadata = document.get("metaData", {})
    final_corroborated = (
        status.get("abstractGameState") == "Final"
        or status.get("codedGameState") == "F"
        or "game_finished" in metadata.get("gameEvents", [])
        or any(
            item in {"gameStateChangeToFinal", "gameStateChangeToGameOver"}
            for item in metadata.get("logicalEvents", [])
        )
    )
    if not final_corroborated:
        raise ValueError("Game end is not corroborated by final/game-over source state")
    terminal_baseball_plays = [
        play
        for play in plays
        if play.get("result", {}).get("eventType") not in ADMINISTRATIVE_EVENT_TYPES
        and (
            play.get("playEvents")
            or play.get("runners")
            or play.get("about", {}).get("isComplete") is True
        )
        and isinstance(play.get("about", {}).get("endTime"), str)
    ]
    if not terminal_baseball_plays:
        raise ValueError("Final game has no terminal baseball event with an endTime")
    final_end_time = terminal_baseball_plays[-1].get("about", {}).get("endTime")
    if not isinstance(final_end_time, str) or not final_end_time.strip():
        raise ValueError("Final play has no about.endTime")
    game_pk = require_numeric(document.get("gamePk"), "Root gamePk")
    game_data = document.get("gameData", {})
    game_description = game_data.get("game", {})
    season = require_numeric(game_description.get("season"), "gameData.game.season")
    provider_version = require_segment(
        metadata.get("timeStamp"), "metaData.timeStamp"
    )
    provider_reference_root = (
        "https://baseballontology.org/data/reference-system/mlb-game/"
        f"{provider_version}"
    )
    root_context: dict[str, object] = {
        "gameEndTime": final_end_time,
        "pitchTypeReferenceSystemIri": f"{provider_reference_root}/pitch-types",
        "pitchTypeReferenceSystemLabel": (
            f"MLB pitch-type reference system observed {provider_version}"
        ),
        "battedTrajectoryReferenceSystemIri": (
            f"{provider_reference_root}/batted-ball-trajectories"
        ),
        "battedTrajectoryReferenceSystemLabel": (
            f"MLB batted-ball trajectory reference system observed {provider_version}"
        ),
    }
    game_type = str(game_description.get("type") or "")
    phase_definition = SEASON_PHASE_BY_GAME_TYPE.get(game_type)
    if phase_definition is not None:
        phase_key, phase_class, category = phase_definition
        root_context["seasonPhase"] = {
            "iri": f"https://baseballontology.org/data/season/{season}/phase/{phase_key}",
            "classIri": f"https://baseballontology.org/{phase_class}",
            "categoryIri": f"https://baseballontology.org/{category}",
            "referenceSystemIri": f"{provider_reference_root}/season-segments",
            "referenceSystemLabel": (
                f"MLB season-segment reference system observed {provider_version}"
            ),
            "seasonIri": f"https://baseballontology.org/data/season/{season}",
            "gameIri": f"https://baseballontology.org/data/game/{game_pk}",
            "gameTypeCode": game_type,
        }
    document[CONTEXT_KEY] = root_context
    player_ids_by_name = unique_player_ids_by_name(document)

    roster_player_count = 0
    boxscore_teams = (
        document.get("liveData", {}).get("boxscore", {}).get("teams", {})
    )
    for side in ("away", "home"):
        team_boxscore = boxscore_teams.get(side, {})
        team_id = require_numeric(
            team_boxscore.get("team", {}).get("id"),
            f"Boxscore {side} team.id",
        )
        for roster_key, roster_player in team_boxscore.get("players", {}).items():
            if CONTEXT_KEY in roster_player:
                raise ValueError(
                    f"Roster player {roster_key} already contains reserved key {CONTEXT_KEY!r}"
                )
            require_numeric(
                roster_player.get("person", {}).get("id"),
                f"Boxscore {side} roster player {roster_key} person.id",
            )
            roster_player[CONTEXT_KEY] = {"teamId": team_id}
            roster_player_count += 1

    pitch_count = 0
    runner_count = 0
    terminal_pitch_count = 0
    review_count = 0
    institutional_pitch_classification_count = 0
    uncaught_third_strike_count = 0
    occupied_base_count = 0
    seen_pitch_ids: set[str] = set()
    current_half_inning: tuple[str, str] | None = None
    outs_after_previous_play = 0
    runners_after_previous_play: dict[str, str] = {}
    for play_position, play in enumerate(plays):
        if CONTEXT_KEY in play:
            raise ValueError(
                f"Play {play_position} already contains reserved key {CONTEXT_KEY!r}"
            )
        about = play.get("about", {})
        matchup = play.get("matchup", {})
        result_event_type = play.get("result", {}).get("eventType")
        play_events = play.get("playEvents", [])
        runners = play.get("runners", [])
        has_plate_appearance_structure = bool(
            isinstance(about.get("atBatIndex"), int)
            and matchup.get("batter", {}).get("id") is not None
            and matchup.get("pitcher", {}).get("id") is not None
            and (play_events or runners)
            and result_event_type not in ADMINISTRATIVE_EVENT_TYPES
        )
        has_completed_plate_appearance_result = bool(
            has_plate_appearance_structure
            and about.get("isComplete") is True
            and isinstance(result_event_type, str)
            and result_event_type not in ADMINISTRATIVE_EVENT_TYPES
        )
        at_bat_index = require_numeric(
            about.get("atBatIndex"), f"Play {play_position} about.atBatIndex"
        )
        batter_id = require_numeric(
            matchup.get("batter", {}).get("id"),
            f"Play {at_bat_index} matchup.batter.id",
        )
        pitcher_id = require_numeric(
            matchup.get("pitcher", {}).get("id"),
            f"Play {at_bat_index} matchup.pitcher.id",
        )

        half_inning = (
            require_numeric(about.get("inning"), f"Play {at_bat_index} about.inning"),
            require_segment(
                str(about.get("halfInning", "")).lower(),
                f"Play {at_bat_index} about.halfInning",
            ),
        )
        if half_inning != current_half_inning:
            current_half_inning = half_inning
            outs_after_previous_play = 0
            runners_after_previous_play = {}
            for event in play.get("playEvents", []):
                if event.get("details", {}).get("eventType") != "runner_placed":
                    continue
                base_number = require_numeric(
                    event.get("base"),
                    f"Play {at_bat_index} runner_placed base",
                )
                if base_number not in {"1", "2", "3"}:
                    raise ValueError(
                        f"Play {at_bat_index} runner_placed has unsupported base {base_number}"
                    )
                runner_id = require_numeric(
                    event.get("player", {}).get("id"),
                    f"Play {at_bat_index} runner_placed player.id",
                )
                if base_number in runners_after_previous_play:
                    raise ValueError(
                        f"Play {at_bat_index} places multiple runners on base {base_number}"
                    )
                runners_after_previous_play[base_number] = runner_id

        start_base_occupancies = [
            {
                "atBatIndex": at_bat_index,
                "runnerId": runner_id,
                "baseNumber": base_number,
                "baseCode": f"{base_number}B",
                "baseLabel": {"1": "First base", "2": "Second base", "3": "Third base"}[base_number],
                "baseSiteLabel": {"1": "First base site", "2": "Second base site", "3": "Third base site"}[base_number],
            }
            for base_number, runner_id in sorted(runners_after_previous_play.items())
        ]

        play_context: dict[str, object] = {
            "outsBefore": outs_after_previous_play,
            "startBaseOccupancies": start_base_occupancies,
            "hasPlateAppearanceStructure": has_plate_appearance_structure,
            "hasCompletedPlateAppearanceResult": has_completed_plate_appearance_result,
            "hasReviewStatus": False,
            "hasReviewChallengerId": False,
        }
        occupied_base_count += len(start_base_occupancies)
        review_status: str | None = None
        review_type: str | None = None
        review_context: dict[str, object] = {}
        if about.get("hasReview") is True:
            description = play.get("result", {}).get("description")
            if not isinstance(description, str):
                raise ValueError(f"Reviewed play {at_bat_index} has no description")
            review_match = REVIEW_DESCRIPTION.search(description)
            if review_match is None:
                raise ValueError(
                    f"Reviewed play {at_bat_index} has an unrecognized review description"
                )
            review_status = require_segment(
                review_match.group("status").lower(),
                f"Play {at_bat_index} review status",
            )
            review_type = require_segment(
                re.sub(r"[^a-z0-9]+", "_", review_match.group("review_type").lower()).strip("_"),
                f"Play {at_bat_index} review type",
            )
            review_initiation = (
                "challenge"
                if review_match.group("action").lower() == "challenged"
                else "umpire_review"
            )
            review_context.update(
                {
                    "hasReviewStatus": True,
                    "hasReviewChallengerId": False,
                    "reviewStatus": review_status,
                    "reviewType": review_type,
                    "reviewInitiation": review_initiation,
                    "reviewOutcome": (
                        "overturning" if review_status == "overturned" else "affirming"
                    ),
                }
            )
            if review_initiation == "challenge":
                challenger_name = review_match.group("initiator").strip()
                challenger_id = player_ids_by_name.get(challenger_name.casefold())
                if challenger_id is not None:
                    review_context["hasReviewChallengerId"] = True
                    review_context["reviewChallengerId"] = require_numeric(
                        challenger_id,
                        f"Play {at_bat_index} review challenger id",
                    )
            review_count += 1

        events_by_index = {
            event.get("index", event_position): event
            for event_position, event in enumerate(play_events)
        }
        classification_event_ids_by_runner: dict[int, str] = {}
        classification_event_ids: set[str] = set()
        for runner_position, runner in enumerate(runners):
            event_type = runner.get("details", {}).get("eventType")
            if event_type not in {"passed_ball", "wild_pitch"}:
                continue
            play_index = runner.get("details", {}).get("playIndex")
            event = events_by_index.get(play_index)
            if event is None:
                raise ValueError(
                    f"Play {at_bat_index} {event_type} runner row references missing "
                    f"play event index {play_index!r}"
                )
            source_pitch_event = event
            if event.get("isPitch") is not True or not event.get("playId"):
                preceding_pitch_events = [
                    candidate
                    for candidate in play_events
                    if candidate.get("isPitch") is True
                    and candidate.get("playId")
                    and candidate.get("index", -1) <= play_index
                ]
                if not preceding_pitch_events:
                    raise ValueError(
                        f"Play {at_bat_index} {event_type} event at index "
                        f"{play_index!r} has no preceding source pitch"
                    )
                source_pitch_event = preceding_pitch_events[-1]
            event_play_id = require_segment(
                source_pitch_event.get("playId"),
                f"Play {at_bat_index} {event_type} event playId",
            )
            classification_event_ids_by_runner[runner_position] = event_play_id
            classification_event_ids.add(event_play_id)

        has_null_strikeout_placeholder = any(
            runner.get("details", {}).get("eventType") == "strikeout"
            and runner.get("details", {}).get("runner", {}).get("id")
            == matchup.get("batter", {}).get("id")
            and runner.get("movement", {}).get("isOut") is None
            for runner in runners
        )
        safe_batter_classifications = {
            runner.get("details", {}).get("eventType")
            for runner in runners
            if runner.get("details", {}).get("runner", {}).get("id")
            == matchup.get("batter", {}).get("id")
            and runner.get("movement", {}).get("isOut") is False
            and runner.get("movement", {}).get("end") == "1B"
            and runner.get("details", {}).get("eventType")
            in {"passed_ball", "wild_pitch"}
        }
        uncaught_classification = next(iter(safe_batter_classifications), None)
        is_uncaught_third_strike = (
            play.get("result", {}).get("eventType") == "strikeout"
            and has_null_strikeout_placeholder
            and len(safe_batter_classifications) == 1
        )
        uncaught_event_id = next(
            (
                classification_event_ids_by_runner[runner_position]
                for runner_position, runner in enumerate(runners)
                if runner.get("details", {}).get("runner", {}).get("id")
                == matchup.get("batter", {}).get("id")
                and runner.get("movement", {}).get("isOut") is False
                and runner.get("movement", {}).get("end") == "1B"
                and runner.get("details", {}).get("eventType")
                == uncaught_classification
            ),
            None,
        )

        for runner_position, runner in enumerate(runners):
            if CONTEXT_KEY in runner:
                raise ValueError(
                    f"Runner {runner_position} in play {at_bat_index} already contains "
                    f"reserved key {CONTEXT_KEY!r}"
                )
            require_numeric(
                runner.get("details", {}).get("runner", {}).get("id"),
                f"Runner {runner_position} in play {at_bat_index} details.runner.id",
            )
            movement = runner.get("movement", {})
            event_type = runner.get("details", {}).get("eventType")
            runner_context: dict[str, object] = {
                "atBatIndex": at_bat_index,
                "runnerIndex": str(runner_position),
                "hasRunnerResolution": isinstance(movement.get("isOut"), bool),
                "hasSupportedStartBase": movement.get("start") in {"1B", "2B", "3B"},
                "endsAtScore": movement.get("end") == "score",
            }
            if runner_position in classification_event_ids_by_runner:
                runner_context["eventPlayId"] = classification_event_ids_by_runner[
                    runner_position
                ]
            if (
                is_uncaught_third_strike
                and event_type == "strikeout"
                and movement.get("isOut") is None
            ):
                runner_context["isUncaughtThirdStrikePlaceholder"] = True
                runner_context["eventPlayId"] = uncaught_event_id
            runner[CONTEXT_KEY] = runner_context
            runner_count += 1

        pitch_events = [
            event for event in play_events if event.get("isPitch") is True
        ]
        if pitch_events:
            terminal_pitch = pitch_events[-1]
            terminal_pitch_id = require_segment(
                terminal_pitch.get("playId"),
                f"Play {at_bat_index} terminal pitch playId",
            )
            play_context["terminalPitchPlayId"] = terminal_pitch_id
            play_context["terminalPitchIsInPlay"] = (
                terminal_pitch.get("details", {}).get("isInPlay") is True
                and terminal_pitch.get("details", {}).get("call", {}).get("code")
                in {"X", "D", "E"}
            )
            terminal_pitch_count += 1

        institutional_pitch_classification_count += len(classification_event_ids)

        if is_uncaught_third_strike:
            if not pitch_events:
                raise ValueError(
                    f"Uncaught third strike play {at_bat_index} has no pitch event"
                )
            if uncaught_event_id is None:
                raise ValueError(
                    f"Uncaught third strike play {at_bat_index} has no classified source pitch"
                )
            terminal_event_id = require_segment(
                pitch_events[-1].get("playId"),
                f"Uncaught third strike play {at_bat_index} terminal pitch playId",
            )
            if uncaught_event_id != terminal_event_id:
                raise ValueError(
                    f"Uncaught third strike play {at_bat_index} classification event "
                    f"{uncaught_event_id} does not match terminal pitch {terminal_event_id}"
                )
            play_context.update(
                {
                    "isUncaughtThirdStrike": True,
                    "uncaughtThirdStrikeEventType": uncaught_classification,
                    "uncaughtThirdStrikePlayId": uncaught_event_id,
                }
            )
            uncaught_third_strike_count += 1

        if review_type is not None and review_status is not None:
            final_decision = final_review_decision(review_type, play, pitch_events)
            if final_decision is not None:
                review_context["reviewFinalDecision"] = final_decision
            if review_status == "overturned":
                review_context["hasUnresolvedOriginalDecision"] = True
            elif final_decision is not None:
                review_context.update(
                    {
                        "reviewOriginalDecision": final_decision,
                        "reviewPattern": f"{final_decision}_to_{final_decision}",
                    }
                )
            play_context.update(review_context)

        play[CONTEXT_KEY] = play_context

        ending_outs = play.get("count", {}).get("outs")
        if not isinstance(ending_outs, int) or ending_outs < outs_after_previous_play or ending_outs > 3:
            raise ValueError(
                f"Play {at_bat_index} has invalid ending out count {ending_outs!r} "
                f"after {outs_after_previous_play} outs"
            )
        outs_after_previous_play = ending_outs
        runners_after_previous_play = {}
        for base_number, source_key in (("1", "postOnFirst"), ("2", "postOnSecond"), ("3", "postOnThird")):
            runner = matchup.get(source_key)
            if runner is None:
                continue
            runner_id = require_numeric(
                runner.get("id") if isinstance(runner, dict) else None,
                f"Play {at_bat_index} matchup.{source_key}.id",
            )
            if runner_id in runners_after_previous_play.values():
                raise ValueError(f"Play {at_bat_index} places runner {runner_id} on multiple bases")
            runners_after_previous_play[base_number] = runner_id

        for event_position, event in enumerate(pitch_events):
            if CONTEXT_KEY in event:
                raise ValueError(
                    f"Pitch {event_position} in play {at_bat_index} already contains "
                    f"reserved key {CONTEXT_KEY!r}"
                )
            play_id = require_segment(
                event.get("playId"),
                f"Pitch {event_position} in play {at_bat_index} playId",
            )
            if play_id in seen_pitch_ids:
                raise ValueError(f"Duplicate pitch playId in context source: {play_id}")
            seen_pitch_ids.add(play_id)
            trajectory = event.get("hitData", {}).get("trajectory")
            is_bunt_attempt = (
                event.get("details", {}).get("call", {}).get("code") in BUNT_CALL_CODES
                or trajectory in BUNT_TRAJECTORIES
            )
            event_context: dict[str, object] = {
                "atBatIndex": at_bat_index,
                "batterId": batter_id,
                "pitcherId": pitcher_id,
                "isBuntAttempt": is_bunt_attempt,
                "matchesBuntContactSource": (
                    is_bunt_attempt
                    and event.get("details", {}).get("call", {}).get("code") != "M"
                ),
                "hasPitchTypeCategory": False,
                "hasBattedTrajectoryCategory": False,
            }
            pitch_type_code = str(
                event.get("details", {}).get("type", {}).get("code") or ""
            )
            pitch_type_category = PITCH_TYPE_CATEGORY_BY_CODE.get(pitch_type_code)
            if pitch_type_category is not None:
                event_context.update(
                    {
                        "hasPitchTypeCategory": True,
                        "pitchTypeCategoryIri": (
                            f"https://baseballontology.org/{pitch_type_category}"
                        ),
                        "pitchTypeReferenceSystemIri": root_context[
                            "pitchTypeReferenceSystemIri"
                        ],
                    }
                )
            trajectory_category = BATTED_TRAJECTORY_CATEGORY_BY_TOKEN.get(
                str(trajectory or "")
            )
            if trajectory_category is not None:
                event_context.update(
                    {
                        "hasBattedTrajectoryCategory": True,
                        "battedTrajectoryCategoryIri": (
                            f"https://baseballontology.org/{trajectory_category}"
                        ),
                        "battedTrajectoryReferenceSystemIri": root_context[
                            "battedTrajectoryReferenceSystemIri"
                        ],
                    }
                )
            event[CONTEXT_KEY] = event_context
            if (
                event_position == len(pitch_events) - 1
                and review_type == "pitch_result"
            ):
                event[CONTEXT_KEY].update(review_context)
            pitch_count += 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(document, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"Context pitches: {pitch_count}")
    print(f"Context roster players: {roster_player_count}")
    print(f"Context runners: {runner_count}")
    print(f"Context occupied bases at plate-appearance start: {occupied_base_count}")
    print(f"Context terminal pitches: {terminal_pitch_count}")
    print(f"Context reviewed plays: {review_count}")
    print(
        "Context passed-ball/wild-pitch classifications: "
        f"{institutional_pitch_classification_count}"
    )
    print(f"Context uncaught third strikes: {uncaught_third_strike_count}")
    print(f"Context game end: {final_end_time}")


if __name__ == "__main__":
    main()
