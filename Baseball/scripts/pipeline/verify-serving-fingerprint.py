#!/usr/bin/env python3
"""Verify the promoted SQL corpus fingerprint against retained compact evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def digest(lines: list[str]) -> str:
    return hashlib.sha256("\n".join(sorted(lines)).encode("utf-8")).hexdigest()


def artifact(state: Path, game_pk: str, graph: str) -> str:
    try:
        manifest = load(state / "pipeline" / "manifests" / f"game-{game_pk}-rml.json")
        value = str(manifest.get("outputSha256", ""))
        if manifest.get("graphIri") == graph and len(value) == 64:
            return value
    except (OSError, ValueError, TypeError):
        pass
    return "manifest-unavailable"


def explorer_metadata(state: Path) -> dict[str, tuple[str, str]]:
    metadata: dict[str, tuple[str, str]] = {}
    for schedule_path in (ROOT / "data" / "raw" / "samples").glob("*/schedule.json"):
        schedule = load(schedule_path)
        for block in schedule.get("dates", []):
            for game in block.get("games", []):
                game_pk = str(game.get("gamePk", ""))
                official_date = str(game.get("officialDate", ""))
                if game_pk.isdigit() and len(official_date) == 10:
                    game_type = str(game.get("gameType", ""))
                    metadata[game_pk] = (official_date, "regular_season" if game_type == "R" else "all_star" if game_type == "A" else "other")
    metadata["566279"] = ("2019-04-01", "fixture")
    for path in (state / "pipeline" / "manifests" / "acquisition" / "games").glob("*/*/*.json"):
        try:
            manifest = load(path)
            game_pk = str(manifest.get("gamePk", ""))
            official_date = str(manifest.get("scheduleDate", ""))
            if game_pk.isdigit() and len(official_date) == 10:
                existing_set = metadata.get(game_pk, ("", "regular_season"))[1]
                game_type = manifest.get("gameType")
                game_set = "all_star" if game_type == "A" else "regular_season" if game_type == "R" else existing_set
                metadata[game_pk] = (official_date, game_set)
        except (OSError, ValueError, TypeError):
            continue
    metadata["566279"] = ("2019-04-01", "fixture")
    return metadata


def verify(state: Path, include_lines: bool = False) -> dict[str, Any]:
    pointer = load(state / "serving" / "current.json")
    database = Path(pointer["databasePath"])
    connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)
    try:
        games = connection.execute(
            "SELECT graph_iri,game_pk,official_date,game_set FROM game_dimension ORDER BY graph_iri"
        ).fetchall()
    finally:
        connection.close()
    stored_lines = [f"{graph}|{date}|{game_set}|{artifact(state, game_pk, graph)}" for graph, game_pk, date, game_set in games]
    metadata = explorer_metadata(state)
    mismatches = []
    explorer_lines = []
    for graph, game_pk, stored_date, stored_set in games:
        expected_date, expected_set = metadata.get(game_pk, (stored_date, stored_set))
        if (stored_date, stored_set) != (expected_date, expected_set):
            mismatches.append({"gamePk": game_pk, "stored": [stored_date, stored_set], "explorer": [expected_date, expected_set]})
        explorer_lines.append(f"{graph}|{expected_date}|{expected_set}|{artifact(state, game_pk, graph)}")
    result = {
        "status": "succeeded" if not mismatches else "failed",
        "gameCount": len(games),
        "pointerFingerprint": pointer["corpusFingerprint"],
        "recomputedStoredFingerprint": digest(stored_lines),
        "recomputedExplorerFingerprint": digest(explorer_lines),
        "metadataMismatches": mismatches,
    }
    if include_lines:
        result["canonicalLines"] = sorted(explorer_lines)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    default = Path(os.environ.get("BASEBALLO_STATE_ROOT") or Path(os.environ.get("LOCALAPPDATA", ".")) / "BaseballO" / "state")
    parser.add_argument("--state-root", type=Path, default=default)
    parser.add_argument("--lines", action="store_true")
    args = parser.parse_args()
    try:
        result = verify(args.state_root.resolve(), args.lines)
        print(json.dumps(result, separators=(",", ":")))
        return 0 if result["status"] == "succeeded" and result["pointerFingerprint"] == result["recomputedExplorerFingerprint"] else 1
    except Exception as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, separators=(",", ":")))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
