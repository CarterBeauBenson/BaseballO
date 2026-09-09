#!/usr/bin/env python3
"""Create an isolated ancestor-aware JSON context for RMLMapper execution."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date
from pathlib import Path


SAFE_IRI_SEGMENT = re.compile(r"^[A-Za-z0-9._~-]+$")
CONTEXT_KEY = "_baseballO"
REVIEW_DESCRIPTION = re.compile(
    r"^(?P<initiator>.+?) (?P<action>challenged|reviewed) \((?P<review_type>[^)]+)\)"
    r"(?:, call on the field was (?P<status>confirmed|overturned|upheld))?:",
    re.IGNORECASE,
)
REVIEW_STATUS_BY_NARRATIVE = {
    "confirmed": "confirmed",
    "upheld": "confirmed",
    "overturned": "overturned",
}
PITCH_DECISION_BY_CALL_CODE = {
    "B": "ball",
    "*B": "ball",
    "C": "strike",
}
BUNT_CALL_CODES = {"L", "M", "O"}
BUNT_TRAJECTORIES = {"bunt_grounder", "bunt_popup", "bunt_line_drive"}
ADMINISTRATIVE_EVENT_TYPES = {"game_advisory"}
# A1 is contact-play membership only. This initial subset deliberately omits
# mixed runner classifications; absence is not evidence of independence.
BATTED_RUNNER_RESULT_TYPES = {
    "single", "double", "triple", "home_run", "field_out", "force_out",
    "grounded_into_double_play", "double_play", "sac_fly", "sac_bunt",
    "fielders_choice", "field_error",
}
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


def batted_runner_resolution_links(play: dict, at_bat_index: str) -> list[dict[str, str]]:
    """Expose evidenced existing resolution identities for A1 RML parthood.

    A PA or event-index join alone is insufficient. Require a completed,
    recognized contact result and a uniquely indexed terminal in-play pitch,
    and admit only runner rows carrying that same result classification.
    This does not calculate attribution, destination, or trajectory state.
    """
    result_type = play.get("result", {}).get("eventType")
    if (
        play.get("about", {}).get("isComplete") is not True
        or result_type not in BATTED_RUNNER_RESULT_TYPES
    ):
        return []
    events = play.get("playEvents", [])
    pitches = [event for event in events if event.get("isPitch") is True]
    if not pitches:
        return []
    terminal = pitches[-1]
    details = terminal.get("details", {})
    event_index = terminal.get("index")
    play_id = terminal.get("playId")
    if (
        details.get("isInPlay") is not True
        or details.get("call", {}).get("code") not in {"X", "D", "E"}
        or type(event_index) is not int
        or event_index < 0
        or not isinstance(play_id, str)
        or not SAFE_IRI_SEGMENT.fullmatch(play_id)
        or sum(event.get("index") == event_index for event in events) != 1
    ):
        return []
    links = []
    for position, runner in enumerate(play.get("runners", [])):
        runner_details = runner.get("details", {})
        movement = runner.get("movement", {})
        runner_event_index = runner_details.get("playIndex")
        if (
            type(runner_event_index) is not int
            or runner_event_index != event_index
            or runner_details.get("eventType") != result_type
            or type(movement.get("isOut")) is not bool
        ):
            continue
        # These branches reuse the current Runner*Source identity selection.
        if movement["isOut"]:
            kind = "out"
        elif movement.get("end") == "score":
            kind = "score"
        elif movement.get("start") in {"1B", "2B", "3B"}:
            kind = "advance"
        else:
            kind = "reach"
        links.append({
            "atBatIndex": at_bat_index,
            "runnerIndex": str(position),
            "resolutionKind": kind,
            "playId": play_id,
        })
    return links


def runner_episode_evidence(play: dict, at_bat_index: str) -> dict[str, list[dict]]:
    """Select the existing act/resolution pair and supported safe decision content.

    No directive or immediately preceding stasis is inferred from movement rows.
    The RML/SHACL layer expresses and validates the reviewed structural pattern.
    """
    products = {"runnerEpisodes": [], "safeDecisionDestinations": []}
    complete = play.get("about", {}).get("isComplete") is True
    for position, row in enumerate(play.get("runners", [])):
        movement = row.get("movement", {})
        runner_id = row.get("details", {}).get("runner", {}).get("id")
        if type(movement.get("isOut")) is not bool or not str(runner_id).isdigit():
            continue
        kind = ("out" if movement["isOut"] else
                "score" if movement.get("end") == "score" else
                "advance" if movement.get("start") in {"1B", "2B", "3B"} else "reach")
        item = {"atBatIndex": at_bat_index, "runnerIndex": str(position),
                "resolutionKind": kind, "runnerId": str(runner_id)}
        products["runnerEpisodes"].append(item)
        if complete and not movement["isOut"] and movement.get("end") in {"1B", "2B", "3B"}:
            products["safeDecisionDestinations"].append({**item, "baseCode": movement["end"]})
    return products


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
    parser.add_argument("--schedule-evidence", type=Path)
    return parser.parse_args()


def schedule_postponement_context(
    path: Path | None, game_pk: str
) -> list[dict[str, object]]:
    if path is None:
        return []
    evidence = json.loads(path.read_text(encoding="utf-8-sig"))
    if evidence.get("artifactType") != "baseballo-mlb-game-schedule-evidence":
        raise ValueError("Schedule evidence has an unexpected artifactType")
    if evidence.get("contractVersion") != 1:
        raise ValueError("Schedule evidence has an unsupported contractVersion")
    if str(evidence.get("gamePk")) != game_pk:
        raise ValueError("Schedule evidence gamePk does not match the game payload")
    schedule_sha256 = str(evidence.get("scheduleSha256") or "")
    if not re.fullmatch(r"[0-9a-f]{64}", schedule_sha256):
        raise ValueError("Schedule evidence lacks a valid scheduleSha256")
    records = evidence.get("postponements")
    if not isinstance(records, list) or not records:
        raise ValueError("Schedule evidence has no postponement records")

    context: list[dict[str, object]] = []
    for position, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"Schedule postponement {position} must be an object")
        act_key = require_segment(record.get("actKey"), f"postponement {position} actKey")
        original_key = require_segment(
            record.get("originalPlanKey"), f"postponement {position} originalPlanKey"
        )
        revised_key = require_segment(
            record.get("revisedPlanKey"), f"postponement {position} revisedPlanKey"
        )
        original_date = str(record.get("originalDate") or "")
        revised_date = str(record.get("revisedDate") or "")
        try:
            if date.fromisoformat(original_date) >= date.fromisoformat(revised_date):
                raise ValueError
        except ValueError as error:
            raise ValueError(
                f"Schedule postponement {position} must identify ordered calendar dates"
            ) from error
        game_iri = f"https://baseballontology.org/data/game/{game_pk}"
        act_iri = f"{game_iri}/schedule/postponement/{act_key}"
        original_plan_iri = f"{game_iri}/schedule-plan/{original_key}"
        revised_plan_iri = f"{game_iri}/schedule-plan/{revised_key}"
        reason = str(record.get("reason") or "")
        item: dict[str, object] = {
            "gameIri": game_iri,
            "actIri": act_iri,
            "originalPlanIri": original_plan_iri,
            "revisedPlanIri": revised_plan_iri,
            "originalDateIdentifierIri": f"{original_plan_iri}/calendar-date",
            "revisedDateIdentifierIri": f"{revised_plan_iri}/calendar-date",
            "originalDayIri": f"https://baseballontology.org/data/day/{original_date}",
            "revisedDayIri": f"https://baseballontology.org/data/day/{revised_date}",
            "originalDate": original_date,
            "revisedDate": revised_date,
            "mlbOrganizationIri": (
                "https://baseballontology.org/data/organization/major-league-baseball"
            ),
            "scheduleResponseIri": (
                "https://baseballontology.org/data/source/mlb-game/schedule/response/"
                f"sha256/{schedule_sha256}"
            ),
            "hasReason": bool(reason),
        }
        if reason:
            reason_key = hashlib.sha256(reason.encode("utf-8")).hexdigest()[:20]
            item.update(
                {
                    "reason": reason,
                    "reasonMeasurementIri": f"{act_iri}/reason/{reason_key}",
                    "reasonReferenceSystemIri": (
                        "https://baseballontology.org/data/reference-system/"
                        "mlb-game/schedule-postponement-reasons"
                    ),
                }
            )
        context.append(item)
    return context


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


def reviewed_play_context(
    play: dict[str, object],
    pitch_events: list[dict[str, object]],
    player_ids_by_name: dict[str, str],
    at_bat_index: str,
) -> dict[str, object]:
    """Return only the review claims supported by one reviewed MLB play.

    MLB's pitch-result challenge wording can omit confirmed/overturned status.
    That absence does not suppress the evidenced challenge, review, or final
    decision, and it never licenses an invented original decision or outcome.
    """
    description = play.get("result", {}).get("description")
    if not isinstance(description, str):
        raise ValueError(f"Reviewed play {at_bat_index} has no description")
    review_match = REVIEW_DESCRIPTION.search(description)
    if review_match is None:
        raise ValueError(
            f"Reviewed play {at_bat_index} has an unrecognized review description"
        )

    review_type = require_segment(
        re.sub(
            r"[^a-z0-9]+",
            "_",
            review_match.group("review_type").lower(),
        ).strip("_"),
        f"Play {at_bat_index} review type",
    )
    review_initiation = (
        "challenge"
        if review_match.group("action").lower() == "challenged"
        else "umpire_review"
    )
    context: dict[str, object] = {
        "hasReview": True,
        "hasReviewStatus": False,
        "hasReviewChallengerId": False,
        "reviewType": review_type,
        "reviewInitiation": review_initiation,
    }

    status_text = review_match.group("status")
    review_status = (
        REVIEW_STATUS_BY_NARRATIVE[status_text.lower()]
        if status_text is not None
        else None
    )
    # A plate appearance can contain more than one review. The play-level
    # reviewDetails describes the review summarized by the play-level result
    # narrative; a reviewed pitch earlier in the same plate appearance can be
    # a separate review with a different outcome. Prefer the matching
    # play-level evidence and consult pitch-level evidence only when it is
    # absent, so distinct review acts are never conflated.
    play_review_details = play.get("reviewDetails")
    if (
        isinstance(play_review_details, dict)
        and isinstance(play_review_details.get("isOverturned"), bool)
    ):
        structured_overturns = {play_review_details["isOverturned"]}
    else:
        structured_overturns = {
            event.get("reviewDetails", {}).get("isOverturned")
            for event in pitch_events
            if isinstance(event.get("reviewDetails"), dict)
            and isinstance(event.get("reviewDetails", {}).get("isOverturned"), bool)
        }
    if len(structured_overturns) > 1:
        raise ValueError(
            f"Reviewed play {at_bat_index} has conflicting structured review outcomes"
        )
    if structured_overturns:
        structured_status = "overturned" if next(iter(structured_overturns)) else "confirmed"
        if review_status is not None and review_status != structured_status:
            raise ValueError(
                f"Reviewed play {at_bat_index} has conflicting narrative and structured review outcomes"
            )
        review_status = structured_status

    if review_status is not None:
        context.update(
            {
                "hasReviewStatus": True,
                "reviewStatus": review_status,
                "reviewOutcome": (
                    "overturning" if review_status == "overturned" else "affirming"
                ),
            }
        )

    if review_initiation == "challenge":
        challenger_name = review_match.group("initiator").strip()
        challenger_id = player_ids_by_name.get(challenger_name.casefold())
        if challenger_id is not None:
            context["hasReviewChallengerId"] = True
            context["reviewChallengerId"] = require_numeric(
                challenger_id,
                f"Play {at_bat_index} review challenger id",
            )

    final_decision = final_review_decision(review_type, play, pitch_events)
    if final_decision is not None:
        context["reviewFinalDecision"] = final_decision
    if review_status == "overturned":
        context["hasUnresolvedOriginalDecision"] = True
    elif review_status is not None and final_decision is not None:
        context.update(
            {
                "reviewOriginalDecision": final_decision,
                "reviewPattern": f"{final_decision}_to_{final_decision}",
            }
        )
    return context


def play_has_plate_appearance_structure(play: dict[str, object]) -> bool:
    """Whether a provider play contains evidence of a plate appearance.

    A pure administrative advisory is not a plate appearance. An advisory can,
    however, be appended to an incomplete plate appearance that already
    contains a real pitch or runner event; those baseball processes retain
    their plate-appearance context even though no completed result is mapped.
    """
    about = play.get("about", {})
    matchup = play.get("matchup", {})
    play_events = play.get("playEvents", [])
    runners = play.get("runners", [])
    result_event_type = play.get("result", {}).get("eventType")
    has_baseball_event = bool(
        runners or any(event.get("isPitch") is True for event in play_events)
    )
    return bool(
        isinstance(about.get("atBatIndex"), int)
        and matchup.get("batter", {}).get("id") is not None
        and matchup.get("pitcher", {}).get("id") is not None
        and (play_events or runners)
        and (
            result_event_type not in ADMINISTRATIVE_EVENT_TYPES
            or has_baseball_event
        )
    )


def annotate_officials(document: dict[str, object]) -> int:
    """Add mapping guards without fabricating absent official names."""
    officials = (
        document.get("liveData", {}).get("boxscore", {}).get("officials", [])
    )
    for position, assignment in enumerate(officials):
        if CONTEXT_KEY in assignment:
            raise ValueError(
                f"Official {position} already contains reserved key {CONTEXT_KEY!r}"
            )
        official = assignment.get("official", {})
        require_numeric(official.get("id"), f"Official {position} official.id")
        full_name = official.get("fullName")
        assignment[CONTEXT_KEY] = {
            "hasOfficialName": isinstance(full_name, str) and bool(full_name.strip())
        }
    return len(officials)


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
    postponement_context = schedule_postponement_context(
        args.schedule_evidence, game_pk
    )
    if postponement_context:
        root_context["schedulePostponements"] = postponement_context
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
    official_count = annotate_officials(document)

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
        pitch_events = [
            event for event in play_events if event.get("isPitch") is True
        ]
        runners = play.get("runners", [])
        has_plate_appearance_structure = play_has_plate_appearance_structure(play)
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
            "battedRunnerResolutions": batted_runner_resolution_links(play, at_bat_index),
            **runner_episode_evidence(play, at_bat_index),
            "hasPlateAppearanceStructure": has_plate_appearance_structure,
            "hasCompletedPlateAppearanceResult": has_completed_plate_appearance_result,
            "hasReview": False,
            "hasReviewStatus": False,
            "hasReviewChallengerId": False,
        }
        occupied_base_count += len(start_base_occupancies)
        review_type: str | None = None
        review_context: dict[str, object] = {}
        if about.get("hasReview") is True:
            review_context = reviewed_play_context(
                play, pitch_events, player_ids_by_name, at_bat_index
            )
            review_type = str(review_context["reviewType"])
            play_context.update(review_context)
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
    print(f"Context officials: {official_count}")
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
    print(f"Context schedule postponements: {len(postponement_context)}")


if __name__ == "__main__":
    main()
