#!/usr/bin/env python3
"""Prove every translated entailment in one bounded CLIF package with Z3."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path

import z3


ROOT = Path(__file__).resolve().parents[2]
ATOM = re.compile(r"^\s*\(([a-z][a-z0-9-]*)\s+(bb_[0-9a-f]{16}(?:\s+bb_[0-9a-f]{16})+)\)\s*$")
PROFILE_PREDICATES = {
    "event-order": {"precedes": 2, "preceded-by": 2},
    "event-structure": {"occurrent-part-of": 2, "has-occurrent-part": 2},
    "participation": {"participates-in": 3, "has-participant": 3},
}
MAX_OBLIGATIONS = 200
MAX_TOTAL_SECONDS = 30
SOLVER_TIMEOUT_MS = 5_000


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_atoms(path: Path, allowed: dict[str, int]) -> list[tuple[str, tuple[str, ...]]]:
    atoms = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = ATOM.match(line)
        if not match or match.group(1) not in allowed:
            continue
        arguments = tuple(match.group(2).split())
        if len(arguments) != allowed[match.group(1)]:
            raise ValueError(f"Unexpected arity in {path.name}: {line.strip()}")
        atoms.append((match.group(1), arguments))
    return sorted(set(atoms))


def make_problem(profile_id: str, asserted, expected):
    allowed = PROFILE_PREDICATES[profile_id]
    entity = z3.DeclareSort("BaseballEntity")
    names = sorted({name for _, args in asserted + expected for name in args})
    constants = {name: z3.Const(name, entity) for name in names}
    predicates = {
        name: z3.Function(name.replace("-", "_"), *([entity] * arity), z3.BoolSort())
        for name, arity in allowed.items()
    }

    def atom(value):
        predicate, arguments = value
        return predicates[predicate](*(constants[name] for name in arguments))

    a, b, c, t = z3.Consts("a b c t", entity)
    if profile_id == "event-order":
        precedes = predicates["precedes"]
        preceded_by = predicates["preceded-by"]
        axioms = [
            z3.ForAll([a, b], precedes(a, b) == preceded_by(b, a)),
            z3.ForAll([a, b, c], z3.Implies(z3.And(precedes(a, b), precedes(b, c)), precedes(a, c))),
            z3.ForAll([a, b], z3.Implies(precedes(a, b), z3.Not(precedes(b, a)))),
        ]
    elif profile_id == "event-structure":
        part_of = predicates["occurrent-part-of"]
        has_part = predicates["has-occurrent-part"]
        axioms = [
            z3.ForAll([a, b], part_of(a, b) == has_part(b, a)),
            z3.ForAll([a, b, c], z3.Implies(z3.And(part_of(a, b), part_of(b, c)), part_of(a, c))),
            z3.ForAll([a, b], z3.Implies(z3.And(part_of(a, b), part_of(b, a)), a == b)),
        ]
    else:
        participates = predicates["participates-in"]
        has_participant = predicates["has-participant"]
        axioms = [
            z3.ForAll([t, a, b], participates(a, b, t) == has_participant(b, a, t))
        ]
    return axioms, [atom(value) for value in asserted], [(value, atom(value)) for value in expected]


def prove(build: Path) -> dict:
    manifest_path = build / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    profile_id = str(manifest["profile"])
    allowed = PROFILE_PREDICATES[profile_id]
    asserted_path = build / "clif" / "asserted-facts.cl"
    expected_path = build / "clif" / "expected-entailments.cl"
    asserted = parse_atoms(asserted_path, allowed)
    expected = parse_atoms(expected_path, allowed)
    if not expected:
        raise ValueError("CLIF package contains no translatable proof obligations")
    if len(expected) > MAX_OBLIGATIONS:
        raise ValueError(f"Proof obligation budget exceeded: {len(expected)} > {MAX_OBLIGATIONS}")
    z3.set_param(proof=True)
    axioms, assertions, obligations = make_problem(profile_id, asserted, expected)
    solver = z3.Solver()
    solver.set(timeout=SOLVER_TIMEOUT_MS)
    solver.add(*(axioms + assertions))
    started = time.perf_counter()
    consistency = str(solver.check())
    if consistency != "sat":
        raise ValueError(f"Asserted CLIF slice is not consistent: {consistency}")
    results = []
    for source_atom, expression in obligations:
        if time.perf_counter() - started > MAX_TOTAL_SECONDS:
            raise ValueError(f"Proof wall-time budget exceeded: {MAX_TOTAL_SECONDS} seconds")
        obligation_started = time.perf_counter()
        solver.push()
        solver.add(z3.Not(expression))
        result = solver.check()
        proof_hash = None
        if result == z3.unsat:
            proof_hash = hashlib.sha256(str(solver.proof()).encode("utf-8")).hexdigest()
        solver.pop()
        results.append(
            {
                "atom": f"({source_atom[0]} {' '.join(source_atom[1])})",
                "result": "proved" if result == z3.unsat else str(result),
                "proofSha256": proof_hash,
                "durationMs": round((time.perf_counter() - obligation_started) * 1000, 3),
            }
        )
    proved = sum(result["result"] == "proved" for result in results)
    report = {
        "artifactType": "baseball-selective-first-order-proof",
        "contractVersion": 1,
        "profile": profile_id,
        "backend": "z3-solver",
        "backendVersion": z3.get_version_string(),
        "backendLicense": "MIT",
        "backendScriptSha256": sha256_file(Path(__file__).resolve()),
        "bfoCommit": manifest["bfoCommit"],
        "rulesetSha256": manifest["rulesetSha256"],
        "assertedClifSha256": sha256_file(asserted_path),
        "expectedClifSha256": sha256_file(expected_path),
        "assertedRelevantFactCount": len(asserted),
        "obligationCount": len(results),
        "provedCount": proved,
        "consistency": consistency,
        "allObligationsProved": proved == len(results),
        "durationMs": round((time.perf_counter() - started) * 1000, 3),
        "budgets": {
            "maxObligations": MAX_OBLIGATIONS,
            "maxTotalSeconds": MAX_TOTAL_SECONDS,
            "solverTimeoutMs": SOLVER_TIMEOUT_MS,
        },
        "scope": "Selected CLIF axiom projection only; not arbitrary CLIF or the complete BFO theory.",
        "obligations": results,
    }
    if not report["allObligationsProved"]:
        raise ValueError(f"Only {proved} of {len(results)} CLIF obligations were proved")
    report_path = build / "clif" / "proof-report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest["selectiveFirstOrderProofExecuted"] = True
    manifest["selectiveFirstOrderProof"] = {
        "path": "clif/proof-report.json",
        "sha256": sha256_file(report_path),
        "backend": "z3-solver",
        "backendVersion": z3.get_version_string(),
        "provedCount": proved,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", type=Path, required=True)
    args = parser.parse_args()
    report = prove(args.build.resolve())
    print(
        f"Selective first-order proof passed: {report['provedCount']}/"
        f"{report['obligationCount']} obligations; consistency={report['consistency']}; "
        f"Z3 {report['backendVersion']}"
    )


if __name__ == "__main__":
    main()
