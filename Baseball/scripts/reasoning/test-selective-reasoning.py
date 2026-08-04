#!/usr/bin/env python3
"""Offline tests for bounded inference, contradictions, and CLIF translation."""

from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path

from rdflib import Graph, Namespace, RDF, URIRef


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = Path(__file__).with_name("selective_reasoner.py")
SPEC = importlib.util.spec_from_file_location("selective_reasoner", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load selective_reasoner.py")
REASONER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REASONER)
PROVER_PATH = Path(__file__).with_name("prove-selective-reasoning.py")
PROVER_SPEC = importlib.util.spec_from_file_location("prove_selective_reasoning", PROVER_PATH)
if PROVER_SPEC is None or PROVER_SPEC.loader is None:
    raise RuntimeError("Could not load prove-selective-reasoning.py")
PROVER = importlib.util.module_from_spec(PROVER_SPEC)
PROVER_SPEC.loader.exec_module(PROVER)

BASE = Namespace("https://baseballontology.org/")
DATA = Namespace("https://baseballontology.org/data/test/")
BFO = Namespace("http://purl.obolibrary.org/obo/")


def fixture() -> tuple[Graph, URIRef]:
    graph = Graph()
    pa = DATA.pa
    batter_act = DATA.batter_act
    pitch = DATA.pitch
    swing = DATA.swing
    contact = DATA.contact
    player = DATA.player
    interval = DATA.pitch_interval
    graph.add((pa, RDF.type, BASE.PlateAppearance))
    graph.add((pa, BFO.BFO_0000117, batter_act))
    graph.add((batter_act, BFO.BFO_0000132, pa))
    graph.add((swing, BFO.BFO_0000132, batter_act))
    graph.add((pitch, BFO.BFO_0000132, pa))
    graph.add((contact, BFO.BFO_0000132, pa))
    graph.add((pitch, BFO.BFO_0000063, swing))
    graph.add((swing, BFO.BFO_0000063, contact))
    graph.add((pitch, BFO.BFO_0000057, player))
    graph.add((pitch, BFO.BFO_0000199, interval))
    graph.add((pitch, RDF.type, BASE.PitchAct))
    graph.add((swing, RDF.type, BASE.SwingAct))
    graph.add((contact, RDF.type, BASE.BatBallContactProcess))
    graph.add((interval, RDF.type, BFO.BFO_0000038))
    # This second plate appearance must never enter the selected slice.
    graph.add((DATA.other_pa, RDF.type, BASE.PlateAppearance))
    graph.add((DATA.other_pitch, BFO.BFO_0000132, DATA.other_pa))
    graph.add((contact, BFO.BFO_0000063, DATA.other_pitch))
    return graph, pa


def run_profile(name: str, graph: Graph, anchor: URIRef) -> tuple[Graph, Graph, dict]:
    path = ROOT / "reasoning" / "profiles" / f"{name}.json"
    profile = REASONER.load_profile(path)
    asserted, selected = REASONER.extract_slice(graph, anchor, profile)
    assert DATA.other_pa not in selected and DATA.other_pitch not in selected
    assert len(selected) <= int(profile["budgets"]["maxNodes"])
    inferred, _, _ = REASONER.apply_rules(asserted, profile, {})
    return asserted, inferred, profile


def test_positive_and_negative() -> None:
    graph, anchor = fixture()
    asserted, inferred, _ = run_profile("event-order", graph, anchor)
    assert (DATA.pitch, BFO.BFO_0000063, DATA.contact) in inferred
    assert (DATA.swing, BFO.BFO_0000062, DATA.pitch) in inferred
    assert (DATA.contact, BFO.BFO_0000062, DATA.pitch) in inferred

    _, structure, _ = run_profile("event-structure", graph, anchor)
    assert (DATA.swing, BFO.BFO_0000132, DATA.pa) in structure
    assert (DATA.pa, BFO.BFO_0000117, DATA.swing) in structure

    _, participation, _ = run_profile("participation", graph, anchor)
    assert (DATA.player, BFO.BFO_0000056, DATA.pitch) in participation

    contradictory, anchor = fixture()
    contradictory.add((DATA.contact, BFO.BFO_0000063, DATA.pitch))
    path = ROOT / "reasoning" / "profiles" / "event-order.json"
    profile = REASONER.load_profile(path)
    asserted, _ = REASONER.extract_slice(contradictory, anchor, profile)
    try:
        REASONER.apply_rules(asserted, profile, {})
    except ValueError as error:
        assert "contradiction" in str(error).lower()
    else:
        raise AssertionError("A precedence cycle was not rejected")


