#!/usr/bin/env python3
"""Run the aggregate repository gate and persist immutable NiFi evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "scripts" / "validate_repository.py"


class ObserverError(RuntimeError):
    """The repository observer could not produce trustworthy evidence."""


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def atomic_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{uuid.uuid4().hex}.tmp")
    temporary.write_bytes(value)
    os.replace(temporary, path)


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    atomic_bytes(
        path,
        (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8"),
    )


def acquire_lock(path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise ObserverError("Repository validation observer is already running") from exc
    os.write(descriptor, f"{os.getpid()}\n".encode("ascii"))
    return descriptor


def record_validation(
    state_root: Path,
    *,
    validator: Path = VALIDATOR,
    python: str = sys.executable,
    timeout_seconds: int = 3600,
) -> tuple[dict[str, Any], int]:
    state_root = state_root.resolve()
    validator = validator.resolve()
    if not validator.is_file():
        raise ObserverError(f"Repository validator is missing: {validator}")
    evidence_root = state_root / "pipeline" / "evidence" / "repository-validation"
    lock_path = state_root / "pipeline" / "locks" / "repository-validation.lock"
    descriptor = acquire_lock(lock_path)
    started = dt.datetime.now(dt.timezone.utc)
    build_id = started.strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid.uuid4().hex[:8]
    stdout_path = evidence_root / f"{build_id}.stdout.log"
    stderr_path = evidence_root / f"{build_id}.stderr.log"
    evidence_path = evidence_root / f"{build_id}.json"
    start_clock = time.perf_counter()
    try:
        try:
            completed = subprocess.run(
                [python, str(validator)],
                cwd=ROOT,
                capture_output=True,
                timeout=timeout_seconds,
                check=False,
            )
            stdout = completed.stdout
            stderr = completed.stderr
            exit_code = int(completed.returncode)
            error = None
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout or b""
            stderr = exc.stderr or b""
            exit_code = 124
            error = f"Aggregate repository validation exceeded {timeout_seconds} seconds"
        atomic_bytes(stdout_path, stdout)
        atomic_bytes(stderr_path, stderr)
        completed_at = dt.datetime.now(dt.timezone.utc)
        evidence: dict[str, Any] = {
            "artifactType": "baseballo-repository-validation-evidence",
            "contractVersion": 1,
            "runId": build_id,
            "status": "passed" if exit_code == 0 else "failed",
            "startedAtUtc": started.isoformat().replace("+00:00", "Z"),
            "completedAtUtc": completed_at.isoformat().replace("+00:00", "Z"),
            "durationMilliseconds": round((time.perf_counter() - start_clock) * 1000, 3),
            "exitCode": exit_code,
            "validatorPath": str(validator),
            "validatorSha256": sha256_file(validator),
            "stdoutPath": str(stdout_path.resolve()),
            "stdoutSha256": sha256_bytes(stdout),
            "stdoutBytes": len(stdout),
            "stderrPath": str(stderr_path.resolve()),
            "stderrSha256": sha256_bytes(stderr),
            "stderrBytes": len(stderr),
            "failureDoesNotControlSourceLanes": True,
            "failureDoesNotChangeRdfOrServingPointers": True,
        }
        if error:
            evidence["error"] = error
        atomic_json(evidence_path, evidence)
        evidence["evidencePath"] = str(evidence_path.resolve())
        return evidence, exit_code
    finally:
        os.close(descriptor)
        lock_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    default_state = Path(
        os.environ.get("BASEBALLO_STATE_ROOT")
        or Path(os.environ.get("LOCALAPPDATA", ".")) / "BaseballO" / "state"
    )
    parser.add_argument("--state-root", type=Path, default=default_state)
    parser.add_argument("--timeout-seconds", type=int, default=3600)
    args = parser.parse_args()
    if args.timeout_seconds <= 0:
        print(json.dumps({"status": "failed", "error": "timeout must be positive"}))
        return 2
    try:
        evidence, exit_code = record_validation(
            args.state_root, timeout_seconds=args.timeout_seconds
        )
        print(json.dumps(evidence, separators=(",", ":"), ensure_ascii=True))
        return exit_code
    except (ObserverError, OSError, ValueError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, separators=(",", ":")))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
