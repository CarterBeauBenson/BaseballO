#!/usr/bin/env python3
"""Validate one generated BaseballO game graph without modifying the ontology."""

from __future__ import annotations

import argparse
from pathlib import Path

from rdflib import Graph, Namespace, RDF, URIRef


BASE = Namespace("https://baseballontology.org/")
DATA = Namespace("https://baseballontology.org/data/")


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
    print(f"Expected game present: {game}")


if __name__ == "__main__":
    main()
