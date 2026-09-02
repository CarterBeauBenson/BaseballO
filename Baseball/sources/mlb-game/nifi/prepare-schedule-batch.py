#!/usr/bin/env python3
"""Validate a transient MLB schedule response and emit completed-game requests.

The raw API response remains transient. Compact schedule-revision evidence is
persisted only when a completed game also has an official postponed occurrence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


BATCH_ID = re.compile(r"^[0-9a-f]{32}$")
POSITIVE_ID = re.compile(r"^[1-9][0-9]*$")
REQUEST_KINDS = {"backfill", "daily"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-root", type=Path, required=True)
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--request-kind", choices=sorted(REQUEST_KINDS), required=True)
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    return parser.parse_args()


def iso_date(value: str, label: str) -> str:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{label} must use YYYY-MM-DD") from error
    if parsed.isoformat() != value:
        raise ValueError(f"{label} must use canonical YYYY-MM-DD")
    return value


def positive_id(value: object, label: str) -> str:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a positive integer")
    rendered = str(value) if isinstance(value, (int, str)) else ""
    if not POSITIVE_ID.fullmatch(rendered):
        raise ValueError(f"{label} must be a positive integer")
    return str(int(rendered))


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".partial",
            delete=False,
        ) as stream:
            temporary_name = stream.name
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
        temporary_name = None
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)


def timestamp_date(value: object, label: str) -> str | None:
    if value is None or value == "":
        return None
    rendered = str(value)
    candidate = rendered[:10]
    return iso_date(candidate, label)


def plan_key(game_pk: str, planned_start: str) -> str:
    return hashlib.sha256(f"{game_pk}|{planned_start}".encode("utf-8")).hexdigest()[:20]


def is_later(original: str, revised: str) -> bool:
    if len(original) >= 19 and len(revised) >= 19:
        try:
            original_time = datetime.fromisoformat(original.replace("Z", "+00:00"))
            revised_time = datetime.fromisoformat(revised.replace("Z", "+00:00"))
            return revised_time > original_time
        except ValueError:
            pass
    return revised[:10] > original[:10]


def schedule_observations(document: dict[str, Any]) -> dict[str, list[dict[str, str | None]]]:
    dates = document.get("dates")
    if not isinstance(dates, list):
        raise ValueError("schedule response dates must be an array")
    games: dict[str, list[dict[str, str | None]]] = {}
    for date_index, date_record in enumerate(dates):
        if not isinstance(date_record, dict):
            raise ValueError(f"dates[{date_index}] must be an object")
        scheduled_date = iso_date(str(date_record.get("date", "")), f"dates[{date_index}].date")
        records = date_record.get("games")
        if not isinstance(records, list):
            raise ValueError(f"dates[{date_index}].games must be an array")
        for game_index, record in enumerate(records):
            label = f"dates[{date_index}].games[{game_index}]"
            if not isinstance(record, dict):
                raise ValueError(f"{label} must be an object")
            game_pk = positive_id(record.get("gamePk"), f"{label}.gamePk")
            status = record.get("status")
            if not isinstance(status, dict):
                raise ValueError(f"{label}.status must be an object")
            state = status.get("abstractGameState")
            if not isinstance(state, str) or not state:
                raise ValueError(f"{label}.status.abstractGameState must be text")
            detailed_state = status.get("detailedState")
            if detailed_state is not None and not isinstance(detailed_state, str):
                raise ValueError(f"{label}.status.detailedState must be text when present")
            reason = status.get("reason")
            if reason is not None and not isinstance(reason, str):
                raise ValueError(f"{label}.status.reason must be text when present")
            games.setdefault(game_pk, []).append(
                {
                    "scheduledDate": scheduled_date,
                    "gameDate": str(record["gameDate"]) if record.get("gameDate") else None,
                    "abstractState": state,
                    "detailedState": detailed_state,
                    "reason": reason,
                    "rescheduleDate": (
                        str(record["rescheduleDate"])
                        if record.get("rescheduleDate")
                        else None
                    ),
                    "rescheduledFrom": (
                        str(record["rescheduledFrom"])
                        if record.get("rescheduledFrom")
                        else None
                    ),
                }
            )
    return games


def completed_games(
    observations: dict[str, list[dict[str, str | None]]],
    schedule_sha256: str,
    batch_id: str,
    evidence_root: Path,
) -> list[dict[str, str]]:
    requests: list[dict[str, str]] = []
    for game_pk in sorted(observations, key=int):
        records = observations[game_pk]
        completed = [
            row
            for row in records
            if row["abstractState"] == "Final"
            and str(row["detailedState"] or "").casefold()
            not in {"postponed", "cancelled", "suspended"}
        ]
        if not completed:
            continue
        completed.sort(key=lambda row: (str(row["scheduledDate"]), str(row["gameDate"] or "")))
        final = completed[-1]
        row: dict[str, str] = {
            "gamePk": game_pk,
            "scheduleDate": str(final["scheduledDate"]),
            "materializeMode": "deferred",
            "scheduleEvidencePath": "none",
        }
        postponed = [
            item
            for item in records
            if str(item["detailedState"] or "").casefold() == "postponed"
        ]
        postponements: list[dict[str, str]] = []
        for position, item in enumerate(postponed):
            original_start = str(item["gameDate"] or item["scheduledDate"])
            revised_start = str(item["rescheduleDate"] or final["gameDate"] or final["scheduledDate"])
            original_date = timestamp_date(original_start, f"game {game_pk} original planned date")
            revised_date = timestamp_date(revised_start, f"game {game_pk} revised planned date")
            if original_date is None or revised_date is None:
                raise ValueError(f"postponed game {game_pk} lacks a usable old or revised date")
            if not is_later(original_start, revised_start):
                raise ValueError(
                    f"postponed game {game_pk} does not identify a later revised plan"
                )
            original_key = plan_key(game_pk, original_start)
            revised_key = plan_key(game_pk, revised_start)
            evidence = {
                "position": str(position),
                "originalPlannedStart": original_start,
                "revisedPlannedStart": revised_start,
                "originalDate": original_date,
                "revisedDate": revised_date,
                "originalPlanKey": original_key,
                "revisedPlanKey": revised_key,
                "actKey": hashlib.sha256(
                    f"{game_pk}|{original_key}|{revised_key}".encode("utf-8")
                ).hexdigest()[:20],
            }
            if item["reason"]:
                evidence["reason"] = str(item["reason"])
            postponements.append(evidence)
        if postponements:
            evidence_path = evidence_root / batch_id / f"{game_pk}.json"
            schedule_evidence = {
                "artifactType": "baseballo-mlb-game-schedule-evidence",
                "contractVersion": 1,
                "batchId": batch_id,
                "gamePk": game_pk,
                "scheduleSha256": schedule_sha256,
                "finalScheduleDate": row["scheduleDate"],
                "postponements": postponements,
            }
            if evidence_path.is_file():
                prior = json.loads(evidence_path.read_text(encoding="utf-8-sig"))
                if prior != schedule_evidence:
                    raise ValueError(
                        f"schedule evidence for game {game_pk} changed within batch {batch_id}"
                    )
            else:
                atomic_json(evidence_path, schedule_evidence)
            row["scheduleEvidencePath"] = str(evidence_path.resolve())
        requests.append(row)
    return requests


def transform(raw: bytes, args: argparse.Namespace) -> dict[str, Any]:
    if not BATCH_ID.fullmatch(args.batch_id):
        raise ValueError("--batch-id must contain 32 lowercase hex digits")
    start_date = iso_date(args.start_date, "--start-date")
    end_date = iso_date(args.end_date, "--end-date")
    if end_date < start_date:
        raise ValueError("--end-date must not precede --start-date")

    if not raw:
        raise ValueError("schedule response is empty")
    schedule_sha256 = hashlib.sha256(raw).hexdigest()
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"schedule response is not strict UTF-8 JSON: {error}") from error
    if not isinstance(document, dict):
        raise ValueError("schedule response root must be an object")

    observations = schedule_observations(document)
    evidence_root = (
        args.state_root.resolve()
        / "pipeline"
        / "control"
        / "mlb-game"
        / "schedule-evidence"
    )
    games = completed_games(
        observations, schedule_sha256, args.batch_id, evidence_root
    )
    created = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    batch_root = args.state_root.resolve() / "pipeline" / "control" / "mlb-game" / "batches"
    manifest_path = batch_root / f"{args.batch_id}.json"
    expected = [row["gamePk"] for row in games]
    manifest = {
        "artifactType": "baseballo-mlb-game-schedule-batch",
        "contractVersion": 1,
        "batchId": args.batch_id,
        "status": "pending" if games else "complete-empty",
        "requestKind": args.request_kind,
        "requestedStartDate": start_date,
        "requestedEndDate": end_date,
        "createdAtUtc": created,
        "scheduleSha256": schedule_sha256,
        "expectedGameCount": len(expected),
        "expectedGamePks": expected,
    }
    if manifest_path.is_file():
        prior = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        immutable = (
            "artifactType",
            "contractVersion",
            "batchId",
            "requestKind",
            "requestedStartDate",
            "requestedEndDate",
            "scheduleSha256",
            "expectedGameCount",
            "expectedGamePks",
        )
        if any(prior.get(key) != manifest.get(key) for key in immutable):
            raise ValueError(f"batch {args.batch_id} was retried with different evidence")
        manifest = prior
    else:
        atomic_json(manifest_path, manifest)

    for row in games:
        row["batchId"] = args.batch_id
    return {
        "artifactType": "baseballo-mlb-game-schedule-requests",
        "contractVersion": 1,
        "batchId": args.batch_id,
        "games": games,
    }


def main() -> int:
    args = parse_args()
    raw = sys.stdin.buffer.read()
    try:
        output = transform(raw, args)
    except (OSError, ValueError) as error:
        # ExecuteStreamCommand routes stdout as the retry FlowFile content.
        # Preserve the original response bytes on a parser failure so a retry
        # or quarantine never receives the former zero-byte placeholder.
        sys.stdout.buffer.write(raw)
        print(f"MLB schedule batch rejected: {error}", file=sys.stderr)
        return 2
    json.dump(output, sys.stdout, ensure_ascii=False, separators=(",", ":"))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
