#!/usr/bin/env python3
"""Regenerate the bounded PA-0 selective-reasoning proof baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PROFILES = ("event-order", "event-structure", "participation")
GAME_PK = "566279"
ANCHOR = "https://baseballontology.org/data/game/566279/plate-appearance/0"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def default_local_root() -> Path:
    configured = os.environ.get("BASEBALLO_LOCAL_ROOT")
    if configured:
        return Path(configured)
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise ValueError("Set BASEBALLO_LOCAL_ROOT or LOCALAPPDATA")
    return Path(local_app_data) / "BaseballO"


def run(command: list[str], timeout: int = 120) -> None:
    subprocess.run(command, cwd=ROOT, check=True, timeout=timeout)


def generate(args: argparse.Namespace) -> dict[str, Any]:
    source_rdf = args.source_rdf.resolve()
    clif_root = args.clif_root.resolve()
    work_root = args.work_root.resolve()
    if not source_rdf.is_file():
        raise ValueError(f"Fixture RDF is missing: {source_rdf}")
    if not clif_root.is_dir():
        raise ValueError(f"Pinned BFO CLIF cache is missing: {clif_root}")

    reasoner = ROOT / "scripts" / "reasoning" / "selective_reasoner.py"
    prover = ROOT / "scripts" / "reasoning" / "prove-selective-reasoning.py"
    shacl_validator = ROOT / "scripts" / "pipeline" / "validate-shacl.py"
    work_root.mkdir(parents=True, exist_ok=True)
    run([
        sys.executable, str(shacl_validator), "--profile", "authoritative",
        "--data", str(source_rdf), "--report-json", str(work_root / "pre-reasoning-shacl.json"),
    ])

    profile_results: list[dict[str, Any]] = []
    for profile in PROFILES:
        build = work_root / profile
        run([
            sys.executable, str(reasoner), "--input", str(source_rdf),
            "--game-pk", GAME_PK, "--anchor", ANCHOR,
            "--profile", str(ROOT / "reasoning" / "profiles" / f"{profile}.json"),
            "--clif-root", str(clif_root), "--output", str(build),
        ])
        run([sys.executable, str(prover), "--build", str(build)])
        post_report = build / "post-reasoning-shacl.json"
        run([
            sys.executable, str(shacl_validator), "--profile", "reasoning-output",
            "--data", str(build / "published.nt"), "--report-json", str(post_report),
        ])
        if load_json(post_report).get("conforms") is not True:
            raise ValueError(f"Reasoning-output SHACL failed for {profile}")
        manifest = load_json(build / "manifest.json")
        proof_path = build / "clif" / "proof-report.json"
        proof = load_json(proof_path)
        if proof.get("allObligationsProved") is not True or proof.get("consistency") != "sat":
            raise ValueError(f"Selective proof failed for {profile}")
        profile_results.append({
            "profile": profile,
            "reasoningGraph": manifest["reasoningGraph"],
            "rulesetSha256": manifest["rulesetSha256"],
            "profileSha256": manifest["profileSha256"],
            "proofReportSha256": sha256_file(proof_path),
            "assertedRelevantFactCount": proof["assertedRelevantFactCount"],
            "obligationCount": proof["obligationCount"],
            "provedCount": proof["provedCount"],
            "consistency": proof["consistency"],
            "durationMs": proof["durationMs"],
        })

    first_proof = load_json(work_root / PROFILES[0] / "clif" / "proof-report.json")
    total_obligations = sum(int(item["obligationCount"]) for item in profile_results)
    total_proved = sum(int(item["provedCount"]) for item in profile_results)
    return {
        "artifactType": "baseball-selective-reasoning-proof-baseline",
        "contractVersion": 1,
        "gamePk": GAME_PK,
        "anchor": ANCHOR,
        "sourceRdfSha256": sha256_file(source_rdf),
        "bfoCommit": first_proof["bfoCommit"],
        "backend": first_proof["backend"],
        "backendVersion": first_proof["backendVersion"],
        "backendScriptSha256": first_proof["backendScriptSha256"],
        "scope": "Selected CLIF axiom projections only; not arbitrary CLIF or the complete BFO theory.",
        "totalObligations": total_obligations,
        "totalProved": total_proved,
        "allProfilesConsistent": all(item["consistency"] == "sat" for item in profile_results),
        "profiles": profile_results,
    }


def parse_args() -> argparse.Namespace:
    local_root = default_local_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-rdf", type=Path,
        default=local_root / "state" / "pipeline" / "rdf" / "game-566279.ttl",
    )
    parser.add_argument(
        "--clif-root", type=Path,
        default=local_root / "runtimes" / "bfo-clif-dd89f4a",
    )
    parser.add_argument(
        "--work-root", type=Path,
        default=local_root / "state" / "reasoning" / "fixture-baseline",
    )
    parser.add_argument(
        "--output", type=Path,
        default=ROOT / "reasoning" / "evidence" / "fixture-566279-pa-0.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = generate(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        f"Fixture proof baseline: {report['totalProved']}/{report['totalObligations']} "
        f"obligations proved across {len(report['profiles'])} profiles"
    )
    print(f"Evidence: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
