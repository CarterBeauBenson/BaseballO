#!/usr/bin/env python3
"""Fail closed unless a source lane has a completed, current proof run.

This is an operational release check. It does not make semantic decisions: it
only confirms that NiFi previously completed the source's bounded proof with
the mapping and SHACL files that are currently on disk.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-root", required=True, type=Path)
    parser.add_argument("--contract", required=True, type=Path)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read JSON evidence {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"JSON evidence is not an object: {path}")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def proof_identity(contract: dict[str, Any]) -> tuple[str, str, tuple[str, ...]]:
    module = str(contract.get("sourceModule", "")).strip()
    if not module:
        raise ValueError("flow contract has no sourceModule")
    if module == "mlb-game":
        scope = str(contract.get("proofGamePk", "")).strip()
        required = ("rml", "shacl", "promote", "materialize", "cleanup")
    else:
        request = contract.get("proofRequest")
        if not isinstance(request, dict):
            raise ValueError(f"{module} flow contract has no proofRequest")
        scope = str(request.get("scopeKey", "")).strip()
        required = ("rml", "shacl", "promote", "cleanup")
    if not scope:
        raise ValueError(f"{module} flow contract has no proof scope")
    return module, scope, required


def evidence_matches(
    run_directory: Path,
    module: str,
    scope: str,
    required: tuple[str, ...],
    contract: dict[str, Any],
    contract_path: Path,
) -> tuple[bool, str, dict[str, Any] | None]:
    records: dict[str, dict[str, Any]] = {}
    for action in required:
        path = run_directory / f"{action}.json"
        if not path.is_file():
            return False, f"missing {action}.json", None
        try:
            record = load_json(path)
        except ValueError as exc:
            return False, str(exc), None
        if str(record.get("action", "")) != action:
            return False, f"{path.name} does not record action {action}", None
        if str(record.get("pipelineRunId", "")) != run_directory.name:
            return False, f"{path.name} has a different pipelineRunId", None
        if module == "mlb-game":
            if str(record.get("gamePk", "")) != scope:
                return False, f"{path.name} has a different gamePk", None
        elif str(record.get("sourceModule", "")) != module or str(
            record.get("scopeKey", "")
        ) != scope:
            return False, f"{path.name} has a different source proof identity", None
        records[action] = record

    if records["shacl"].get("conforms") is not True:
        return False, "SHACL evidence does not conform", None
    if records["cleanup"].get("authoritativeRdfRemainsInGraphStore") is not True:
        return False, "cleanup evidence does not preserve authoritative RDF", None

    manifest_value = records["rml"].get("rmlManifest")
    if not isinstance(manifest_value, str) or not manifest_value:
        return False, "RML evidence has no manifest", None
    manifest_path = Path(manifest_value)
    if not manifest_path.is_file():
        return False, f"RML manifest is missing: {manifest_path}", None
    try:
        manifest = load_json(manifest_path)
    except ValueError as exc:
        return False, str(exc), None

    hash_pairs = (
        ("mappingPath", "mappingSha256", "mapping"),
        ("shaclShapePath", "shaclShapeSha256", "shacl"),
    )
    for path_key, hash_key, contract_key in hash_pairs:
        value = manifest.get(path_key)
        expected = str(manifest.get(hash_key, "")).lower()
        if not isinstance(value, str) or not value:
            relative = contract.get(contract_key)
            if not isinstance(relative, str) or not relative:
                return False, f"proof has no path for {contract_key}", None
            artifact = (contract_path.parent.parent / relative).resolve()
        else:
            artifact = Path(value)
        if not expected:
            return False, f"RML manifest has no {hash_key}", None
        if not artifact.is_file():
            return False, f"proof artifact is missing: {artifact}", None
        if sha256(artifact) != expected:
            return False, f"proof artifact changed after the proof: {artifact}", None

    return True, "released", records["cleanup"]


def main() -> int:
    args = parse_args()
    contract_path = args.contract.resolve()
    contract = load_json(contract_path)
    module, scope, required = proof_identity(contract)
    proof_root = args.state_root.resolve() / "pipeline" / "evidence" / module / scope
    if not proof_root.is_dir():
        raise ValueError(f"no proof evidence directory exists for {module}/{scope}")

    failures: list[str] = []
    run_directories = sorted(
        (item for item in proof_root.iterdir() if item.is_dir()),
        key=lambda item: (item.stat().st_mtime_ns, item.name),
        reverse=True,
    )
    for run_directory in run_directories:
        matched, reason, cleanup = evidence_matches(
            run_directory, module, scope, required, contract, contract_path
        )
        if matched:
            print(
                json.dumps(
                    {
                        "artifactType": "baseballo-source-proof-release",
                        "contractVersion": 1,
                        "sourceModule": module,
                        "proofScope": scope,
                        "proofRunId": run_directory.name,
                        "proofCompletedAtUtc": cleanup.get("completedAtUtc"),
                        "released": True,
                    },
                    separators=(",", ":"),
                )
            )
            return 0
        failures.append(f"{run_directory.name}: {reason}")

    detail = "; ".join(failures[:3]) or "no proof runs were found"
    raise ValueError(f"no current completed proof releases {module}: {detail}")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2)
