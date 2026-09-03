#!/usr/bin/env python3
"""Emit one immutable, source-owned promoted-graph event from promotion evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SOURCE_REGISTRY = ROOT / "sources" / "source-modules.json"


class EventError(ValueError):
    """Raised when promotion evidence cannot produce an admitted event."""


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise EventError(f"JSON artifact must be an object: {path}")
    return value


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require_contained_file(path: Path, root: Path, label: str) -> Path:
    resolved = path.resolve()
    if not resolved.is_file() or not resolved.is_relative_to(root.resolve()):
        raise EventError(f"{label} must be a file under {root}: {path}")
    return resolved


def source_modules() -> dict[str, dict[str, Any]]:
    registry = load_json(SOURCE_REGISTRY)
    if (
        registry.get("artifactType") != "baseballo-source-module-catalog"
        or registry.get("contractVersion") != 2
    ):
        raise EventError("The source-module registry contract is invalid")
    return {
        str(item.get("id")): item
        for item in registry.get("modules", [])
        if isinstance(item, dict)
    }


def normalize_promotion(evidence: dict[str, Any]) -> dict[str, Any]:
    artifact_type = evidence.get("artifactType")
    if artifact_type == "baseballo-source-graph-promotion":
        if evidence.get("contractVersion") != 1:
            raise EventError("Unsupported source-graph promotion contract")
        normalized = {
            "sourceModule": str(evidence.get("sourceModule", "")),
            "scopeKey": str(evidence.get("scopeKey", "")),
            "pipelineRunId": str(evidence.get("pipelineRunId", "")),
            "promotedAtUtc": str(evidence.get("promotedAtUtc", "")),
            "authoritativeGraph": str(evidence.get("authoritativeGraph", "")),
            "authoritativeTripleCount": evidence.get("tripleCount"),
            "authoritativeRdfSha256": str(evidence.get("rdfSha256", "")),
        }
    elif artifact_type == "baseball-nifi-game-promotion":
        if evidence.get("contractVersion") != 1:
            raise EventError("Unsupported game graph-pair promotion contract")
        normalized = {
            "sourceModule": "mlb-game",
            "scopeKey": f"game-{evidence.get('gamePk', '')}",
            "pipelineRunId": str(evidence.get("pipelineRunId", "")),
            "promotedAtUtc": str(evidence.get("promotedAtUtc", "")),
            "authoritativeGraph": str(evidence.get("authoritativeGraph", "")),
            "authoritativeTripleCount": evidence.get("authoritativeTripleCount"),
            "queryIndexGraph": str(evidence.get("queryIndexGraph", "")),
            "queryIndexTripleCount": evidence.get("queryIndexTripleCount"),
            "queryIndexManifest": str(evidence.get("queryIndexManifest", "")),
            "queryIndexManifestSha256": str(evidence.get("queryIndexManifestSha256", "")),
        }
    else:
        raise EventError(f"Unsupported promotion evidence type: {artifact_type!r}")

    for field in ("sourceModule", "scopeKey", "pipelineRunId", "promotedAtUtc", "authoritativeGraph"):
        if not normalized[field]:
            raise EventError(f"Promotion evidence lacks {field}")
    triple_count = normalized["authoritativeTripleCount"]
    if not isinstance(triple_count, int) or isinstance(triple_count, bool) or triple_count <= 0:
        raise EventError("Promotion evidence has an invalid authoritative triple count")
    return normalized


def atomic_write_immutable(path: Path, payload: dict[str, Any]) -> str:
    expected = canonical_bytes(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != expected:
            raise EventError(f"Immutable promoted-graph event already exists with different bytes: {path}")
        return "already-present"
    handle, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(expected)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return "created"


def emit(state_root: Path, promotion_evidence: Path) -> dict[str, Any]:
    evidence_root = state_root.resolve() / "pipeline" / "evidence"
    evidence_path = require_contained_file(promotion_evidence, evidence_root, "Promotion evidence")
    evidence = load_json(evidence_path)
    normalized = normalize_promotion(evidence)
    modules = source_modules()
    module_id = normalized["sourceModule"]
    if module_id not in modules:
        raise EventError(f"Promotion evidence names an unregistered source module: {module_id}")
    prefixes = modules[module_id].get("authoritativeGraphPrefixes")
    if (
        not isinstance(prefixes, list)
        or not any(normalized["authoritativeGraph"].startswith(str(prefix)) for prefix in prefixes)
    ):
        raise EventError("Promoted graph is outside its source module's registered namespace")

    evidence_sha256 = sha256_file(evidence_path)
    identity = {
        "sourceModule": module_id,
        "scopeKey": normalized["scopeKey"],
        "pipelineRunId": normalized["pipelineRunId"],
        "promotionEvidenceSha256": evidence_sha256,
    }
    event_id = hashlib.sha256(canonical_bytes(identity)).hexdigest()
    event = {
        "artifactType": "baseballo-promoted-graph-event",
        "contractVersion": 1,
        "eventId": event_id,
        **normalized,
        "promotionEvidence": str(evidence_path),
        "promotionEvidenceSha256": evidence_sha256,
    }
    event_path = (
        state_root.resolve()
        / "pipeline"
        / "events"
        / "promoted-graphs"
        / module_id
        / normalized["scopeKey"]
        / f"{event_id}.json"
    )
    status = atomic_write_immutable(event_path, event)
    return {
        "artifactType": "baseballo-promoted-graph-event-emission",
        "contractVersion": 1,
        "status": status,
        "eventId": event_id,
        "eventPath": str(event_path),
        "eventSha256": sha256_file(event_path),
        "sourceModule": module_id,
        "authoritativeGraph": normalized["authoritativeGraph"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-root", type=Path, required=True)
    parser.add_argument("--promotion-evidence", type=Path, required=True)
    parser.add_argument("--result-json", type=Path)
    args = parser.parse_args()
    try:
        result = emit(args.state_root, args.promotion_evidence)
        if args.result_json:
            args.result_json.parent.mkdir(parents=True, exist_ok=True)
            args.result_json.write_bytes(canonical_bytes(result))
        print(json.dumps(result, separators=(",", ":")))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, separators=(",", ":")))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
