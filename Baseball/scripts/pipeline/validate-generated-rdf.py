#!/usr/bin/env python3
"""Validate one generated BaseballO game graph without modifying the ontology."""

from __future__ import annotations

import argparse
from pathlib import Path

from rdflib import Graph, Namespace, RDF, URIRef


BASE = Namespace("https://baseballontology.org/")
DATA = Namespace("https://baseballontology.org/data/")
BFO = Namespace("http://purl.obolibrary.org/obo/")
CCO = Namespace("https://www.commoncoreontologies.org/")


def require_typed_link(
    graph: Graph,
    subjects: set[URIRef],
    predicate: URIRef,
    object_classes: tuple[URIRef, ...],
    label: str,
) -> None:
    missing = []
    for subject in subjects:
        objects = set(graph.objects(subject, predicate))
        if not any(
            (object_, RDF.type, object_class) in graph
            for object_ in objects
            for object_class in object_classes
        ):
            missing.append(subject)
    if missing:
        raise ValueError(
            f"{label}: {len(missing)} subject(s) lack the required typed link; "
            f"examples: {', '.join(map(str, missing[:5]))}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("rdf_file", type=Path)
    parser.add_argument("game_pk")
    parser.add_argument("--expected-plate-appearances", type=int)
    parser.add_argument("--expected-batter-acts", type=int)
    parser.add_argument("--expected-pitches", type=int)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    graph = Graph()
    graph.parse(args.rdf_file, format="turtle")
    if not graph:
        raise ValueError("Generated RDF graph is empty")

    game = URIRef(f"{DATA}game/{args.game_pk}")
    if (game, RDF.type, BASE.BaseballGame) not in graph:
        raise ValueError(f"Expected BaseballGame assertion is missing for {game}")

    plate_appearances = len(set(graph.subjects(RDF.type, BASE.PlateAppearance)))
    batter_acts = len(set(graph.subjects(RDF.type, BASE.BatterAct)))
    pitches = len(set(graph.subjects(RDF.type, BASE.PitchAct)))
    if (
        args.expected_plate_appearances is not None
        and plate_appearances != args.expected_plate_appearances
    ):
        raise ValueError(
            "PlateAppearance count does not match the source: "
            f"expected {args.expected_plate_appearances}, got {plate_appearances}"
        )
    if args.expected_batter_acts is not None and batter_acts != args.expected_batter_acts:
        raise ValueError(
            "BatterAct count does not match the source: "
            f"expected {args.expected_batter_acts}, got {batter_acts}"
        )
    if args.expected_pitches is not None and pitches != args.expected_pitches:
        raise ValueError(
            "PitchAct count does not match the source: "
            f"expected {args.expected_pitches}, got {pitches}"
        )

    pitch_subjects = set(graph.subjects(RDF.type, BASE.PitchAct))
    require_typed_link(
        graph,
        pitch_subjects,
        BFO.BFO_0000063,
        (BASE.PitchBallMotionProcess,),
        "PitchAct to PitchBallMotionProcess chain",
    )

    contact_subjects = set(graph.subjects(RDF.type, BASE.BatBallContactProcess))
    require_typed_link(
        graph,
        contact_subjects,
        BFO.BFO_0000063,
        (BASE.BattedBallMotionProcess,),
        "BatBallContactProcess to BattedBallMotionProcess chain",
    )
    missing_contact_acts = []
    for contact in contact_subjects:
        preceding = set(graph.subjects(BFO.BFO_0000063, contact))
        if not any(
            (act, RDF.type, act_class) in graph
            for act in preceding
            for act_class in (BASE.SwingAct, BASE.BuntAct)
        ):
            missing_contact_acts.append(contact)
    if missing_contact_acts:
        raise ValueError(
            "BatBallContactProcess lacks a preceding SwingAct or BuntAct: "
            + ", ".join(map(str, missing_contact_acts[:5]))
        )

    institutional_patterns = (
        (BASE.BallProcess, (BASE.BallJudgmentAct,)),
        (BASE.StrikeProcess, (BASE.StrikeJudgmentAct, BASE.FoulTipJudgmentAct)),
        (BASE.FairBallProcess, (BASE.FairBallJudgmentAct,)),
        (BASE.FoulBallProcess, (BASE.FoulBallJudgmentAct,)),
        (BASE.FoulTipProcess, (BASE.FoulTipJudgmentAct,)),
        (BASE.OutProcess, (BASE.OutJudgmentAct,)),
        (BASE.SafeProcess, (BASE.SafeJudgmentAct,)),
        (BASE.RunProcess, (BASE.RunJudgmentAct,)),
        (BASE.StolenBaseProcess, (BASE.StolenBaseJudgmentAct,)),
    )
    for process_class, judgment_classes in institutional_patterns:
        process_subjects = set(graph.subjects(RDF.type, process_class))
        require_typed_link(
            graph,
            process_subjects,
            BFO.BFO_0000117,
            judgment_classes,
            f"{process_class.split('/')[-1]} adjudication",
        )

    fair_subjects = set(graph.subjects(RDF.type, BASE.FairBallProcess))
    require_typed_link(
        graph,
        fair_subjects,
        BFO.BFO_0000063,
        (BASE.BaseballInstitutionalProcess,),
        "FairBallProcess to plate-appearance result chain",
    )

    plate_result_subjects = {
        subject
        for subject in graph.subjects(RDF.type, BASE.BaseballInstitutionalProcess)
        if str(subject).endswith("/result")
    }
    require_typed_link(
        graph,
        plate_result_subjects,
        BFO.BFO_0000117,
        (BASE.BaseballAdjudicationAct,),
        "Plate-appearance result adjudication",
    )

    for foul_tip in graph.subjects(RDF.type, BASE.FoulTipProcess):
        if (foul_tip, RDF.type, BASE.StrikeProcess) not in graph:
            raise ValueError(
                f"FoulTipProcess is not the same counted individual as StrikeProcess: {foul_tip}"
            )

    record_subjects = set(graph.subjects(RDF.type, BASE.BaseballEventRecord))
    process_or_act_subjects = {
        subject
        for class_ in (
            BASE.PitchAct,
            BASE.SwingAct,
            BASE.BuntAct,
            BASE.BaseballPhysicalProcess,
            BASE.BaseballInstitutionalProcess,
        )
        for subject in graph.subjects(RDF.type, class_)
    }
    collapsed_records = record_subjects & process_or_act_subjects
    if collapsed_records:
        raise ValueError(
            "BaseballEventRecord identity is collapsed with an act or process: "
            + ", ".join(map(str, list(collapsed_records)[:5]))
        )

    subjects = {subject for subject in graph.subjects()}
    predicates = {predicate for predicate in graph.predicates()}
    classes = {class_ for class_ in graph.objects(None, RDF.type)}
    print(f"Generated triples: {len(graph)}")
    print(f"Distinct subjects: {len(subjects)}")
    print(f"Distinct predicates: {len(predicates)}")
    print(f"Distinct asserted classes: {len(classes)}")
    print(f"Plate appearances: {plate_appearances}")
    print(f"Batter acts: {batter_acts}")
    print(f"Pitches: {pitches}")
    print(f"Pitch motions: {len(set(graph.subjects(RDF.type, BASE.PitchBallMotionProcess)))}")
    print(f"Bat-ball contacts: {len(contact_subjects)}")
    print(f"Plate-appearance results with adjudication: {len(plate_result_subjects)}")
    print(f"Expected game present: {game}")


if __name__ == "__main__":
    main()
