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
ADMISSION_PATH = ROOT / "reasoning" / "profile-admission-tests.json"

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


def test_profile_admission_contract() -> None:
    contract = json.loads(ADMISSION_PATH.read_text(encoding="utf-8"))
    assert contract["artifactType"] == "baseball-selective-reasoning-profile-admission-tests"
    assert contract["contractVersion"] == 1
    profile_ids = {path.stem for path in (ROOT / "reasoning" / "profiles").glob("*.json")}
    assert set(contract["profiles"]) == profile_ids
    terms = {name: URIRef(value) for name, value in contract["terms"].items()}

    def resolve(value: str) -> URIRef:
        return terms[value] if value in terms else URIRef(value)

    def triple(values: list[str]) -> tuple[URIRef, URIRef, URIRef]:
        subject, predicate, object_ = values
        return resolve(subject), URIRef(predicate), resolve(object_)

    for profile_id, admission in contract["profiles"].items():
        assert admission["semanticFamily"]
        assert admission["positiveEntailments"]
        assert admission["forbiddenEntailments"]
        graph, anchor = fixture()
        asserted, inferred, profile = run_profile(profile_id, graph, anchor)
        closure = Graph()
        for value in asserted:
            closure.add(value)
        for value in inferred:
            closure.add(value)
        for expected in admission["positiveEntailments"]:
            assert triple(expected) in inferred, f"Missing positive admission entailment: {profile_id} / {expected}"
        for forbidden in admission["forbiddenEntailments"]:
            assert triple(forbidden) not in closure, f"Forbidden admission entailment: {profile_id} / {forbidden}"

        additions = admission["contradictionAdditions"]
        if additions:
            contradictory, contradiction_anchor = fixture()
            for addition in additions:
                contradictory.add(triple(addition))
            contradiction_slice, _ = REASONER.extract_slice(contradictory, contradiction_anchor, profile)
            try:
                REASONER.apply_rules(contradiction_slice, profile, {})
            except ValueError as error:
                assert "contradiction" in str(error).lower()
            else:
                raise AssertionError(f"Declared contradiction was not rejected: {profile_id}")
        else:
            assert not profile.get("constraints")
            assert str(admission["contradictionPolicy"]).startswith("not-applicable:")


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
    test_profile_admission_contract()
    test_budget_and_determinism()
    test_clif_translation()
    print("Selective reasoning tests passed: 3 profile admission contracts, isolation, positive and forbidden entailments, applicable contradictions, budgets, deterministic output, CLIF translation, and first-order proof.")


if __name__ == "__main__":
    main()
