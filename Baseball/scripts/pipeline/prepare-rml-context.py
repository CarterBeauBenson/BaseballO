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
OPPOSITE_REVIEW_DECISION = {
    "ball": "strike",
    "strike": "ball",
    "out": "safe",
    "safe": "out",
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

    final_end_time = plays[-1].get("about", {}).get("endTime")
    if not isinstance(final_end_time, str) or not final_end_time.strip():
        raise ValueError("Final play has no about.endTime")
    document[CONTEXT_KEY] = {"gameEndTime": final_end_time}
    player_ids_by_name = unique_player_ids_by_name(document)

    pitch_count = 0
    runner_count = 0
    terminal_pitch_count = 0
    review_count = 0
    pitch_ball_control_failure_count = 0
    uncaught_third_strike_count = 0
    seen_pitch_ids: set[str] = set()
    for play_position, play in enumerate(plays):
        if CONTEXT_KEY in play:
            raise ValueError(
                f"Play {play_position} already contains reserved key {CONTEXT_KEY!r}"
            )
        about = play.get("about", {})
        matchup = play.get("matchup", {})
        plate_appearance_is_sac_bunt = (
            play.get("result", {}).get("eventType") == "sac_bunt"
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

        play_context: dict[str, object] = {}
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
                    review_context["reviewChallengerId"] = require_numeric(
                        challenger_id,
                        f"Play {at_bat_index} review challenger id",
                    )
            review_count += 1

        play_events = play.get("playEvents", [])
        events_by_index = {
            event.get("index", event_position): event
            for event_position, event in enumerate(play_events)
        }
        runners = play.get("runners", [])
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

        if classification_event_ids:
            play_context["hasPitchBallControlFailure"] = True
            play_context["pitchBallControlFailureEventIds"] = sorted(
                classification_event_ids
            )
            pitch_ball_control_failure_count += len(classification_event_ids)

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
                original_decision = (
                    OPPOSITE_REVIEW_DECISION[final_decision]
                    if review_status == "overturned"
                    else final_decision
                )
                review_context.update(
                    {
                        "reviewFinalDecision": final_decision,
                        "reviewOriginalDecision": original_decision,
                        "reviewPattern": f"{original_decision}_to_{final_decision}",
                    }
                )
            play_context.update(review_context)

        play[CONTEXT_KEY] = play_context

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
            event[CONTEXT_KEY] = {
                "atBatIndex": at_bat_index,
                "batterId": batter_id,
                "pitcherId": pitcher_id,
                "plateAppearanceIsSacBunt": plate_appearance_is_sac_bunt,
            }
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
    print(f"Context runners: {runner_count}")
    print(f"Context terminal pitches: {terminal_pitch_count}")
    print(f"Context reviewed plays: {review_count}")
    print(f"Context pitch-ball control failures: {pitch_ball_control_failure_count}")
    print(f"Context uncaught third strikes: {uncaught_third_strike_count}")
    print(f"Context game end: {final_end_time}")


if __name__ == "__main__":
    main()