def test_budget_and_determinism() -> None:
    graph, anchor = fixture()
    asserted, inferred, profile = run_profile("event-order", graph, anchor)
    slice_constrained = json.loads(json.dumps(profile))
    slice_constrained["budgets"]["maxNodes"] = 1
    try:
        REASONER.validate_slice_budgets(
            asserted,
            {value for value in asserted.all_nodes() if isinstance(value, URIRef)},
            slice_constrained,
        )
    except ValueError as error:
        assert "budget" in str(error).lower()
    else:
        raise AssertionError("A selected-node budget violation was accepted")

    constrained = json.loads(json.dumps(profile))
    constrained["budgets"]["maxInferredTriples"] = 1
    try:
        REASONER.apply_rules(asserted, constrained, {})
    except ValueError as error:
        assert "budget" in str(error).lower()
    else:
        raise AssertionError("An inferred-triple budget violation was accepted")

    with tempfile.TemporaryDirectory() as directory:
        first = Path(directory) / "first.nt"
        second = Path(directory) / "second.nt"
        REASONER.write_sorted_ntriples(first, inferred)
        REASONER.write_sorted_ntriples(second, reversed(list(inferred)))
        assert first.read_bytes() == second.read_bytes()


def test_clif_translation() -> None:
    graph, anchor = fixture()
    asserted, inferred, profile = run_profile("participation", graph, anchor)
    closure = Graph()
    for triple in asserted:
        closure.add(triple)
    for triple in inferred:
        closure.add(triple)
    with tempfile.TemporaryDirectory() as directory:
        build = Path(directory)
        clif = build / "clif"
        clif.mkdir()
        asserted_path = clif / "asserted-facts.cl"
        expected_path = clif / "expected-entailments.cl"
        asserted_stats = REASONER.emit_clif_facts(asserted, profile, asserted_path)
        expected_stats = REASONER.emit_clif_facts(
            inferred, profile, expected_path, context=closure
        )
        assert asserted_stats["factCount"] > 0
        assert expected_stats["factCount"] > 0
        assert "(has-participant " in asserted_path.read_text(encoding="utf-8")
        assert "(participates-in " in expected_path.read_text(encoding="utf-8")
        (build / "manifest.json").write_text(
            json.dumps(
                {
                    "profile": "participation",
                    "bfoCommit": "dd89f4a193038b66ef0e891d546c05a5b477f40f",
                    "rulesetSha256": "0" * 64,
                    "fullFirstOrderProofExecuted": False,
                }
            ),
            encoding="utf-8",
        )
        report = PROVER.prove(build)
        assert report["allObligationsProved"]
        assert report["provedCount"] == expected_stats["factCount"]


def validate_contracts() -> None:
    source_manifest = json.loads(
        (ROOT / "reasoning" / "bfo-clif-manifest.json").read_text(encoding="utf-8")
    )
    assert source_manifest["commit"] == "dd89f4a193038b66ef0e891d546c05a5b477f40f"
    entries = {entry["name"]: entry for entry in source_manifest["modules"]}
    assert len(entries) == 6
    for entry in entries.values():
        assert len(entry["sha256"]) == 64 and int(entry["bytes"]) > 0
    for path in sorted((ROOT / "reasoning" / "profiles").glob("*.json")):
        profile = REASONER.load_profile(path)
        assert set(profile["clif"]["modules"]) <= set(entries)
        assert profile["anchorClass"] == str(BASE.PlateAppearance)


def main() -> None:
    validate_contracts()
    test_positive_and_negative()
    test_budget_and_determinism()
    test_clif_translation()
    print("Selective reasoning tests passed: 3 profiles, isolation, inference, contradiction, budgets, deterministic output, CLIF translation, and first-order proof.")


if __name__ == "__main__":
    main()
