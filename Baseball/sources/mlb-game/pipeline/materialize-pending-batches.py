#!/usr/bin/env python3
"""Materialize SQL once all games in a pending MLB schedule batch promoted."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MODULE_ROOT = Path(__file__).resolve().parents[1]
BASEBALL_ROOT = MODULE_ROOT.parents[1]
INVENTORY_SCRIPT = BASEBALL_ROOT / "scripts" / "pipeline" / "game_promotion_inventory.py"
MATERIALIZER = BASEBALL_ROOT / "scripts" / "pipeline" / "materialize-serving-layer.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-root", type=Path, required=True)
    return parser.parse_args()


def json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def timestamp(value: object) -> datetime:
    text = str(value).replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        raise ValueError("timestamp has no timezone")
    return parsed.astimezone(timezone.utc)


def atomic_json(path: Path, value: dict[str, Any]) -> None:
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


def promotion_inventory(state_root: Path) -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location("game_promotion_inventory", INVENTORY_SCRIPT)
    if spec is None or spec.loader is None:
        raise ValueError("cannot load the game promotion inventory")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.promotion_inventory(state_root)


def main() -> int:
    args = parse_args()
    state_root = args.state_root.resolve()
    batch_root = state_root / "pipeline" / "control" / "mlb-game" / "batches"
    batch_root.mkdir(parents=True, exist_ok=True)
    pending: list[tuple[datetime, Path, dict[str, Any]]] = []
    for path in sorted(batch_root.glob("*.json")):
        batch = json_object(path)
        if (
            batch.get("artifactType") != "baseballo-mlb-game-schedule-batch"
            or batch.get("contractVersion") != 1
        ):
            raise ValueError(f"unsupported game batch manifest: {path}")
        if batch.get("status") == "pending":
            pending.append((timestamp(batch.get("createdAtUtc")), path, batch))
    if not pending:
        print(json.dumps({"status": "idle", "pendingBatchCount": 0}, separators=(",", ":")))
        return 0

    inventory = promotion_inventory(state_root)
    games = inventory["games"]
    ready: list[tuple[Path, dict[str, Any]]] = []
    waiting: list[dict[str, Any]] = []
    for created, path, batch in sorted(pending, key=lambda item: (item[0], item[1].name)):
        missing: list[str] = []
        stale: list[str] = []
        for game_pk in batch.get("expectedGamePks", []):
            record = games.get(str(game_pk))
            if record is None:
                missing.append(str(game_pk))
            elif timestamp(record.get("promotedAtUtc")) < created:
                stale.append(str(game_pk))
        if missing or stale:
            waiting.append(
                {
                    "batchId": batch.get("batchId"),
                    "missingPromotionCount": len(missing),
                    "stalePromotionCount": len(stale),
                }
            )
        else:
            ready.append((path, batch))
    if not ready:
        print(
            json.dumps(
                {"status": "waiting", "pendingBatchCount": len(pending), "batches": waiting},
                separators=(",", ":"),
            )
        )
        return 0

    result = subprocess.run(
        [
            sys.executable,
            "-B",
            str(MATERIALIZER),
            "--state-root",
            str(state_root),
            "--retain-builds",
            "3",
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        raise ValueError(f"serving materialization failed: {result.stdout[-4000:]}")
    pointer_path = state_root / "serving" / "current.json"
    pointer = json_object(pointer_path)
    completed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    for path, batch in ready:
        batch["status"] = "materialized"
        batch["materializedAtUtc"] = completed_at
        batch["servingBuildId"] = pointer.get("buildId")
        batch["servingCorpusFingerprint"] = pointer.get("corpusFingerprint")
        batch["servingGameCount"] = pointer.get("gameCount")
        atomic_json(path, batch)
    print(
        json.dumps(
            {
                "status": "materialized",
                "materializedBatchCount": len(ready),
                "waitingBatchCount": len(waiting),
                "buildId": pointer.get("buildId"),
                "corpusFingerprint": pointer.get("corpusFingerprint"),
                "gameCount": pointer.get("gameCount"),
            },
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print(f"Pending MLB game batch materialization failed: {error}", file=sys.stderr)
        raise SystemExit(2)
