#!/usr/bin/env python3
"""Compare pending SQL candidates with authoritative Explorer results."""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import hashlib
import importlib.util
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
BASE_ACCEPTANCE_PATH = ROOT / "scripts" / "pipeline" / "verify-explorer-serving.py"
SPEC = importlib.util.spec_from_file_location("baseballo_base_acceptance", BASE_ACCEPTANCE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Could not load {BASE_ACCEPTANCE_PATH}")
BASE_ACCEPTANCE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE_ACCEPTANCE)

FAMILIES = frozenset({"paq", "advanced", "explore", "empty-games", "derived", "all"})
PAQ_PREFIX = "advanced:plate-appearance-fingerprint"


class EquivalenceError(RuntimeError):
    """A candidate result differs from its authoritative reference result."""


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def request_json(
    base_url: str,
    path: str,
    body: dict[str, Any] | None,
    *,
    timeout_seconds: float,
    layer: str,
    equivalence_token: str | None = None,
) -> tuple[dict[str, Any], float]:
    headers = {"Accept": "application/json", "Connection": "close"}
    if layer == "authoritative":
        headers["X-BaseballO-Force-Authoritative"] = "true"
    elif layer == "candidate-sql":
        if not equivalence_token:
            raise EquivalenceError("Candidate SQL proof requires an equivalence token")
        headers["X-BaseballO-Use-Candidate-Sql"] = "true"
        headers["X-BaseballO-Require-Materialized"] = "true"
        headers["X-BaseballO-Equivalence-Token"] = equivalence_token
    else:
        raise EquivalenceError(f"Unknown proof layer: {layer}")
    encoded = None
    method = "GET"
    if body is not None:
        encoded = json.dumps(body, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json"
        method = "POST"
    request = Request(base_url.rstrip("/") + path, data=encoded, headers=headers, method=method)
    started = time.perf_counter()
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read()
            status = response.status
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise EquivalenceError(f"{layer} {method} {path} returned HTTP {exc.code}: {detail}") from exc
    except (URLError, TimeoutError) as exc:
        raise EquivalenceError(f"{layer} {method} {path} failed: {exc}") from exc
    if status != 200:
        raise EquivalenceError(f"{layer} {method} {path} returned HTTP {status}")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EquivalenceError(f"{layer} {method} {path} did not return UTF-8 JSON") from exc
    if not isinstance(payload, dict):
        raise EquivalenceError(f"{layer} {method} {path} did not return a JSON object")
    return payload, round((time.perf_counter() - started) * 1000, 3)


def fetch_catalogs(base_url: str, timeout_seconds: float) -> dict[str, dict[str, Any]]:
    catalogs: dict[str, dict[str, Any]] = {}
    for name, path in (
        ("explore", "/api/catalog"),
        ("advanced", "/api/advanced/catalog"),
        ("empty", "/api/empty-games/catalog"),
        ("derived", "/api/derived/catalog"),
    ):
        request = Request(base_url.rstrip("/") + path, headers={"Accept": "application/json", "Connection": "close"})
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                value = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise EquivalenceError(f"Could not read Explorer catalog {path}: {exc}") from exc
        if not isinstance(value, dict):
            raise EquivalenceError(f"Explorer catalog {path} is not an object")
        catalogs[name] = value
    return catalogs


@contextlib.contextmanager
def managed_explorer(state_root: Path, timeout_seconds: float):
    node = shutil.which("node")
    if not node:
        raise EquivalenceError("Node.js is required for the isolated equivalence Explorer")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        port = int(listener.getsockname()[1])
    token = uuid.uuid4().hex + uuid.uuid4().hex
    environment = os.environ.copy()
    environment.update({
        "PORT": str(port),
        "BASEBALLO_STATE_ROOT": str(state_root.resolve()),
        "BASEBALLO_PYTHON": sys.executable,
        "BASEBALLO_EQUIVALENCE_TOKEN": token,
    })
    process = subprocess.Popen(
        [node, str(ROOT / "web" / "server.mjs")],
        cwd=ROOT / "web",
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    base_url = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + min(30.0, timeout_seconds)
    try:
        while time.monotonic() < deadline:
            if process.poll() is not None:
                stdout, stderr = process.communicate(timeout=1)
                raise EquivalenceError(
                    f"Isolated equivalence Explorer exited early: {(stderr or stdout).strip()}"
                )
            try:
                with urlopen(base_url + "/api/catalog", timeout=1) as response:
                    if response.status == 200:
                        break
            except (HTTPError, URLError, TimeoutError):
                time.sleep(0.2)
        else:
            raise EquivalenceError("Isolated equivalence Explorer did not become ready")
        yield base_url, token
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def selected_probes(catalogs: dict[str, dict[str, Any]], family: str) -> list[dict[str, Any]]:
    probes = [probe for probe in BASE_ACCEPTANCE.build_probes(catalogs) if probe["kind"] == "result"]
    if family == "paq":
        selected = [probe for probe in probes if probe["name"].startswith(PAQ_PREFIX)]
    elif family == "advanced":
        selected = [
            probe for probe in probes
            if probe["name"].startswith("advanced:") and not probe["name"].startswith(PAQ_PREFIX)
        ]
    elif family == "explore":
        selected = [probe for probe in probes if probe["name"].startswith("explore:")]
    elif family == "empty-games":
        selected = [probe for probe in probes if probe["name"].startswith("empty-games:")]
    elif family == "derived":
        selected = [probe for probe in probes if probe["name"].startswith("derived:")]
    else:
        selected = probes
    if not selected:
        raise EquivalenceError(f"No equivalence probes were generated for {family}")
    return selected


def result_signature(payload: dict[str, Any], label: str) -> dict[str, Any]:
    head = payload.get("head")
    results = payload.get("results")
    if not isinstance(head, dict) or not isinstance(head.get("vars"), list):
        raise EquivalenceError(f"{label} has no result-variable list")
    if not isinstance(results, dict) or not isinstance(results.get("bindings"), list):
        raise EquivalenceError(f"{label} has no result bindings")
    variables = head["vars"]
    if any(not isinstance(variable, str) or not variable for variable in variables):
        raise EquivalenceError(f"{label} has an invalid result variable")
    canonical_rows: list[str] = []
    for row in results["bindings"]:
        if not isinstance(row, dict):
            raise EquivalenceError(f"{label} contains a non-object binding")
        terms = []
        for variable in variables:
            term = row.get(variable)
            if term is None:
                terms.append(None)
                continue
            if not isinstance(term, dict) or not isinstance(term.get("type"), str) or not isinstance(term.get("value"), str):
                raise EquivalenceError(f"{label} has an invalid RDF term for {variable}")
            terms.append({
                key: term[key]
                for key in ("type", "value", "datatype", "xml:lang")
                if key in term
            })
        canonical_rows.append(canonical_json(terms))
    sequence = "\n".join(canonical_rows).encode("utf-8")
    row_set = "\n".join(sorted(canonical_rows)).encode("utf-8")
    return {
        "variables": variables,
        "rowCount": len(canonical_rows),
        "rowSequenceSha256": hashlib.sha256(sequence).hexdigest(),
        "rowMultisetSha256": hashlib.sha256(row_set).hexdigest(),
    }


def response_metadata(payload: dict[str, Any], expected_layer: str, label: str) -> dict[str, Any]:
    meta = payload.get("meta")
    accepted_layers = {expected_layer}
    if expected_layer == "authoritative":
        accepted_layers.add("unified")
    if not isinstance(meta, dict) or meta.get("layer") not in accepted_layers:
        raise EquivalenceError(f"{label} did not execute on {expected_layer}")
    build_id = meta.get("servingBuildId")
    fingerprint = meta.get("corpusFingerprint")
    if expected_layer == "materialized" and (not isinstance(build_id, str) or not build_id):
        raise EquivalenceError(f"{label} has no SQL build ID")
    if not isinstance(fingerprint, str) or len(fingerprint) != 64:
        raise EquivalenceError(f"{label} has no valid corpus fingerprint")
    return {"buildId": build_id, "corpusFingerprint": fingerprint}


def atomic_evidence(path: Path, evidence: dict[str, Any]) -> None:
    path = path.resolve()
    if path.exists():
        raise EquivalenceError(f"Refusing to overwrite equivalence evidence: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def prove(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    started = dt.datetime.now(dt.timezone.utc)
    run_id = started.strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid.uuid4().hex[:8]
    evidence: dict[str, Any] = {
        "artifactType": "baseballo-explorer-family-equivalence-evidence",
        "contractVersion": 1,
        "runId": run_id,
        "family": args.family,
        "status": "failed",
        "startedAtUtc": started.isoformat().replace("+00:00", "Z"),
        "comparison": "exact RDF-term bindings, variable order, row multiset, and row sequence",
        "admissionEffect": "none; ontologist-approved serving contract remains the route authority",
        "artifacts": {
            "serverSha256": sha256_file(ROOT / "web" / "server.mjs"),
            "servingAdapterSha256": sha256_file(ROOT / "scripts" / "pipeline" / "query-serving-layer.py"),
            "candidateAdapterSha256": sha256_file(ROOT / "scripts" / "pipeline" / "query-serving-candidate.py"),
            "servingContractSha256": sha256_file(ROOT / "serving" / "contract.json"),
            "servingSchemaSha256": sha256_file(ROOT / "serving" / "schema.sql"),
        },
        "probes": [],
    }
    exit_code = 1
    build_id: str | None = None
    fingerprint: str | None = None
    try:
        catalogs = fetch_catalogs(args.base_url, args.timeout_seconds)
        for probe in selected_probes(catalogs, args.family):
            authoritative, authoritative_ms = request_json(
                args.base_url, probe["path"], probe.get("body"),
                timeout_seconds=args.timeout_seconds, layer="authoritative",
                equivalence_token=args.equivalence_token,
            )
            candidate, candidate_ms = request_json(
                args.base_url, probe["path"], probe.get("body"),
                timeout_seconds=args.timeout_seconds, layer="candidate-sql",
                equivalence_token=args.equivalence_token,
            )
            authoritative_meta = response_metadata(authoritative, "authoritative", probe["name"])
            candidate_meta = response_metadata(candidate, "materialized", probe["name"])
            if authoritative_meta["corpusFingerprint"] != candidate_meta["corpusFingerprint"]:
                raise EquivalenceError(f"{probe['name']} compared different corpus fingerprints")
            if build_id is None:
                build_id = str(candidate_meta["buildId"])
                fingerprint = str(candidate_meta["corpusFingerprint"])
            elif (candidate_meta["buildId"], candidate_meta["corpusFingerprint"]) != (build_id, fingerprint):
                raise EquivalenceError(f"{probe['name']} used a different immutable SQL build")
            authoritative_signature = result_signature(authoritative, f"{probe['name']} authoritative")
            candidate_signature = result_signature(candidate, f"{probe['name']} candidate SQL")
            if authoritative_signature != candidate_signature:
                raise EquivalenceError(
                    f"{probe['name']} differs: authoritative={authoritative_signature}; "
                    f"candidate={candidate_signature}"
                )
            evidence["probes"].append({
                "name": probe["name"],
                "request": probe.get("body"),
                "authoritativeDurationMilliseconds": authoritative_ms,
                "candidateSqlDurationMilliseconds": candidate_ms,
                **authoritative_signature,
            })
        evidence.update({
            "status": "passed",
            "buildId": build_id,
            "corpusFingerprint": fingerprint,
            "probeCount": len(evidence["probes"]),
        })
        exit_code = 0
    except (EquivalenceError, OSError, ValueError) as exc:
        evidence["error"] = str(exc)
    evidence["completedAtUtc"] = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    evidence["evidenceSha256"] = hashlib.sha256(
        canonical_json(evidence).encode("utf-8")
    ).hexdigest()
    evidence_root = args.evidence_root or (
        args.state_root.resolve() / "serving" / "equivalence" / (build_id or "failed") / args.family
    )
    evidence_path = evidence_root / f"{run_id}.json"
    atomic_evidence(evidence_path, evidence)
    evidence["evidencePath"] = str(evidence_path.resolve())
    return evidence, exit_code


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    default_state = Path(
        os.environ.get("BASEBALLO_STATE_ROOT")
        or Path(os.environ.get("LOCALAPPDATA", ".")) / "BaseballO" / "state"
    )
    parser.add_argument("--family", choices=sorted(FAMILIES), required=True)
    parser.add_argument("--base-url")
    parser.add_argument("--equivalence-token")
    parser.add_argument("--state-root", type=Path, default=default_state)
    parser.add_argument("--evidence-root", type=Path)
    parser.add_argument("--timeout-seconds", type=float, default=120.0)
    args = parser.parse_args()
    try:
        if bool(args.base_url) != bool(args.equivalence_token):
            raise EquivalenceError(
                "Externally managed proof requires both --base-url and --equivalence-token"
            )
        if args.base_url:
            evidence, exit_code = prove(args)
        else:
            with managed_explorer(args.state_root, args.timeout_seconds) as (base_url, token):
                args.base_url = base_url
                args.equivalence_token = token
                evidence, exit_code = prove(args)
        print(json.dumps(evidence, separators=(",", ":"), ensure_ascii=True))
        return exit_code
    except (EquivalenceError, OSError, ValueError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, separators=(",", ":")))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
