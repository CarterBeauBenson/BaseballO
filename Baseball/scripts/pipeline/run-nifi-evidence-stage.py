#!/usr/bin/env python3
"""Run one repository-defined NiFi evidence stage with fail-closed manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONTRACT = REPOSITORY_ROOT / "infra" / "nifi" / "repeatable-stages.json"
MANIFEST_VERSION = 1
TAIL_LIMIT = 8_000


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", delete=False, dir=path.parent
    ) as output:
        json.dump(value, output, indent=2, ensure_ascii=False)
        output.write("\n")
        temporary = Path(output.name)
    os.replace(temporary, path)


def load_contract(path: Path) -> dict[str, Any]:
    contract = json.loads(path.read_text(encoding="utf-8"))
    if contract.get("contractVersion") != 1:
        raise ValueError("NiFi evidence contractVersion must be 1")
    stages = contract.get("stages")
    if not isinstance(stages, dict) or not stages:
        raise ValueError("NiFi evidence contract must define stages")
    return contract


def safe_matches(
    root: Path, patterns: list[str], label: str, *, require_each_pattern: bool = True
) -> tuple[list[Path], list[str]]:
    root = root.resolve()
    matches: set[Path] = set()
    unmatched: list[str] = []
    for pattern in patterns:
        if not isinstance(pattern, str) or not pattern or Path(pattern).is_absolute():
            raise ValueError(f"Invalid {label} glob: {pattern!r}")
        pattern_matches = [path.resolve() for path in root.glob(pattern) if path.is_file()]
        if not pattern_matches:
            if require_each_pattern:
                raise ValueError(f"{label} glob matched no files: {pattern}")
            unmatched.append(pattern)
            continue
        for path in pattern_matches:
            if path != root and root not in path.parents:
                raise ValueError(f"{label} escaped its root: {path}")
            matches.add(path)
    return sorted(matches, key=lambda path: path.relative_to(root).as_posix()), unmatched


def dependency_records(root: Path, paths: list[Path], scope: str) -> list[dict[str, Any]]:
    return [
        {
            "scope": scope,
            "path": path.relative_to(root).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in paths
    ]


def stage_fingerprint(
    stage_name: str,
    definition: dict[str, Any],
    contract_version: int,
    dependencies: list[dict[str, Any]],
) -> str:
    semantic_definition = {
        key: value
        for key, value in definition.items()
        if key not in {"description", "schedule"}
    }
    payload = {
        "stage": stage_name,
        "contractVersion": contract_version,
        "definition": semantic_definition,
        "dependencies": dependencies,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def executable(name: str) -> str:
    if name == "powershell" and os.environ.get("BASEBALLO_POWERSHELL"):
        configured = Path(os.environ["BASEBALLO_POWERSHELL"]).resolve()
        if configured.is_file():
            return str(configured)
        raise ValueError(f"Configured PowerShell executable is unavailable: {configured}")
    result = shutil.which(name)
    if not result:
        raise ValueError(f"Required executable is unavailable: {name}")
    return str(Path(result).resolve())


def expand_command(
    values: list[str], repository_root: Path, state_root: Path, artifact_directory: Path
) -> list[str]:
    replacements = {
        "{python}": sys.executable,
        "{powershell}": executable("powershell"),
        "{repositoryRoot}": str(repository_root),
        "{stateRoot}": str(state_root),
        "{artifactDirectory}": str(artifact_directory),
    }
    command: list[str] = []
    for value in values:
        if not isinstance(value, str) or not value:
            raise ValueError("Stage command entries must be non-empty strings")
        expanded = value
        for token, replacement in replacements.items():
            expanded = expanded.replace(token, replacement)
        if "{" in expanded or "}" in expanded:
            raise ValueError(f"Unknown command placeholder in {value!r}")
        command.append(expanded)
    if not command:
        raise ValueError("Stage command must not be empty")
    return command


def assert_loopback_ports(ports: list[Any]) -> None:
    for raw_port in ports:
        port = int(raw_port)
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=2):
                pass
        except OSError as exc:
            raise RuntimeError(f"Required loopback service is unavailable on port {port}") from exc


def tail(value: str) -> str:
    return value[-TAIL_LIMIT:]


def run_stage(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    repository_root = args.repository_root.resolve()
    contract_path = args.contract.resolve()
    state_root = args.state_root.resolve()
    contract = load_contract(contract_path)
    definition = contract["stages"].get(args.stage)
    if not isinstance(definition, dict):
        available = ", ".join(sorted(contract["stages"]))
        raise ValueError(f"Unknown NiFi evidence stage {args.stage!r}; available: {available}")

    dependency_paths, _ = safe_matches(
        repository_root, definition.get("dependencies", []), "repository dependency"
    )
    dependencies = dependency_records(repository_root, dependency_paths, "repository")
    state_patterns = definition.get("stateDependencies", [])
    unmatched_state_patterns: list[str] = []
    if state_patterns:
        state_paths, unmatched_state_patterns = safe_matches(
            state_root,
            state_patterns,
            "state dependency",
            require_each_pattern=False,
        )
        dependencies.extend(dependency_records(state_root, state_paths, "local-state"))
        dependencies.extend(
            {"scope": "local-state", "path": pattern, "missing": True}
            for pattern in unmatched_state_patterns
        )

    runner_path = Path(__file__).resolve()
    dependencies.append(
        {
            "scope": "runner",
            "path": runner_path.name,
            "bytes": runner_path.stat().st_size,
            "sha256": sha256_file(runner_path),
        }
    )
    contract_hash = sha256_file(contract_path)
    fingerprint = stage_fingerprint(
        args.stage, definition, int(contract["contractVersion"]), dependencies
    )
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid.uuid4().hex
    evidence_root = state_root / "pipeline" / "evidence" / "nifi" / args.stage
    run_root = evidence_root / "runs"
    latest_success_path = evidence_root / "latest-success.json"
    manifest_path = run_root / f"{run_id}.json"
    artifact_directory = evidence_root / "artifacts" / fingerprint
    started_at = utc_now()

    base_manifest: dict[str, Any] = {
        "artifactType": "baseball-nifi-stage-evidence",
        "manifestVersion": MANIFEST_VERSION,
        "runId": run_id,
        "stage": args.stage,
        "description": definition.get("description", ""),
        "startedAtUtc": started_at,
        "contractPath": contract_path.relative_to(repository_root).as_posix()
        if repository_root in contract_path.parents
        else str(contract_path),
        "contractSha256": contract_hash,
        "dependencyFingerprint": fingerprint,
        "cacheable": bool(definition.get("cacheable", False)),
        "dependencySummary": {
            "files": sum(1 for item in dependencies if not item.get("missing")),
            "repositoryFiles": sum(
                1 for item in dependencies if item["scope"] == "repository"
            ),
            "localStateFiles": sum(
                1 for item in dependencies if item["scope"] == "local-state" and not item.get("missing")
            ),
            "missingLocalStatePatterns": unmatched_state_patterns,
        },
    }

    if definition.get("cacheable", False) and not args.force and latest_success_path.is_file():
        previous = json.loads(latest_success_path.read_text(encoding="utf-8"))
        if previous.get("dependencyFingerprint") == fingerprint:
            manifest = {
                **base_manifest,
                "status": "skipped",
                "finishedAtUtc": utc_now(),
                "reason": "unchanged-dependency-fingerprint",
                "previousSuccessfulRunId": previous.get("runId"),
                "previousSuccessfulManifest": str(latest_success_path),
            }
            atomic_write_json(manifest_path, manifest)
            return manifest, 0

    artifact_directory.mkdir(parents=True, exist_ok=True)
    command: list[str] = []
    manifest = {**base_manifest, "status": "running"}
    atomic_write_json(manifest_path, manifest)

    started_clock = time.monotonic()
    try:
        command = expand_command(
            definition.get("command", []), repository_root, state_root, artifact_directory
        )
        manifest["command"] = command
        atomic_write_json(manifest_path, manifest)
        assert_loopback_ports(definition.get("requiresLoopbackPorts", []))
        completed = subprocess.run(
            command,
            cwd=repository_root,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=int(definition.get("timeoutSeconds", 900)),
            check=False,
        )
        exit_code = int(completed.returncode)
        stdout = completed.stdout
        stderr = completed.stderr
        error = None if exit_code == 0 else f"Stage command exited with status {exit_code}"
    except subprocess.TimeoutExpired as exc:
        exit_code = 124
        stdout = exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        error = f"Stage exceeded its {definition.get('timeoutSeconds', 900)} second timeout"
    except Exception as exc:  # The manifest and quarantine are the failure boundary.
        exit_code = 1
        stdout = ""
        stderr = str(exc)
        error = str(exc)

    combined_log = (
        f"stage={args.stage}\nrunId={run_id}\ncommand={json.dumps(command)}\n"
        f"\n--- stdout ---\n{stdout}\n--- stderr ---\n{stderr}"
    )
    log_path = run_root / f"{run_id}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(combined_log, encoding="utf-8", newline="\n")
    manifest.update(
        {
            "status": "succeeded" if exit_code == 0 else "failed",
            "finishedAtUtc": utc_now(),
            "durationMilliseconds": round((time.monotonic() - started_clock) * 1000),
            "exitCode": exit_code,
            "logPath": str(log_path),
            "logSha256": sha256_file(log_path),
            "stdoutTail": tail(stdout),
            "stderrTail": tail(stderr),
        }
    )
    if error:
        manifest["error"] = error
    if artifact_directory.exists():
        artifact_files = sorted(path for path in artifact_directory.rglob("*") if path.is_file())
        manifest["artifacts"] = [
            {
                "path": path.relative_to(artifact_directory).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in artifact_files
        ]
    atomic_write_json(manifest_path, manifest)

    if exit_code == 0:
        atomic_write_json(latest_success_path, manifest)
    else:
        quarantine = state_root / "pipeline" / "quarantine" / "nifi-evidence" / args.stage / run_id
        quarantine.mkdir(parents=True, exist_ok=False)
        shutil.copy2(manifest_path, quarantine / "manifest.json")
        shutil.copy2(log_path, quarantine / "stage.log")
        manifest["quarantinePath"] = str(quarantine)
        atomic_write_json(manifest_path, manifest)
        atomic_write_json(quarantine / "manifest.json", manifest)
    return manifest, exit_code


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True)
    parser.add_argument("--state-root", type=Path, required=True)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--repository-root", type=Path, default=REPOSITORY_ROOT)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        manifest, exit_code = run_stage(args)
    except Exception as exc:
        print(json.dumps({"status": "failed", "stage": args.stage, "error": str(exc)}))
        return 2
    print(json.dumps(manifest, separators=(",", ":"), ensure_ascii=False))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
