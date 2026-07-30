#!/usr/bin/env python3
"""Prepare a structurally enriched MLB game JSON file for Stage 1 YARRRML.

This script does not create RDF classes or relations. It only:
- copies stable source identifiers into nested records;
- exposes source array indexes;
- flattens repeating structures into reusable arrays;
- derives container time bounds from their source parts.

The raw MLB JSON remains authoritative and unchanged.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def first_non_null(values: list[str | None]) -> str | None:
    return min((v for v in values if v), default=None)


def last_non_null(values: list[str | None]) -> str | None:
    return max((v for v in values if v), default=None)


def prepare(raw: dict[str, Any], source_name: str) -> dict[str, Any]:
    game_pk = raw["gamePk"]
    game_data = raw.get("gameData", {})
    live_data = raw.get("liveData", {})
    plays = live_data.get("plays", {}).get("allPlays", [])
    venue = game_data.get("venue") or {}
    venue_id = venue.get("id")

    pitch_starts: list[str | None] = []
    pitch_ends: list[str | None] = []
    pitches: list[dict[str, Any]] = []
    plate_appearances: list[dict[str, Any]] = []

    inning_times: dict[int, dict[str, list[str | None]]] = defaultdict(
        lambda: {"starts": [], "ends": []}
    )
    half_times: dict[tuple[int, str], dict[str, list[str | None]]] = defaultdict(
        lambda: {"starts": [], "ends": []}
    )

    for play_position, play in enumerate(plays):
        about = play.get("about", {})
        matchup = play.get("matchup", {})
        result = play.get("result", {})
        at_bat_index = about.get("atBatIndex", play.get("atBatIndex", play_position))
        inning = about.get("inning")
        half_inning = about.get("halfInning")
        start_time = about.get("startTime")
        end_time = about.get("endTime", play.get("playEndTime"))

        batter = matchup.get("batter") or {}
        pitcher = matchup.get("pitcher") or {}

        contact_event_index = None
        terminal_pitch_event_index = None
        for event_position, event in enumerate(play.get("playEvents", [])):
            if event.get("isPitch"):
                event_index = event.get("index", event_position)
                terminal_pitch_event_index = event_index
                details = event.get("details", {})
                call_code = (details.get("call") or {}).get("code", details.get("code"))
                if details.get("isInPlay") or call_code in {"F", "T"}:
                    contact_event_index = event_index

        pa = {
            "gamePk": game_pk,
            "venueId": venue_id,
            "atBatIndex": at_bat_index,
            "sourcePlayPosition": play_position,
            "inning": inning,
            "halfInning": half_inning,
            "startTime": start_time,
            "endTime": end_time,
            "batterId": batter.get("id"),
            "pitcherId": pitcher.get("id"),
            "event": result.get("event"),
            "eventType": result.get("eventType"),
            "eventTypeSegment": (result.get("eventType") or "unclassified").replace("_", "-"),
            "contactEventIndex": contact_event_index,
            "terminalPitchEventIndex": terminal_pitch_event_index,
            "description": result.get("description"),
            "isOut": result.get("isOut"),
            "isComplete": about.get("isComplete"),
            "hasOut": about.get("hasOut"),
            "isScoringPlay": about.get("isScoringPlay"),
        }
        plate_appearances.append(pa)

        if inning is not None:
            inning_times[inning]["starts"].append(start_time)
            inning_times[inning]["ends"].append(end_time)
        if inning is not None and half_inning:
            half_times[(inning, half_inning)]["starts"].append(start_time)
            half_times[(inning, half_inning)]["ends"].append(end_time)

        for event_position, event in enumerate(play.get("playEvents", [])):
            if not event.get("isPitch"):
                continue
            details = event.get("details", {})
            call = details.get("call") or {}
            pitch_data = event.get("pitchData") or {}
            hit_data = event.get("hitData") or {}
            pitch_coordinates = pitch_data.get("coordinates") or {}
            hit_coordinates = hit_data.get("coordinates") or {}
            event_index = event.get("index", event_position)

            pitch = {
                "gamePk": game_pk,
                "venueId": venue_id,
                "atBatIndex": at_bat_index,
                "eventIndex": event_index,
                "sourceEventPosition": event_position,
                "playId": event.get("playId"),
                "pitchNumber": event.get("pitchNumber"),
                "startTime": event.get("startTime"),
                "endTime": event.get("endTime"),
                "batterId": batter.get("id"),
                "pitcherId": pitcher.get("id"),
                "callCode": call.get("code", details.get("code")),
                "callDescription": call.get("description", details.get("description")),
                "isStrike": details.get("isStrike"),
                "isBall": details.get("isBall"),
                "isInPlay": details.get("isInPlay"),
                "isOut": details.get("isOut"),
                "pitchTypeCode": (details.get("type") or {}).get("code"),
                "pitchTypeDescription": (details.get("type") or {}).get("description"),
                "platePX": pitch_coordinates.get("pX"),
                "platePZ": pitch_coordinates.get("pZ"),
                "hitLocationCode": hit_data.get("location"),
                "hitCoordX": hit_coordinates.get("coordX"),
                "hitCoordY": hit_coordinates.get("coordY"),
                "trajectory": hit_data.get("trajectory"),
            }
            pitches.append(pitch)
            pitch_starts.append(pitch["startTime"])
            pitch_ends.append(pitch["endTime"])

    innings = [
        {
            "gamePk": game_pk,
            "venueId": venue_id,
            "inning": inning,
            "startTime": first_non_null(times["starts"]),
            "endTime": last_non_null(times["ends"]),
        }
        for inning, times in sorted(inning_times.items())
    ]

    half_innings = [
        {
            "gamePk": game_pk,
            "venueId": venue_id,
            "inning": inning,
            "halfInning": half,
            "startTime": first_non_null(times["starts"]),
            "endTime": last_non_null(times["ends"]),
        }
        for (inning, half), times in sorted(half_times.items())
    ]

    teams = []
    for side in ("away", "home"):
        team = (game_data.get("teams") or {}).get(side) or {}
        if team.get("id") is not None:
            teams.append(
                {
                    "gamePk": game_pk,
                    "side": side,
                    "teamId": team.get("id"),
                    "teamName": team.get("name"),
                }
            )

    players = []
    for player in (game_data.get("players") or {}).values():
        if player.get("id") is not None:
            players.append(
                {
                    "playerId": player.get("id"),
                    "fullName": player.get("fullName"),
                    "isPlayer": player.get("isPlayer"),
                }
            )
    players.sort(key=lambda item: item["playerId"])

    final_out_times: list[str | None] = []
    for play in plays:
        is_final_out_play = any(
            (runner.get("movement") or {}).get("isOut")
            and (runner.get("movement") or {}).get("outNumber") == 3
            for runner in play.get("runners", [])
        )
        if is_final_out_play:
            final_out_times.append((play.get("about") or {}).get("endTime", play.get("playEndTime")))

    final_out_time = last_non_null(final_out_times)
    game_end_fallback_used = final_out_time is None
    if final_out_time is None:
        final_out_time = last_non_null([p.get("endTime") for p in plate_appearances])

    game = {
        "gamePk": game_pk,
        "sourceName": source_name,
        "officialDate": (game_data.get("datetime") or {}).get("officialDate"),
        "firstPitchTime": first_non_null(pitch_starts),
        "finalOutTime": final_out_time,
        "gameEndFallbackUsed": game_end_fallback_used,
        "venueId": venue.get("id"),
        "venueName": venue.get("name"),
    }

    return {
        "game": game,
        "teams": teams,
        "players": players,
        "innings": innings,
        "halfInnings": half_innings,
        "plateAppearances": plate_appearances,
        "pitches": pitches,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="Raw MLB feed/live JSON")
    parser.add_argument("output", type=Path, help="Structurally enriched JSON")
    args = parser.parse_args()

    with args.input.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)

    prepared = prepare(raw, args.input.name)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump(prepared, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


if __name__ == "__main__":
    main()
