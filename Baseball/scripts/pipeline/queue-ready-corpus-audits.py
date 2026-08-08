#!/usr/bin/env python3
"""Queue one fail-closed corpus audit after every requested game is promoted."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
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
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", delete=False, dir=path.parent) as output:
        json.dump(value, output, indent=2, ensure_ascii=False)
        output.write("\n")
        temporary = Path(output.name)
    os.replace(temporary, path)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def newest_matching_promotion(root: Path, game_pk: str, raw_hash: str, submitted_at: datetime) -> Path | None:
    candidates: list[tuple[datetime, Path]] = []
    for path in (root / game_pk).glob("*.json"):
        try:
            value = load_json(path)
            promoted_at = datetime.fromisoformat(str(value["promotedAtUtc"]).replace("Z", "+00:00"))
            if (
                value.get("artifactType") == "baseball-nifi-game-promotion"
                and str(value.get("gamePk")) == game_pk
                and str(value.get("rawSha256")) == raw_hash
                and promoted_at >= submitted_at
            ):
                candidates.append((promoted_at, path.resolve()))
        except (KeyError, ValueError, OSError, json.JSONDecodeError):
            continue
    return max(candidates, default=(None, None), key=lambda item: item[0])[1]


def queue_ready(state_root: Path) -> dict[str, Any]:
    pipeline = state_root.resolve() / "pipeline"
    submissions = pipeline / "manifests" / "submissions"
    promotions = pipeline / "evidence" / "nifi" / "game-promotion"
    inbox = pipeline / "inbox" / "corpus-audits"
    staging = pipeline / "staging" / "corpus-audits"
    completions = pipeline / "evidence" / "nifi" / "corpus-completion"
    queued: list[str] = []
    waiting: dict[str, int] = {}

    for submission_path in sorted(submissions.glob("*.json")):
        submission = load_json(submission_path)
        if submission.get("artifactType") != "nifi-game-corpus-submission" or submission.get("auditRequested") is not True:
            continue
        run_id = str(submission.get("runId", ""))
        if not run_id or submission.get("auditStatus") == "audited":
            continue
        if (completions / f"{run_id}.json").is_file() or (inbox / f"{run_id}.json").is_file() or (staging / f"{run_id}.json").is_file():
            continue
        submitted_at = datetime.fromisoformat(str(submission["submittedAtUtc"]).replace("Z", "+00:00"))
        games = list(submission.get("games", []))
        if not games or len(games) != int(submission.get("uniqueGameCount", -1)):
            raise ValueError(f"Submission {run_id} has an inconsistent game list")
        promotion_records: list[dict[str, Any]] = []
        missing = 0
        for game in sorted(games, key=lambda item: int(item["gamePk"])):
            game_pk = str(game["gamePk"])
            raw_hash = str(game["sha256"])
            promotion_path = newest_matching_promotion(promotions, game_pk, raw_hash, submitted_at)
            if promotion_path is None:
                missing += 1
                continue
            promotion_records.append({
                "gamePk": game_pk,
                "rawSha256": raw_hash,
                "promotionManifest": str(promotion_path),
                "promotionManifestSha256": sha256_file(promotion_path),
            })
        if missing:
            waiting[run_id] = missing
            continue
        signature = "\n".join(f"{item['gamePk']}|{item['rawSha256']}" for item in promotion_records)
        request = {
            "artifactType": "baseball-nifi-corpus-audit-request",
            "contractVersion": 1,
            "submissionRunId": run_id,
            "queuedAtUtc": utc_now(),
            "corpusSha256": hashlib.sha256(signature.encode("utf-8")).hexdigest(),
            "gameCount": len(promotion_records),
            "auditScope": str(submission.get("auditScope", "accepted-2026-08-03-eight-game")),
            "submissionManifest": str(submission_path.resolve()),
            "games": promotion_records,
            "stages": {},
        }
        atomic_json(inbox / f"{run_id}.json", request)
        submission["auditStatus"] = "queued"
        submission["auditQueuedAtUtc"] = request["queuedAtUtc"]
        atomic_json(submission_path, submission)
        queued.append(run_id)

    return {"status": "succeeded", "queued": queued, "waiting": waiting, "checkedAtUtc": utc_now()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(queue_ready(args.state_root), separators=(",", ":")))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, separators=(",", ":")))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
