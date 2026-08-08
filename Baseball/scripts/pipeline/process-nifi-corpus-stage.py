#!/usr/bin/env python3
"""Run one event-driven corpus audit stage and preserve its request/evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
STAGES = {
    "canned": "canned-query-audit",
    "advanced": "advanced-query-audit",
    "equivalence": "authoritative-index-equivalence",
    "benchmark": "benchmark-evidence",
}


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


def within(path: Path, root: Path, label: str) -> Path:
    path = path.resolve()
    root = root.resolve()
    if path == root or root not in path.parents:
        raise ValueError(f"{label} is outside {root}: {path}")
    return path


def run(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    state_root = args.state_root.resolve()
    pipeline = state_root / "pipeline"
    request_path = within(args.request, pipeline / "staging" / "corpus-audits", "Corpus request")
    request = load_json(request_path)
    if request.get("artifactType") != "baseball-nifi-corpus-audit-request" or request.get("contractVersion") != 1:
        raise ValueError("Unsupported corpus audit request contract")
    submission_id = str(request.get("submissionRunId", ""))
    if not submission_id or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-" for character in submission_id):
        raise ValueError("Unsafe corpus submission identifier")
    evidence_root = pipeline / "evidence" / "nifi" / "corpus-audit" / submission_id
    wrapper_manifest = evidence_root / f"{args.stage}.json"
    log_path = evidence_root / f"{args.stage}.log"
    quarantine = pipeline / "quarantine" / "nifi-corpus-audit" / submission_id / args.stage
    started = utc_now()
    log_text = ""

    try:
        if args.stage in STAGES:
            stage_name = STAGES[args.stage]
            command = [
                sys.executable,
                str(REPOSITORY_ROOT / "scripts" / "pipeline" / "run-nifi-evidence-stage.py"),
                "--contract", str(REPOSITORY_ROOT / "infra" / "nifi" / "repeatable-stages.json"),
                "--stage", stage_name,
                "--state-root", str(state_root),
                "--force",
            ]
            completed = subprocess.run(command, cwd=REPOSITORY_ROOT, text=True, encoding="utf-8", errors="replace", capture_output=True, check=False)
            log_text = f"--- stdout ---\n{completed.stdout}\n--- stderr ---\n{completed.stderr}"
            if completed.returncode != 0:
                raise RuntimeError(f"Evidence stage {stage_name} failed with status {completed.returncode}")
            result = json.loads(completed.stdout)
            if result.get("status") != "succeeded":
                raise RuntimeError(f"Evidence stage {stage_name} did not succeed")
            stage_manifest = pipeline / "evidence" / "nifi" / stage_name / "runs" / f"{result['runId']}.json"
            if not stage_manifest.is_file():
                raise RuntimeError(f"Evidence stage {stage_name} produced no manifest")
            request.setdefault("stages", {})[args.stage] = {
                "status": "succeeded",
                "completedAtUtc": utc_now(),
                "evidenceManifest": str(stage_manifest.resolve()),
                "evidenceManifestSha256": sha256_file(stage_manifest),
            }
            atomic_json(request_path, request)
            stage_result: dict[str, Any] = {"evidenceStage": stage_name, **request["stages"][args.stage]}
        else:
            missing = [stage for stage in STAGES if request.get("stages", {}).get(stage, {}).get("status") != "succeeded"]
            if missing:
                raise RuntimeError(f"Corpus completion refused; missing stages: {', '.join(missing)}")
            stage_records = []
            for stage in STAGES:
                evidence_path = within(Path(request["stages"][stage]["evidenceManifest"]), state_root, "Stage evidence")
                if not evidence_path.is_file() or sha256_file(evidence_path) != request["stages"][stage]["evidenceManifestSha256"]:
                    raise RuntimeError(f"Corpus completion refused; stale evidence for {stage}")
                evidence = load_json(evidence_path)
                if evidence.get("status") != "succeeded":
                    raise RuntimeError(f"Corpus completion refused; failed evidence for {stage}")
                stage_records.append({"stage": stage, "manifest": str(evidence_path), "sha256": sha256_file(evidence_path)})
            completion_path = pipeline / "evidence" / "nifi" / "corpus-completion" / f"{submission_id}.json"
            submission_path = within(Path(request["submissionManifest"]), pipeline / "manifests" / "submissions", "Submission manifest")
            submission = load_json(submission_path)
            completion = {
                "artifactType": "baseball-nifi-corpus-completion",
                "contractVersion": 1,
                "submissionRunId": submission_id,
                "completedAtUtc": utc_now(),
                "corpusSha256": request["corpusSha256"],
                "gameCount": request["gameCount"],
                "auditScope": request["auditScope"],
                "stages": stage_records,
            }
            request.setdefault("stages", {})["complete"] = {"status": "succeeded", "completedAtUtc": completion["completedAtUtc"]}
            atomic_json(request_path, request)
            submission["auditStatus"] = "audited"
            submission["auditCompletedAtUtc"] = completion["completedAtUtc"]
            submission["auditCompletionManifest"] = str(completion_path.resolve())
            atomic_json(submission_path, submission)
            stage_result = {"completionManifest": str(completion_path.resolve()), "gameCount": request["gameCount"]}

        evidence_root.mkdir(parents=True, exist_ok=True)
        log_path.write_text(log_text, encoding="utf-8", newline="\n")
        wrapper = {
            "artifactType": "baseball-nifi-corpus-stage-evidence",
            "contractVersion": 1,
            "submissionRunId": submission_id,
            "stage": args.stage,
            "status": "succeeded",
            "startedAtUtc": started,
            "completedAtUtc": utc_now(),
            "result": stage_result,
            "logPath": str(log_path.resolve()),
            "logSha256": sha256_file(log_path),
        }
        atomic_json(wrapper_manifest, wrapper)
        if args.stage == "complete":
            atomic_json(Path(stage_result["completionManifest"]), completion)
            request_path.unlink()
        return wrapper, 0
    except Exception as exc:
        evidence_root.mkdir(parents=True, exist_ok=True)
        log_path.write_text(f"{log_text}\n{exc}\n", encoding="utf-8", newline="\n")
        failure = {
            "artifactType": "baseball-nifi-corpus-stage-evidence",
            "contractVersion": 1,
            "submissionRunId": submission_id,
            "stage": args.stage,
            "status": "failed",
            "startedAtUtc": started,
            "failedAtUtc": utc_now(),
            "error": str(exc),
            "quarantinePath": str(quarantine.resolve()),
        }
        atomic_json(wrapper_manifest, failure)
        quarantine.mkdir(parents=True, exist_ok=False)
        shutil.copy2(request_path, quarantine / "request.json")
        shutil.copy2(wrapper_manifest, quarantine / "manifest.json")
        shutil.copy2(log_path, quarantine / "stage.log")
        return failure, 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=[*STAGES, "complete"], required=True)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--state-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        manifest, status = run(args)
    except Exception as exc:
        print(json.dumps({"status": "failed", "stage": args.stage, "error": str(exc)}, separators=(",", ":")))
        return 2
    print(json.dumps(manifest, separators=(",", ":")))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
