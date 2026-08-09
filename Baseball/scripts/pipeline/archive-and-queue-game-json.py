#!/usr/bin/env python3
"""Archive byte-identical game JSON and queue a NiFi semantic work request."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", delete=False, dir=path.parent
    ) as output:
        json.dump(value, output, indent=2, ensure_ascii=False)
        output.write("\n")
        temporary = Path(output.name)
    os.replace(temporary, path)


def safe_numeric(value: Any, label: str) -> str:
    text = str(value or "")
    if not text.isdigit():
        raise ValueError(f"The supplied JSON has no safe numeric {label}: {text!r}")
    return text


def archive_source(source: Path, destination: Path, expected_hash: str) -> bool:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file():
        if sha256_file(destination) != expected_hash:
            raise ValueError(f"Content-addressed archive collision at {destination}")
        return False
    with tempfile.NamedTemporaryFile(delete=False, dir=destination.parent) as output:
        temporary = Path(output.name)
        with source.open("rb") as input_stream:
            shutil.copyfileobj(input_stream, output)
    try:
        if sha256_file(temporary) != expected_hash:
            raise ValueError("The archived copy is not byte-identical to the supplied JSON")
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--state-root", type=Path, required=True)
    parser.add_argument("--source-filename")
    parser.add_argument("--force-rdf-load", action="store_true")
    args = parser.parse_args()

    input_path = args.input.resolve(strict=True)
    state_root = args.state_root.resolve()
    pipeline_root = state_root / "pipeline"
    input_hash = sha256_file(input_path)
    input_bytes = input_path.stat().st_size
    started_at = datetime.now(timezone.utc)
    run_id = started_at.strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid.uuid4().hex
    source_filename = Path(args.source_filename).name if args.source_filename else input_path.name
    document = json.loads(input_path.read_text(encoding="utf-8-sig"))
    game_pk = safe_numeric(document.get("gamePk"), "gamePk")
    season = safe_numeric(document.get("gameData", {}).get("game", {}).get("season"), "season")
    if len(season) != 4:
        raise ValueError(f"Game {game_pk} has no safe four-digit season")
    game_state = str(
        document.get("gameData", {}).get("status", {}).get("abstractGameState", "")
    )

    raw_path = pipeline_root / "raw" / "games" / season / game_pk / f"{input_hash}.json"
    archived_new = archive_source(input_path, raw_path, input_hash)
    manifest_path = (
        pipeline_root
        / "manifests"
        / "imports"
        / "games"
        / season
        / game_pk
        / f"{run_id}.json"
    )
    request_path = pipeline_root / "inbox" / "rdf" / f"{run_id}-{game_pk}.json"
    status = "archived-not-final" if game_state != "Final" else "queued-for-rdf"
    manifest: dict[str, Any] = {
        "artifactType": "game-json-manual-import",
        "ingestionMode": "nifi-manual-local-file",
        "pipelineRunId": run_id,
        "gamePk": game_pk,
        "season": season,
        "sourceFileName": source_filename,
        "importedAtUtc": started_at.isoformat().replace("+00:00", "Z"),
        "completedAtUtc": utc_now() if game_state != "Final" else None,
        "contentSha256": input_hash,
        "byteCount": input_bytes,
        "rawPath": str(raw_path),
        "archivedNew": archived_new,
        "feedAbstractGameState": game_state,
        "status": status,
        "graphIri": None,
        "semanticWorkRequest": str(request_path) if game_state == "Final" else None,
    }
    atomic_json(manifest_path, manifest)

    result: dict[str, Any] = {
        "artifactType": "baseball-nifi-game-archive-result",
        "pipelineRunId": run_id,
        "gamePk": game_pk,
        "season": season,
        "status": status,
        "rawPath": str(raw_path),
        "rawSha256": input_hash,
        "importManifestPath": str(manifest_path),
        "semanticWorkRequest": None,
    }
    if game_state == "Final":
        request = {
            "artifactType": "baseball-nifi-game-work-request",
            "contractVersion": 1,
            "pipelineRunId": run_id,
            "queuedAtUtc": utc_now(),
            "gamePk": game_pk,
            "season": season,
            "rawPath": str(raw_path),
            "rawSha256": input_hash,
            "importManifestPath": str(manifest_path),
            "forceRdfLoad": bool(args.force_rdf_load),
            "action": "pending",
            "stages": {},
        }
        try:
            atomic_json(request_path, request)
        except Exception:
            manifest["status"] = "queue-failed"
            manifest["completedAtUtc"] = utc_now()
            atomic_json(manifest_path, manifest)
            raise
        result["semanticWorkRequest"] = str(request_path)

    if sha256_file(input_path) != input_hash:
        raise RuntimeError("The supplied JSON changed while it was archived")
    print(json.dumps(result, separators=(",", ":"), ensure_ascii=False))


if __name__ == "__main__":
    main()
