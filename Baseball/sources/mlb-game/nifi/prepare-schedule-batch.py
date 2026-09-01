#!/usr/bin/env python3
"""Validate a transient MLB schedule response and emit final-game requests.

The raw schedule stays in the NiFi FlowFile. Only its hash, request scope, and
the expected final game identifiers are persisted as compact batch evidence.
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


def final_games(document: dict[str, Any]) -> list[dict[str, str]]:
    dates = document.get("dates")
    if not isinstance(dates, list):
        raise ValueError("schedule response dates must be an array")
    games: dict[str, dict[str, str]] = {}
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
            if state != "Final":
                continue
            row = {
                "gamePk": game_pk,
                "scheduleDate": scheduled_date,
                "materializeMode": "deferred",
            }
            existing = games.get(game_pk)
            if existing is not None and existing != row:
                raise ValueError(f"schedule repeats game {game_pk} with conflicting dates")
            games[game_pk] = row
    return [games[key] for key in sorted(games, key=int)]


def main() -> int:
    args = parse_args()
    if not BATCH_ID.fullmatch(args.batch_id):
        raise ValueError("--batch-id must contain 32 lowercase hex digits")
    start_date = iso_date(args.start_date, "--start-date")
    end_date = iso_date(args.end_date, "--end-date")
    if end_date < start_date:
        raise ValueError("--end-date must not precede --start-date")

    raw = sys.stdin.buffer.read()
    if not raw:
        raise ValueError("schedule response is empty")
    schedule_sha256 = hashlib.sha256(raw).hexdigest()
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"schedule response is not strict UTF-8 JSON: {error}") from error
    if not isinstance(document, dict):
        raise ValueError("schedule response root must be an object")

    games = final_games(document)
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
    json.dump(
        {
            "artifactType": "baseballo-mlb-game-schedule-requests",
            "contractVersion": 1,
            "batchId": args.batch_id,
            "games": games,
        },
        sys.stdout,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print(f"MLB schedule batch rejected: {error}", file=sys.stderr)
        raise SystemExit(2)
