#!/usr/bin/env python3
"""Compare bounded reasoning over reviewed simple and complicated plate appearances."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from rdflib import Graph, URIRef


ROOT = Path(__file__).resolve().parents[2]
PROFILES = ("event-order", "event-structure", "participation")
PREDICATES = {
    "event-order": (
        "http://purl.obolibrary.org/obo/BFO_0000063",
        "http://purl.obolibrary.org/obo/BFO_0000062",
    ),
    "event-structure": (
        "http://purl.obolibrary.org/obo/BFO_0000117",
        "http://purl.obolibrary.org/obo/BFO_0000132",
    ),
    "participation": (
        "http://purl.obolibrary.org/obo/BFO_0000057",
        "http://purl.obolibrary.org/obo/BFO_0000056",
    ),
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def default_local_root() -> Path:
    configured = os.environ.get("BASEBALLO_LOCAL_ROOT")
    if configured:
        return Path(configured)
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise ValueError("Set BASEBALLO_LOCAL_ROOT or LOCALAPPDATA")
    return Path(local_app_data) / "BaseballO"


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def canonical_rows(graph: Graph, predicates: tuple[str, ...]) -> list[str]:
    allowed = {URIRef(value) for value in predicates}
    return sorted(
        f"{subject.n3()}|{predicate.n3()}|{object_.n3()}"
        for subject, predicate, object_ in graph
        if predicate in allowed
    )


def row_summary(graph: Graph, predicates: tuple[str, ...]) -> dict[str, Any]:
    rows = canonical_rows(graph, predicates)
    return {
        "rowCount": len(rows),
        "rowSetSha256": hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest(),
        "predicateCounts": {
            predicate: sum(1 for _ in graph.triples((None, URIRef(predicate), None)))
            for predicate in predicates
        },
    }


def validate_sample(raw: dict[str, Any], sample: dict[str, Any]) -> None:
    plays = {int(play["about"]["atBatIndex"]): play for play in raw["liveData"]["plays"]["allPlays"]}
    index = int(sample["plateAppearanceIndex"])
    if index not in plays:
        raise ValueError(f"Reviewed plate appearance is missing: {index}")
    play = plays[index]
    observed = {
        "eventType": str(play["result"]["eventType"]),
        "playEventCount": len(play.get("playEvents", [])),
        "pitchCount": sum(1 for event in play.get("playEvents", []) if event.get("isPitch") is True),
        "runnerRecordCount": len(play.get("runners", [])),
        "description": str(play["result"]["description"]),
    }
    for key, value in observed.items():
        if sample.get(key) != value:
            raise ValueError(f"Reviewed sample {sample['id']} changed at {key}: {value!r}")


def evaluate(args: argparse.Namespace) -> dict[str, Any]:
    samples_contract = load_json(args.samples.resolve())
    if samples_contract.get("artifactType") != "baseball-selective-reasoning-reviewed-samples" or samples_contract.get("contractVersion") != 1:
        raise ValueError("Unsupported reviewed-sample contract")
    samples = list(samples_contract.get("samples", []))
    if {sample.get("complexity") for sample in samples} != {"simple", "complicated"}:
        raise ValueError("Reviewed samples must contain simple and complicated cases")
    source_json = args.source_json.resolve()
    source_rdf = args.source_rdf.resolve()
    clif_root = args.clif_root.resolve()
    raw = load_json(source_json)
    if str(raw.get("gamePk")) != "566279":
        raise ValueError("The reviewed sample currently targets fixture game 566279")
    for sample in samples:
        validate_sample(raw, sample)

    reasoner = ROOT / "scripts" / "reasoning" / "selective_reasoner.py"
    prover = ROOT / "scripts" / "reasoning" / "prove-selective-reasoning.py"
    shacl_validator = ROOT / "scripts" / "pipeline" / "validate-shacl.py"
    authoritative_shape = ROOT / "sources" / "mlb-game" / "shacl" / "authoritative.ttl"
    reasoning_shape = ROOT / "shacl" / "reasoning-output.ttl"
    results: list[dict[str, Any]] = []
    args.work_root.mkdir(parents=True, exist_ok=True)
    pre_report_path = args.work_root.resolve() / "pre-reasoning-shacl.json"
    subprocess.run(
        [sys.executable, str(shacl_validator), "--profile", "authoritative", "--data", str(source_rdf), "--report-json", str(pre_report_path)],
        cwd=ROOT, check=True, timeout=90,
    )
    pre_report = load_json(pre_report_path)
    if pre_report.get("conforms") is not True:
        raise ValueError("Reviewed source RDF did not pass authoritative SHACL before reasoning")
    for sample in samples:
        for profile in PROFILES:
            build = args.work_root.resolve() / str(sample["id"]) / profile
            command = [
                sys.executable, str(reasoner), "--input", str(source_rdf),
                "--game-pk", str(sample["gamePk"]), "--anchor", str(sample["anchor"]),
                "--profile", str(ROOT / "reasoning" / "profiles" / f"{profile}.json"),
                "--clif-root", str(clif_root), "--output", str(build),
            ]
            subprocess.run(command, cwd=ROOT, check=True, timeout=90)
            subprocess.run([sys.executable, str(prover), "--build", str(build)], cwd=ROOT, check=True, timeout=90)
            post_report_path = build / "post-reasoning-shacl.json"
            subprocess.run(
                [sys.executable, str(shacl_validator), "--profile", "reasoning-output", "--data", str(build / "published.nt"), "--report-json", str(post_report_path)],
                cwd=ROOT, check=True, timeout=90,
            )
            post_report = load_json(post_report_path)
            if post_report.get("conforms") is not True:
                raise ValueError(f"Reasoning-output SHACL failed for {sample['id']} / {profile}")
            manifest = load_json(build / "manifest.json")
            proof = load_json(build / "clif" / "proof-report.json")
            if proof.get("allObligationsProved") is not True or proof.get("consistency") != "sat":
                raise ValueError(f"Reasoning proof failed for {sample['id']} / {profile}")
            asserted = Graph().parse(build / "asserted-slice.nt", format="nt")
            closure = Graph().parse(build / "closure.nt", format="nt")
            asserted_query = row_summary(asserted, PREDICATES[profile])
            closure_query = row_summary(closure, PREDICATES[profile])
            results.append({
                "sample": sample["id"],
                "complexity": sample["complexity"],
                "anchor": sample["anchor"],
                "profile": profile,
                "rulesetSha256": manifest["rulesetSha256"],
                "profileSha256": manifest["profileSha256"],
                "counts": manifest["counts"],
                "inferredSha256": manifest["artifacts"]["inferred"]["sha256"],
                "queryComparison": {
                    "predicates": list(PREDICATES[profile]),
                    "asserted": asserted_query,
                    "closure": closure_query,
                    "newRows": closure_query["rowCount"] - asserted_query["rowCount"],
                },
                "proof": {
                    "backend": proof["backend"],
                    "backendVersion": proof["backendVersion"],
                    "consistency": proof["consistency"],
                    "obligationCount": proof["obligationCount"],
                    "provedCount": proof["provedCount"],
                    "allObligationsProved": proof["allObligationsProved"],
                },
                "shaclValidation": {
                    "explicitGraphBeforeReasoning": {
                        "profile": "authoritative",
                        "conforms": True,
                        "shapeSha256": sha256_file(authoritative_shape),
                    },
                    "inferredGraphBeforeLoad": {
                        "profile": "reasoning-output",
                        "conforms": True,
                        "shapeSha256": sha256_file(reasoning_shape),
                    },
                },
            })
    return {
        "artifactType": "baseball-selective-reasoning-reviewed-sample-evidence",
        "contractVersion": 1,
        "scope": "Two explicit plate appearances only; no full-game or corpus closure.",
        "sourceJson": source_json.relative_to(ROOT).as_posix(),
        "sourceJsonSha256": sha256_file(source_json),
        "sourceRdfSha256": sha256_file(source_rdf),
        "samplesContract": args.samples.resolve().relative_to(ROOT).as_posix(),
        "samplesContractSha256": sha256_file(args.samples.resolve()),
        "sampleCount": len(samples),
        "profileCount": len(PROFILES),
        "runCount": len(results),
        "allProfilesConsistent": all(result["proof"]["consistency"] == "sat" for result in results),
        "allObligationsProved": all(result["proof"]["allObligationsProved"] for result in results),
        "results": results,
    }


def parse_args() -> argparse.Namespace:
    local_root = default_local_root()
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=Path, default=ROOT / "reasoning" / "reviewed-samples.json")
    parser.add_argument("--source-json", type=Path, default=ROOT / "data" / "raw" / "game-566279.json")
    parser.add_argument("--source-rdf", type=Path, default=local_root / "state" / "pipeline" / "rdf" / "game-566279.ttl")
    parser.add_argument("--clif-root", type=Path, default=local_root / "runtimes" / "bfo-clif-dd89f4a")
    parser.add_argument("--work-root", type=Path, default=local_root / "state" / "reasoning" / "reviewed-samples")
    parser.add_argument("--output-report", type=Path, default=local_root / "state" / "reasoning" / "evidence" / "reviewed-samples.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = evaluate(args)
    args.output_report.parent.mkdir(parents=True, exist_ok=True)
    args.output_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Reviewed reasoning sample: {report['runCount']} runs; all proofs passed")
    print(f"Evidence: {args.output_report.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
