#!/usr/bin/env python3
"""Fail-closed semantic artifact freeze and proposal leakage validation.

This control records byte fingerprints.  It does not assert that the frozen
artifacts are semantically correct or accepted by the project ontologist.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Callable, Iterable
from urllib.parse import urlparse

from rdflib import Graph, URIRef


BASEBALL_ROOT = Path(__file__).resolve().parents[1]
GIT_ROOT = BASEBALL_ROOT.parent
DEFAULT_MANIFEST = BASEBALL_ROOT / "governance" / "semantic-freeze.json"
DEFAULT_REVIEW_SCHEMA = BASEBALL_ROOT / "governance" / "proposal-review.schema.json"
BOOTSTRAP_BASE_COMMIT = "cb16a8e6f3d487f3542b91907cde3f47ff0a0978"
ONTOLOGIST = "Carter Beau Benson"

FREEZE_ARTIFACT_TYPE = "baseballo-semantic-freeze"
FREEZE_CONTRACT_VERSION = 1
FREEZE_STATUS = "frozen-unratified"
HASH_CANONICALIZATION = "utf-8-sig decode; CRLF and CR to LF; UTF-8 encode without BOM"
RUNTIME_ARTIFACT_ROLES = {
    "mapping",
    "contextBuilder",
    "authoritativeShacl",
}
ACTIVE_PROPOSAL_STATUSES = {"draft", "under-review"}
TERMINAL_PROPOSAL_STATUSES = {"accepted", "rejected"}
ALL_PROPOSAL_STATUSES = ACTIVE_PROPOSAL_STATUSES | TERMINAL_PROPOSAL_STATUSES
REVIEW_ARTIFACT_FIELDS = {
    "competencyQuestions",
    "sourceEvidence",
    "fieldSelectionInventory",
    "sourceIndependentMermaid",
}
DECISION_FIELDS = {
    "disposition",
    "decidedBy",
    "decidedAt",
    "rationale",
    "authorizedArtifacts",
}
HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
PROPOSAL_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PREFIX_DECLARATION = re.compile(
    r"(?im)(?:@prefix|prefix)\s+([A-Za-z][A-Za-z0-9_-]*|):\s*<([^>]+)>"
)
SCRIPT_SUFFIXES = {".py", ".ps1", ".sh"}
STRUCTURED_SUFFIXES = {".json", ".yaml", ".yml", ".csv", ".ttl"}
SEMANTIC_RESPONSIBILITY_SCRIPT_PATHS = frozenset(
    {
        # The MLB-game context builder declares the source-to-world mapping
        # input consumed by its RML. Source-module context builders are already
        # protected by the sources/<module>/mapping boundary below.
        "scripts/pipeline/prepare-rml-context.py",
        # Operational validators, SHACL, SPARQL, serving code, and UI code are
        # deliberately outside the ontology and mapping approval freeze.
    }
)


class SemanticControlError(ValueError):
    """Raised when a semantic change-control invariant fails."""


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_semantic_bytes(value: bytes, *, description: str) -> bytes:
    """Canonicalize repository text identically across Git/Windows checkouts."""
    try:
        text = value.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise SemanticControlError(
            f"Protected semantic artifact is not UTF-8 text: {description}"
        ) from error
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def semantic_sha256_bytes(value: bytes, *, description: str) -> str:
    return sha256_bytes(canonical_semantic_bytes(value, description=description))


def semantic_sha256_file(path: Path) -> str:
    try:
        value = path.read_bytes()
    except OSError as error:
        raise SemanticControlError(f"Cannot read protected artifact {path}: {error}") from error
    return semantic_sha256_bytes(value, description=str(path))


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False) + "\n"


def _relative_posix(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _git_path(baseball_root: Path, relative: str) -> str:
    return f"{baseball_root.name}/{relative}"


def _baseball_relative(baseball_root: Path, git_path: str) -> str:
    prefix = f"{baseball_root.name}/"
    if not git_path.startswith(prefix):
        raise SemanticControlError(
            f"Protected path must be rooted at {prefix}: {git_path}"
        )
    relative = git_path[len(prefix) :]
    _validate_relative_path(relative, "protected artifact")
    return relative


def _validate_relative_path(value: str, description: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value:
        raise SemanticControlError(f"Invalid {description} path: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise SemanticControlError(f"Unsafe {description} path: {value!r}")
    return path


def is_protected_relative_path(relative: str) -> bool:
    """Return whether a Baseball-root-relative repository path is frozen."""
    try:
        path = _validate_relative_path(relative, "candidate")
    except SemanticControlError:
        return False
    parts = path.parts
    name = path.name.lower()
    suffix = path.suffix.lower()

    if len(parts) == 2 and parts[0] == "ontology" and name.endswith(".ttl"):
        return True
    if relative in {
        "sources/source-modules.json",
        "governance/ontology-curation-debt.json",
        "governance/proposal-review.schema.json",
    }:
        return True

    if len(parts) >= 4 and parts[0] == "sources":
        area = parts[2]
        if area == "mapping":
            return suffix != ".md" and suffix != ".pyc" and "__pycache__" not in parts
        if area == "review":
            return suffix in STRUCTURED_SUFFIXES

    if len(parts) >= 3 and parts[:2] == ("mappings", "policies"):
        return suffix in STRUCTURED_SUFFIXES
    if parts and parts[0] == "scripts" and suffix in SCRIPT_SUFFIXES:
        if len(parts) >= 2 and parts[1] == "reasoning":
            return True
        return relative in SEMANTIC_RESPONSIBILITY_SCRIPT_PATHS

    if parts and parts[0] == "reasoning":
        if relative in {
            "reasoning/bfo-clif-manifest.json",
            "reasoning/profile-admission-tests.json",
            "reasoning/reviewed-samples.json",
        }:
            return True
        return len(parts) >= 3 and parts[1] == "profiles" and suffix == ".json"
    return False


def is_bootstrap_semantic_payload(relative: str) -> bool:
    """Identify payloads that the one-time freeze bootstrap may not alter."""
    path = PurePosixPath(relative)
    parts = path.parts
    name = path.name.lower()
    suffix = path.suffix.lower()
    if len(parts) == 2 and parts[0] == "ontology" and name.endswith(".ttl"):
        return True
    if len(parts) >= 4 and parts[0] == "sources":
        if parts[2] == "mapping":
            return suffix != ".md" and suffix != ".pyc" and "__pycache__" not in parts
    if len(parts) >= 3 and parts[:2] == ("mappings", "policies"):
        return suffix in STRUCTURED_SUFFIXES
    if parts and parts[0] == "reasoning":
        return is_protected_relative_path(relative)
    if len(parts) >= 2 and parts[:2] == ("scripts", "reasoning"):
        return is_protected_relative_path(relative)
    return relative == "scripts/pipeline/prepare-rml-context.py"


def discover_protected_artifacts(baseball_root: Path = BASEBALL_ROOT) -> set[str]:
    protected: set[str] = set()
    for path in baseball_root.rglob("*"):
        if not path.is_file():
            continue
        relative = _relative_posix(path, baseball_root)
        if is_protected_relative_path(relative):
            protected.add(_git_path(baseball_root, relative))
    return protected


def protected_set_sha256(artifacts: dict[str, str]) -> str:
    payload = "".join(f"{path}\0{artifacts[path]}\n" for path in sorted(artifacts))
    return sha256_bytes(payload.encode("utf-8"))


def _load_json(path: Path, description: str) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SemanticControlError(f"Cannot read {description} {path}: {error}") from error
    if not isinstance(value, dict):
        raise SemanticControlError(f"{description} must be a JSON object: {path}")
    return value


def validate_freeze_header(manifest: dict) -> None:
    if manifest.get("artifactType") != FREEZE_ARTIFACT_TYPE:
        raise SemanticControlError("Semantic freeze has an unknown artifactType")
    if manifest.get("contractVersion") != FREEZE_CONTRACT_VERSION:
        raise SemanticControlError("Semantic freeze contractVersion must be 1")
    if manifest.get("status") != FREEZE_STATUS or manifest.get("ratified") is not False:
        raise SemanticControlError(
            "Semantic baseline must be labeled frozen-unratified with ratified=false"
        )
    if manifest.get("bootstrapBaseCommit") != BOOTSTRAP_BASE_COMMIT:
        raise SemanticControlError("Semantic freeze has an unexpected bootstrap base")
    if manifest.get("hashCanonicalization") != HASH_CANONICALIZATION:
        raise SemanticControlError("Semantic freeze hash canonicalization is unknown")
    artifacts = manifest.get("protectedArtifacts")
    if not isinstance(artifacts, dict) or not artifacts:
        raise SemanticControlError("Semantic freeze protectedArtifacts must be non-empty")
    admissions = manifest.get("runtimeAdmissions")
    if not isinstance(admissions, list):
        raise SemanticControlError("Semantic freeze runtimeAdmissions must be an array")
    if "accepted" in str(manifest.get("status", "")).lower():
        raise SemanticControlError("A frozen baseline may never claim acceptance")


def _validate_protected_artifact_map(artifacts: dict) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for path, digest in artifacts.items():
        if not isinstance(path, str):
            raise SemanticControlError("Protected artifact paths must be strings")
        _validate_relative_path(path, "protected artifact")
        if not isinstance(digest, str) or not HEX_SHA256.fullmatch(digest):
            raise SemanticControlError(f"Invalid SHA-256 for protected artifact {path}")
        normalized[path] = digest
    return normalized


def _validate_runtime_admission_shape(
    manifest: dict, admission: dict, *, module_id: str | None = None
) -> dict[str, dict[str, str]]:
    if not isinstance(admission, dict):
        raise SemanticControlError("Runtime admission entries must be objects")
    expected_fields = {
        "moduleId",
        "operationalStatus",
        "semanticStatus",
        "artifacts",
    }
    if set(admission) != expected_fields:
        raise SemanticControlError(
            f"Runtime admission has unexpected fields: {sorted(set(admission) ^ expected_fields)}"
        )
    current_module = admission.get("moduleId")
    if not isinstance(current_module, str) or not PROPOSAL_ID.fullmatch(current_module):
        raise SemanticControlError(f"Invalid runtime moduleId: {current_module!r}")
    if module_id is not None and current_module != module_id:
        raise SemanticControlError(
            f"Runtime admission module mismatch: expected {module_id}, found {current_module}"
        )
    operational = admission.get("operationalStatus")
    semantic = admission.get("semanticStatus")
    if operational != "active":
        raise SemanticControlError(
            f"Runtime module {current_module} is not operationally active: {operational!r}"
        )
    if (
        not isinstance(semantic, str)
        or not semantic.startswith("frozen-")
        or any(word in semantic.lower() for word in ("accepted", "approved", "ratified"))
    ):
        raise SemanticControlError(
            f"Runtime module {current_module} lacks a frozen, unratified semantic state"
        )
    role_map = admission.get("artifacts")
    if not isinstance(role_map, dict) or set(role_map) != RUNTIME_ARTIFACT_ROLES:
        raise SemanticControlError(
            f"Runtime module {current_module} must pin exactly {sorted(RUNTIME_ARTIFACT_ROLES)}"
        )
    result: dict[str, dict[str, str]] = {}
    for role in sorted(RUNTIME_ARTIFACT_ROLES):
        pin = role_map[role]
        if not isinstance(pin, dict) or set(pin) != {"path", "sha256"}:
            raise SemanticControlError(
                f"Runtime {current_module}/{role} pin must contain path and sha256"
            )
        path = pin.get("path")
        digest = pin.get("sha256")
        if not isinstance(path, str):
            raise SemanticControlError(
                f"Runtime {current_module}/{role} pin has an invalid path"
            )
        _baseball_relative(BASEBALL_ROOT, path)
        if not isinstance(digest, str) or not HEX_SHA256.fullmatch(digest):
            raise SemanticControlError(
                f"Runtime {current_module}/{role} pin has an invalid SHA-256"
            )
        result[role] = {"path": path, "sha256": digest}
    return result


def validate_runtime_admission(
    module_id: str,
    *,
    baseball_root: Path = BASEBALL_ROOT,
    manifest_path: Path = DEFAULT_MANIFEST,
) -> dict:
    manifest = _load_json(manifest_path, "semantic freeze")
    validate_freeze_header(manifest)
    matches = [
        entry
        for entry in manifest["runtimeAdmissions"]
        if isinstance(entry, dict) and entry.get("moduleId") == module_id
    ]
    if len(matches) != 1:
        raise SemanticControlError(
            f"Expected exactly one runtime admission for {module_id}; found {len(matches)}"
        )
    pins = _validate_runtime_admission_shape(manifest, matches[0], module_id=module_id)
    for role, pin in pins.items():
        relative = _baseball_relative(baseball_root, pin["path"])
        path = baseball_root / relative
        if not path.is_file() or semantic_sha256_file(path) != pin["sha256"]:
            raise SemanticControlError(
                f"Runtime pin mismatch for {module_id}/{role}: {pin['path']}"
            )
    return matches[0]


def validate_freeze_manifest(
    *,
    baseball_root: Path = BASEBALL_ROOT,
    manifest_path: Path = DEFAULT_MANIFEST,
) -> tuple[dict, int]:
    manifest = _load_json(manifest_path, "semantic freeze")
    validate_freeze_header(manifest)
    protected = _validate_protected_artifact_map(manifest["protectedArtifacts"])
    discovered = discover_protected_artifacts(baseball_root)
    declared = set(protected)
    missing = sorted(declared - discovered)
    additions = sorted(discovered - declared)
    if missing or additions:
        raise SemanticControlError(
            "Semantic protected set changed; "
            f"missing={missing}, unregistered={additions}"
        )
    for git_path, expected_hash in protected.items():
        relative = _baseball_relative(baseball_root, git_path)
        actual_hash = semantic_sha256_file(baseball_root / relative)
        if actual_hash != expected_hash:
            raise SemanticControlError(
                f"Frozen semantic artifact changed: {git_path}; "
                f"expected {expected_hash}, found {actual_hash}"
            )
    expected_set_hash = protected_set_sha256(protected)
    if manifest.get("protectedSetSha256") != expected_set_hash:
        raise SemanticControlError("Semantic freeze protectedSetSha256 is stale")

    seen_modules: set[str] = set()
    for admission in manifest["runtimeAdmissions"]:
        _validate_runtime_admission_shape(manifest, admission)
        module_id = admission["moduleId"]
        if module_id in seen_modules:
            raise SemanticControlError(f"Duplicate runtime admission: {module_id}")
        seen_modules.add(module_id)
    return manifest, len(protected)


def _validate_iri(value: object) -> str:
    if not isinstance(value, str):
        raise SemanticControlError(f"Proposed IRI must be a string: {value!r}")
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or any(
        character.isspace() for character in value
    ):
        raise SemanticControlError(f"Proposed IRI must be an absolute HTTP(S) IRI: {value!r}")
    return value


def _validate_review_artifact_path(
    value: object,
    *,
    proposal_directory: Path | None,
    require_files: bool,
) -> tuple[str, str]:
    if not isinstance(value, dict) or set(value) != {"path", "sha256"}:
        raise SemanticControlError(
            "Review artifacts must be exact {path, sha256} objects"
        )
    artifact_path = value.get("path")
    digest = value.get("sha256")
    if not isinstance(artifact_path, str):
        raise SemanticControlError("Review artifact path must be a string")
    relative = _validate_relative_path(artifact_path, "review artifact")
    if not isinstance(digest, str) or not HEX_SHA256.fullmatch(digest):
        raise SemanticControlError(
            f"Review artifact has an invalid canonical SHA-256: {artifact_path}"
        )
    if require_files:
        if proposal_directory is None:
            raise SemanticControlError(
                "Review artifact verification requires a proposal directory"
            )
        resolved = (proposal_directory / Path(*relative.parts)).resolve()
        if not resolved.is_relative_to(proposal_directory.resolve()) or not resolved.is_file():
            raise SemanticControlError(f"Review artifact does not exist: {artifact_path}")
        actual = semantic_sha256_file(resolved)
        if actual != digest:
            raise SemanticControlError(
                f"Review artifact canonical SHA-256 mismatch: {artifact_path}"
            )
    return artifact_path, digest


def validate_review_record(
    record: dict,
    *,
    record_path: str,
    active: bool,
    proposal_directory: Path | None = None,
    require_artifact_files: bool = False,
) -> set[str]:
    expected_fields = {
        "$schema",
        "artifactType",
        "schemaVersion",
        "proposalId",
        "title",
        "status",
        "proposedIris",
        "artifacts",
        "ontologistDecision",
    }
    if set(record) != expected_fields:
        raise SemanticControlError(
            f"Proposal review {record_path} has unexpected fields: "
            f"{sorted(set(record) ^ expected_fields)}"
        )
    schema_ref = record.get("$schema")
    if not isinstance(schema_ref, str) or not re.fullmatch(
        r"(?:\.\./)+governance/proposal-review\.schema\.json", schema_ref
    ):
        raise SemanticControlError(f"Proposal review {record_path} has an invalid $schema")
    if (
        record.get("artifactType") != "baseballo-semantic-proposal-review"
        or record.get("schemaVersion") != 1
    ):
        raise SemanticControlError(f"Proposal review {record_path} has an invalid envelope")
    proposal_id = record.get("proposalId")
    if not isinstance(proposal_id, str) or not PROPOSAL_ID.fullmatch(proposal_id):
        raise SemanticControlError(f"Proposal review {record_path} has an invalid proposalId")
    if proposal_directory is not None and proposal_id != proposal_directory.name:
        raise SemanticControlError(
            f"Proposal review id {proposal_id} differs from directory {proposal_directory.name}"
        )
    if not isinstance(record.get("title"), str) or not record["title"].strip():
        raise SemanticControlError(f"Proposal review {record_path} has no title")
    status = record.get("status")
    if status not in ALL_PROPOSAL_STATUSES:
        raise SemanticControlError(f"Proposal review {record_path} has invalid status {status!r}")
    if active and status not in ACTIVE_PROPOSAL_STATUSES:
        raise SemanticControlError(
            f"Active proposal {proposal_id} may only be draft or under-review"
        )

    proposed = record.get("proposedIris")
    if not isinstance(proposed, list):
        raise SemanticControlError(f"Proposal review {record_path} proposedIris must be an array")
    proposed_iris = [_validate_iri(value) for value in proposed]
    if len(proposed_iris) != len(set(proposed_iris)):
        raise SemanticControlError(f"Proposal review {record_path} repeats a proposed IRI")

    artifacts = record.get("artifacts")
    if not isinstance(artifacts, dict) or set(artifacts) != REVIEW_ARTIFACT_FIELDS:
        raise SemanticControlError(
            f"Proposal review {record_path} must declare exactly {sorted(REVIEW_ARTIFACT_FIELDS)}"
        )
    for field in sorted(REVIEW_ARTIFACT_FIELDS):
        values = artifacts[field]
        if not isinstance(values, list):
            raise SemanticControlError(
                f"Proposal review {record_path} artifact field {field} must be an array"
            )
        normalized = [
            _validate_review_artifact_path(
                value,
                proposal_directory=proposal_directory,
                require_files=require_artifact_files and status == "under-review",
            )
            for value in values
        ]
        normalized_paths = [path for path, _ in normalized]
        if len(normalized_paths) != len(set(normalized_paths)):
            raise SemanticControlError(
                f"Proposal review {record_path} repeats an artifact in {field}"
            )
    if status in {"under-review", "accepted"} and any(
        not artifacts[field] for field in REVIEW_ARTIFACT_FIELDS
    ):
        raise SemanticControlError(
            f"Proposal {proposal_id} has not completed every pre-review artifact family"
        )

    decision = record.get("ontologistDecision")
    if status in ACTIVE_PROPOSAL_STATUSES:
        if decision is not None:
            raise SemanticControlError(
                f"Active proposal {proposal_id} may not carry an ontologist decision"
            )
    else:
        if not isinstance(decision, dict) or set(decision) != DECISION_FIELDS:
            raise SemanticControlError(
                f"Terminal proposal {proposal_id} lacks an exact ontologistDecision"
            )
        if decision.get("disposition") != status:
            raise SemanticControlError(
                f"Proposal {proposal_id} decision does not match status {status}"
            )
        if decision.get("decidedBy") != ONTOLOGIST:
            raise SemanticControlError(
                f"Proposal {proposal_id} decision must be made by {ONTOLOGIST}"
            )
        if not isinstance(decision.get("rationale"), str) or not decision["rationale"].strip():
            raise SemanticControlError(
                f"Proposal {proposal_id} decision lacks rationale"
            )
        decided_at = decision.get("decidedAt")
        try:
            if not isinstance(decided_at, str) or date.fromisoformat(decided_at).isoformat() != decided_at:
                raise ValueError
        except ValueError as error:
            raise SemanticControlError(
                f"Proposal {proposal_id} decision has invalid decidedAt"
            ) from error
        authorized = decision.get("authorizedArtifacts")
        if not isinstance(authorized, list):
            raise SemanticControlError(
                f"Proposal {proposal_id} authorizedArtifacts must be an array"
            )
        checked = []
        for value in authorized:
            if not isinstance(value, str):
                raise SemanticControlError(
                    f"Proposal {proposal_id} authorized artifact must be a string"
                )
            _validate_relative_path(value, "authorized artifact")
            if not value.startswith("Baseball/"):
                raise SemanticControlError(
                    f"Proposal {proposal_id} authorized artifact must be Git-root-relative"
                )
            checked.append(value)
        if len(checked) != len(set(checked)):
            raise SemanticControlError(
                f"Proposal {proposal_id} repeats an authorized artifact"
            )
    return set(proposed_iris)


def collect_active_proposed_iris(
    *, baseball_root: Path = BASEBALL_ROOT
) -> tuple[set[str], int]:
    proposal_root = baseball_root / "proposals"
    if not proposal_root.is_dir():
        raise SemanticControlError("Active proposal directory is missing")
    proposed_iris: set[str] = set()
    proposal_count = 0
    for proposal_directory in sorted(path for path in proposal_root.iterdir() if path.is_dir()):
        review_path = proposal_directory / "review.json"
        if not review_path.is_file():
            raise SemanticControlError(
                f"Active proposal lacks review.json: {proposal_directory.name}"
            )
        record = _load_json(review_path, "proposal review")
        current = validate_review_record(
            record,
            record_path=_relative_posix(review_path, baseball_root),
            active=True,
            proposal_directory=proposal_directory,
            require_artifact_files=True,
        )
        overlap = proposed_iris & current
        if overlap:
            raise SemanticControlError(
                f"Proposed IRIs are owned by multiple active proposals: {sorted(overlap)}"
            )
        proposed_iris.update(current)
        proposal_count += 1
    return proposed_iris, proposal_count


def is_executable_leakage_path(relative: str) -> bool:
    path = PurePosixPath(relative)
    parts = path.parts
    suffix = path.suffix.lower()
    name = path.name.lower()
    if parts and parts[0] == "ontology" and name.endswith(".ttl"):
        return True
    if len(parts) >= 4 and parts[0] == "sources":
        if parts[2] == "mapping" and (
            name.endswith(".rml.ttl")
            or "policy" in name
            or "coverage" in name
            or "registry" in name
            or "gap" in name
        ):
            return True
        if parts[2] == "shacl" and name.endswith(".ttl"):
            return True
    if relative == "sources/source-modules.json":
        return True
    if parts and parts[0] == "shacl" and name.endswith(".ttl"):
        return True
    if parts and parts[0] == "sparql" and suffix in {".rq", ".json"}:
        return True
    if parts and parts[0] == "reasoning" and suffix in {
        ".json",
        ".ttl",
        ".clif",
        ".py",
        ".ps1",
    }:
        return True
    if len(parts) >= 2 and parts[:2] == ("scripts", "reasoning"):
        return suffix in SCRIPT_SUFFIXES | {".json", ".clif", ".ttl"}
    if parts and parts[0] == "serving":
        return suffix in {".json", ".sql", ".py", ".js", ".mjs", ".rq", ".ttl"}
    if parts and parts[0] == "web" and "node_modules" not in parts:
        return suffix in {".js", ".mjs", ".json", ".html", ".css", ".rq", ".sql"}
    if len(parts) >= 3 and parts[:2] == ("scripts", "pipeline") and "serving" in name:
        return suffix in SCRIPT_SUFFIXES | {".sql", ".json"}
    if len(parts) >= 3 and parts[:2] == ("mappings", "policies"):
        return suffix in STRUCTURED_SUFFIXES
    return False


def discover_executable_leakage_files(baseball_root: Path = BASEBALL_ROOT) -> list[Path]:
    files = []
    for path in baseball_root.rglob("*"):
        if not path.is_file():
            continue
        relative = _relative_posix(path, baseball_root)
        if is_executable_leakage_path(relative):
            files.append(path)
    return sorted(files)


def _qname_variants(text: str, iri: str) -> set[str]:
    variants: set[str] = set()
    for match in PREFIX_DECLARATION.finditer(text):
        prefix, namespace = match.groups()
        if not iri.startswith(namespace):
            continue
        local = iri[len(namespace) :]
        if local and re.fullmatch(r"[A-Za-z0-9_.~-]+", local):
            variants.add(f"{prefix}{local}" if prefix == ":" else f"{prefix}:{local}")
    return variants


def _text_contains_iri(text: str, iri: str) -> bool:
    if iri in text:
        return True
    for qname in _qname_variants(text, iri):
        if re.search(
            rf"(?<![A-Za-z0-9_.~-]){re.escape(qname)}(?![A-Za-z0-9_.~-])",
            text,
        ):
            return True
    return False


def find_proposal_iri_leaks(
    proposed_iris: set[str], *, baseball_root: Path = BASEBALL_ROOT
) -> list[tuple[str, str]]:
    if not proposed_iris:
        return []
    leaks: list[tuple[str, str]] = []
    for path in discover_executable_leakage_files(baseball_root):
        relative = _relative_posix(path, baseball_root)
        if path.name.lower().endswith(".ttl"):
            try:
                graph = Graph().parse(path, format="turtle")
            except Exception as error:
                raise SemanticControlError(
                    f"Cannot parse executable Turtle while checking proposal leakage: {relative}: {error}"
                ) from error
            used_iris = {
                str(term)
                for triple in graph
                for term in triple
                if isinstance(term, URIRef)
            }
            for iri in sorted(proposed_iris & used_iris):
                leaks.append((relative, iri))
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise SemanticControlError(
                f"Cannot read executable artifact for proposal leakage: {relative}: {error}"
            ) from error
        for iri in sorted(proposed_iris):
            if _text_contains_iri(text, iri):
                leaks.append((relative, iri))
    return leaks


def validate_active_proposals_and_leakage(
    *, baseball_root: Path = BASEBALL_ROOT
) -> tuple[int, int]:
    proposed_iris, proposal_count = collect_active_proposed_iris(
        baseball_root=baseball_root
    )
    leaks = find_proposal_iri_leaks(proposed_iris, baseball_root=baseball_root)
    if leaks:
        rendered = ", ".join(f"{path} -> {iri}" for path, iri in leaks)
        raise SemanticControlError(
            "Active proposal IRIs leaked into executable artifacts: " + rendered
        )
    return proposal_count, len(proposed_iris)


def _run_git(git_root: Path, arguments: list[str], *, check: bool = True) -> bytes:
    command = [
        "git",
        "-c",
        f"safe.directory={git_root.resolve().as_posix()}",
        *arguments,
    ]
    result = subprocess.run(
        command,
        cwd=git_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise SemanticControlError(
            f"Git command failed ({' '.join(arguments)}): {stderr}"
        )
    return result.stdout


def _resolve_commit(git_root: Path, reference: str) -> str:
    output = _run_git(git_root, ["rev-parse", "--verify", f"{reference}^{{commit}}"])
    commit = output.decode("ascii", errors="strict").strip()
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise SemanticControlError(f"Git reference is not a commit: {reference}")
    return commit


def _git_blob(git_root: Path, commit: str, git_path: str) -> bytes | None:
    _validate_relative_path(git_path, "Git blob")
    result = subprocess.run(
        [
            "git",
            "-c",
            f"safe.directory={git_root.resolve().as_posix()}",
            "show",
            f"{commit}:{git_path}",
        ],
        cwd=git_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode == 0:
        return result.stdout
    return None


def _git_json(git_root: Path, commit: str, git_path: str, description: str) -> dict | None:
    blob = _git_blob(git_root, commit, git_path)
    if blob is None:
        return None
    try:
        value = json.loads(blob.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise SemanticControlError(
            f"Cannot parse {description} at {commit[:12]}:{git_path}: {error}"
        ) from error
    if not isinstance(value, dict):
        raise SemanticControlError(
            f"{description} at {commit[:12]}:{git_path} must be an object"
        )
    return value


def _validate_manifest_at_ref(
    git_root: Path, baseball_root: Path, commit: str, manifest: dict
) -> dict[str, str]:
    validate_freeze_header(manifest)
    protected = _validate_protected_artifact_map(manifest["protectedArtifacts"])
    # The manifest records the protection boundary that applied at this
    # historical commit. Reclassifying that tree with the validator currently
    # checked out would make an ordinary classifier change retroactively
    # invalidate an otherwise valid decision-only commit. Exact discovery for
    # the current checkout remains the responsibility of
    # validate_freeze_manifest().
    for path, digest in protected.items():
        blob = _git_blob(git_root, commit, path)
        if blob is None or semantic_sha256_bytes(blob, description=path) != digest:
            raise SemanticControlError(
                f"Protected artifact at {commit[:12]} differs from freeze: {path}"
            )
    if manifest.get("protectedSetSha256") != protected_set_sha256(protected):
        raise SemanticControlError(
            f"Protected set fingerprint is stale at {commit[:12]}"
        )
    for admission in manifest["runtimeAdmissions"]:
        _validate_runtime_admission_shape(manifest, admission)
    return protected


def _git_changed_paths(git_root: Path, base_commit: str, head_commit: str) -> set[str]:
    output = _run_git(
        git_root,
        ["diff", "--name-only", "--no-renames", base_commit, head_commit, "--"],
    )
    return {
        line.strip()
        for line in output.decode("utf-8", errors="strict").splitlines()
        if line.strip()
    }


def _validate_change_decision(
    *,
    manifest: dict,
    changed_protected: set[str],
    base_decision_blob: bytes | None,
    head_decision_blob: bytes | None,
    base_artifact_loader: Callable[[str], bytes | None],
) -> None:
    decision_pointer = manifest.get("changeDecision")
    if not isinstance(decision_pointer, dict) or set(decision_pointer) != {
        "path",
        "sha256",
    }:
        raise SemanticControlError(
            "Protected semantic changes require an exact archived changeDecision pointer"
        )
    decision_path = decision_pointer.get("path")
    decision_hash = decision_pointer.get("sha256")
    if (
        not isinstance(decision_path, str)
        or not decision_path.startswith("Baseball/archive/design-records/")
        or not decision_path.endswith("/review.json")
    ):
        raise SemanticControlError(
            "changeDecision must point to an archived design-record review.json"
        )
    if not isinstance(decision_hash, str) or not HEX_SHA256.fullmatch(decision_hash):
        raise SemanticControlError("changeDecision has an invalid SHA-256")
    if base_decision_blob is None:
        raise SemanticControlError(
            "The archived design decision was not present in the base commit"
        )
    if head_decision_blob != base_decision_blob:
        raise SemanticControlError(
            "The archived design decision changed with the protected implementation"
        )
    if semantic_sha256_bytes(
        base_decision_blob, description=str(decision_path)
    ) != decision_hash:
        raise SemanticControlError("changeDecision SHA-256 differs from the base decision")
    try:
        record = json.loads(base_decision_blob.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise SemanticControlError(f"Archived design decision is invalid JSON: {error}") from error
    if not isinstance(record, dict):
        raise SemanticControlError("Archived design decision must be an object")
    validate_review_record(
        record,
        record_path=decision_path,
        active=False,
        require_artifact_files=False,
    )
    if record.get("status") != "accepted":
        raise SemanticControlError("Only an explicitly accepted archived decision may authorize change")
    decision_directory = PurePosixPath(decision_path).parent
    for field in sorted(REVIEW_ARTIFACT_FIELDS):
        for artifact in record["artifacts"][field]:
            artifact_path = (decision_directory / artifact["path"]).as_posix()
            blob = base_artifact_loader(artifact_path)
            if blob is None:
                raise SemanticControlError(
                    "Accepted review artifact was not present in the base commit: "
                    f"{artifact_path}"
                )
            actual = semantic_sha256_bytes(blob, description=artifact_path)
            if actual != artifact["sha256"]:
                raise SemanticControlError(
                    "Accepted review artifact differs from its base-commit pin: "
                    f"{artifact_path}"
                )
    authorized = set(record["ontologistDecision"]["authorizedArtifacts"])
    uncovered = sorted(changed_protected - authorized)
    if uncovered:
        raise SemanticControlError(
            f"Archived decision does not authorize changed protected artifacts: {uncovered}"
        )


def validate_git_ordering_gate(
    base_ref: str,
    *,
    head_ref: str = "HEAD",
    baseball_root: Path = BASEBALL_ROOT,
    git_root: Path = GIT_ROOT,
) -> tuple[str, str, int]:
    base_commit = _resolve_commit(git_root, base_ref)
    head_commit = _resolve_commit(git_root, head_ref)
    manifest_git_path = f"{baseball_root.name}/governance/semantic-freeze.json"
    base_manifest = _git_json(
        git_root, base_commit, manifest_git_path, "base semantic freeze"
    )
    head_manifest = _git_json(
        git_root, head_commit, manifest_git_path, "head semantic freeze"
    )
    if head_manifest is None:
        raise SemanticControlError("Head commit has no semantic freeze manifest")
    head_protected = _validate_manifest_at_ref(
        git_root, baseball_root, head_commit, head_manifest
    )

    if base_manifest is None:
        if (
            base_commit != BOOTSTRAP_BASE_COMMIT
            or head_manifest.get("bootstrapBaseCommit") != BOOTSTRAP_BASE_COMMIT
        ):
            raise SemanticControlError(
                "Missing base freeze is permitted only for the recorded one-time bootstrap"
            )
        changed = _git_changed_paths(git_root, base_commit, head_commit)
        forbidden = sorted(
            path
            for path in changed
            if path.startswith(f"{baseball_root.name}/")
            and is_bootstrap_semantic_payload(
                path[len(baseball_root.name) + 1 :]
            )
        )
        if forbidden:
            raise SemanticControlError(
                "One-time freeze bootstrap changed semantic payloads: " + ", ".join(forbidden)
            )
        return base_commit, head_commit, 0

    base_protected = _validate_manifest_at_ref(
        git_root, baseball_root, base_commit, base_manifest
    )
    changed_protected = {
        path
        for path in set(base_protected) | set(head_protected)
        if base_protected.get(path) != head_protected.get(path)
    }
    if not changed_protected:
        return base_commit, head_commit, 0

    pointer = head_manifest.get("changeDecision")
    decision_path = pointer.get("path") if isinstance(pointer, dict) else ""
    base_blob = (
        _git_blob(git_root, base_commit, decision_path)
        if isinstance(decision_path, str) and decision_path
        else None
    )
    head_blob = (
        _git_blob(git_root, head_commit, decision_path)
        if isinstance(decision_path, str) and decision_path
        else None
    )
    _validate_change_decision(
        manifest=head_manifest,
        changed_protected=changed_protected,
        base_decision_blob=base_blob,
        head_decision_blob=head_blob,
        base_artifact_loader=lambda path: _git_blob(git_root, base_commit, path),
    )
    return base_commit, head_commit, len(changed_protected)


def _bootstrap_runtime_admissions(
    baseball_root: Path, protected: dict[str, str], catalog: dict
) -> list[dict]:
    """Create the one-module bootstrap admission when no freeze exists yet."""
    modules = catalog.get("modules", [])
    if not isinstance(modules, list) or len(modules) != 1:
        raise SemanticControlError(
            "A new freeze may bootstrap only the mlb-game runtime admission; "
            "additional modules require explicit pins in an existing freeze"
        )
    module = modules[0]
    if not isinstance(module, dict) or module.get("id") != "mlb-game":
        raise SemanticControlError(
            "A new freeze may bootstrap only the mlb-game runtime admission"
        )
    rml = module.get("rml", [])
    shacl = module.get("shacl", [])
    if len(rml) != 1 or len(shacl) != 1:
        raise SemanticControlError(
            "Default runtime pin requires one RML and one SHACL file: mlb-game"
        )
    paths = {
        "mapping": _git_path(baseball_root, str(rml[0])),
        "contextBuilder": _git_path(
            baseball_root, "scripts/pipeline/prepare-rml-context.py"
        ),
        "authoritativeShacl": _git_path(baseball_root, str(shacl[0])),
    }
    role_map = {}
    for role, path in paths.items():
        relative = _baseball_relative(baseball_root, path)
        digest = semantic_sha256_file(baseball_root / relative)
        role_map[role] = {"path": path, "sha256": digest}
    return [
        {
            "moduleId": "mlb-game",
            "operationalStatus": module.get(
                "operationalStatus", module.get("status", "active")
            ),
            "semanticStatus": module.get("semanticStatus", "frozen-known-debt"),
            "artifacts": role_map,
        }
    ]


def _pinned_runtime_admissions(
    baseball_root: Path, protected: dict[str, str]
) -> list[dict]:
    """Refresh already explicit runtime pins without admitting a new module."""
    catalog_path = baseball_root / "sources" / "source-modules.json"
    catalog = _load_json(catalog_path, "source-module catalog")
    manifest_path = baseball_root / "governance" / "semantic-freeze.json"
    if not manifest_path.is_file():
        return _bootstrap_runtime_admissions(baseball_root, protected, catalog)

    current_manifest = _load_json(manifest_path, "existing semantic freeze")
    validate_freeze_header(current_manifest)
    current_admissions = current_manifest["runtimeAdmissions"]
    admission_by_module: dict[str, dict] = {}
    for admission in current_admissions:
        if not isinstance(admission, dict):
            raise SemanticControlError("Runtime admission entries must be objects")
        module_id = admission.get("moduleId")
        if not isinstance(module_id, str) or module_id in admission_by_module:
            raise SemanticControlError(
                f"Existing freeze has an invalid or repeated runtime module: {module_id!r}"
            )
        admission_by_module[module_id] = admission

    modules = catalog.get("modules", [])
    if not isinstance(modules, list):
        raise SemanticControlError("Source-module catalog modules must be an array")
    catalog_by_module: dict[str, dict] = {}
    for module in modules:
        if not isinstance(module, dict):
            raise SemanticControlError("Source-module catalog entries must be objects")
        module_id = module.get("id")
        if not isinstance(module_id, str) or module_id in catalog_by_module:
            raise SemanticControlError(
                f"Source-module catalog has an invalid or repeated id: {module_id!r}"
            )
        catalog_by_module[module_id] = module

    if set(catalog_by_module) != set(admission_by_module):
        missing = sorted(set(catalog_by_module) - set(admission_by_module))
        retired = sorted(set(admission_by_module) - set(catalog_by_module))
        raise SemanticControlError(
            "Runtime admission set differs from the source-module catalog; "
            f"explicit decision required (missing pins={missing}, retired pins={retired})"
        )

    admissions: list[dict] = []
    for module_id in [module.get("id") for module in modules]:
        module = catalog_by_module[module_id]
        current = admission_by_module[module_id]
        rml = module.get("rml", [])
        shacl = module.get("shacl", [])
        if len(rml) != 1 or len(shacl) != 1:
            raise SemanticControlError(
                f"Runtime pin requires one RML and one SHACL file: {module_id}"
            )
        current_roles = current.get("artifacts")
        if not isinstance(current_roles, dict) or set(current_roles) != RUNTIME_ARTIFACT_ROLES:
            raise SemanticControlError(
                f"Existing runtime admission has invalid artifact roles: {module_id}"
            )
        for role in sorted(RUNTIME_ARTIFACT_ROLES):
            pin = current_roles[role]
            if not isinstance(pin, dict) or set(pin) != {"path", "sha256"}:
                raise SemanticControlError(
                    f"Runtime {module_id}/{role} pin must contain path and sha256"
                )
        expected_mapping = _git_path(baseball_root, str(rml[0]))
        expected_shacl = _git_path(baseball_root, str(shacl[0]))
        if current_roles["mapping"].get("path") != expected_mapping:
            raise SemanticControlError(
                f"Runtime mapping pin differs from the source catalog: {module_id}"
            )
        if current_roles["authoritativeShacl"].get("path") != expected_shacl:
            raise SemanticControlError(
                f"Runtime SHACL pin differs from the source catalog: {module_id}"
            )
        role_map = {}
        for role in sorted(RUNTIME_ARTIFACT_ROLES):
            pin = current_roles[role]
            path = pin.get("path")
            relative = _baseball_relative(baseball_root, path)
            digest = semantic_sha256_file(baseball_root / relative)
            role_map[role] = {"path": path, "sha256": digest}
        refreshed = {
            "moduleId": module_id,
            "operationalStatus": current.get("operationalStatus"),
            "semanticStatus": current.get("semanticStatus"),
            "artifacts": role_map,
        }
        _validate_runtime_admission_shape(
            {"protectedArtifacts": protected}, refreshed, module_id=module_id
        )
        admissions.append(refreshed)
    return admissions


def build_freeze_manifest(
    *,
    baseball_root: Path = BASEBALL_ROOT,
    change_decision: str | None = None,
) -> dict:
    protected_paths = discover_protected_artifacts(baseball_root)
    protected = {
        path: semantic_sha256_file(
            baseball_root / _baseball_relative(baseball_root, path)
        )
        for path in sorted(protected_paths)
    }
    decision_pointer = None
    if change_decision is not None:
        _validate_relative_path(change_decision, "change decision")
        if not change_decision.startswith("Baseball/archive/design-records/"):
            raise SemanticControlError("Change decision must be an archived design record")
        decision_file = baseball_root.parent / Path(*PurePosixPath(change_decision).parts)
        if not decision_file.is_file():
            raise SemanticControlError(f"Change decision does not exist: {change_decision}")
        decision_pointer = {
            "path": change_decision,
            "sha256": semantic_sha256_file(decision_file),
        }
    return {
        "artifactType": FREEZE_ARTIFACT_TYPE,
        "contractVersion": FREEZE_CONTRACT_VERSION,
        "status": FREEZE_STATUS,
        "ratified": False,
        "bootstrapBaseCommit": BOOTSTRAP_BASE_COMMIT,
        "hashCanonicalization": HASH_CANONICALIZATION,
        "protectedSetSha256": protected_set_sha256(protected),
        "changeDecision": decision_pointer,
        "protectedArtifacts": protected,
        "runtimeAdmissions": _pinned_runtime_admissions(baseball_root, protected),
    }


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate BaseballO's frozen, unratified semantic artifact boundary."
    )
    parser.add_argument("--root", type=Path, default=BASEBALL_ROOT)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--base-ref")
    parser.add_argument("--head-ref", default="HEAD")
    parser.add_argument("--runtime-admission", metavar="MODULE_ID")
    parser.add_argument(
        "--print-manifest",
        action="store_true",
        help="Print a freshly fingerprinted manifest; never writes or implies approval.",
    )
    parser.add_argument(
        "--change-decision",
        help="Archived Git-root-relative review.json to record while printing a manifest.",
    )
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    baseball_root = args.root.resolve()
    git_root = baseball_root.parent
    manifest_path = (
        args.manifest.resolve()
        if args.manifest is not None
        else baseball_root / "governance" / "semantic-freeze.json"
    )
    try:
        if args.print_manifest:
            if args.runtime_admission or args.base_ref:
                raise SemanticControlError(
                    "--print-manifest cannot be combined with runtime or Git validation"
                )
            manifest = build_freeze_manifest(
                baseball_root=baseball_root,
                change_decision=args.change_decision,
            )
            sys.stdout.write(canonical_json(manifest))
            return 0
        if args.change_decision:
            raise SemanticControlError("--change-decision requires --print-manifest")
        if args.runtime_admission:
            if args.base_ref:
                raise SemanticControlError(
                    "--runtime-admission validates only its byte pins and cannot use --base-ref"
                )
            admission = validate_runtime_admission(
                args.runtime_admission,
                baseball_root=baseball_root,
                manifest_path=manifest_path,
            )
            print(
                f"Runtime admission verified: {admission['moduleId']} "
                f"operational={admission['operationalStatus']} "
                f"semantic={admission['semanticStatus']} "
                "(frozen/unratified pin; not semantic acceptance)."
            )
            return 0

        _, protected_count = validate_freeze_manifest(
            baseball_root=baseball_root,
            manifest_path=manifest_path,
        )
        proposal_count, proposed_iri_count = validate_active_proposals_and_leakage(
            baseball_root=baseball_root
        )
        print(
            f"Semantic freeze verified: {protected_count} exact artifacts; "
            "baseline is frozen/unratified, not accepted."
        )
        print(
            f"Active proposal gate verified: {proposal_count} proposals, "
            f"{proposed_iri_count} exact proposed IRIs, no executable leakage."
        )
        if args.base_ref:
            base, head, changed = validate_git_ordering_gate(
                args.base_ref,
                head_ref=args.head_ref,
                baseball_root=baseball_root,
                git_root=git_root,
            )
            print(
                f"Semantic Git ordering verified: {base[:12]}..{head[:12]}, "
                f"{changed} authorized protected changes."
            )
        return 0
    except SemanticControlError as error:
        print(f"Semantic change control failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
