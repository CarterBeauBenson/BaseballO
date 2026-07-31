#!/usr/bin/env python3
"""Merge and validate query-index CONSTRUCT results deterministically."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from rdflib import Graph, Namespace, RDF, RDFS, URIRef
from rdflib.term import BNode


IDX = Namespace("https://w3id.org/baseball/query-index/")

REQUIRED_PROPERTIES = {
    IDX.GameFact: (IDX.season, IDX.venue, IDX.gameStart, IDX.derivedFrom),
    IDX.PlateAppearanceFact: (IDX.game, IDX.agent, IDX.result, IDX.derivedFrom),
    IDX.PlateAppearanceResultFact: (
        IDX.plateAppearance,
        IDX.game,
        IDX.agent,
        IDX.outcomeClass,
        IDX.sourceEventType,
        IDX.derivedFrom,
    ),
    IDX.HitFact: (
        IDX.agent,
        IDX.game,
        IDX.venue,
        IDX.hitType,
        IDX.plateAppearance,
        IDX.derivedFrom,
    ),
    IDX.PitchFact: (
        IDX.agent,
        IDX.game,
        IDX.venue,
        IDX.plateAppearance,
        IDX.derivedFrom,
    ),
    IDX.PitchCallFact: (
        IDX.pitch,
        IDX.agent,
        IDX.game,
        IDX.callType,
        IDX.derivedFrom,
    ),
    IDX.BattingActFact: (
        IDX.agent,
        IDX.game,
        IDX.plateAppearance,
        IDX.battingActType,
        IDX.derivedFrom,
    ),
    IDX.ContactFact: (
        IDX.agent,
        IDX.game,
        IDX.venue,
        IDX.plateAppearance,
        IDX.battedBall,
        IDX.derivedFrom,
    ),
    IDX.RunnerResolutionFact: (
        IDX.agent,
        IDX.game,
        IDX.resolutionClass,
        IDX.sourceEventType,
        IDX.derivedFrom,
    ),
    IDX.StolenBaseFact: (IDX.agent, IDX.game, IDX.derivedFrom),
    IDX.AssignmentFact: (
        IDX.game,
        IDX.assignee,
        IDX.assignmentType,
        IDX.derivedFrom,
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stats", type=Path, required=True)
    parser.add_argument("--game-pk", required=True)
    parser.add_argument("--source-graph", required=True)
    parser.add_argument("--index-resource", required=True)
    return parser.parse_args()


def require_values(graph: Graph, subject: URIRef, predicates: tuple[URIRef, ...]) -> None:
    for predicate in predicates:
        if not any(graph.objects(subject, predicate)):
            raise ValueError(f"{subject} has no required {predicate} value")


def main() -> None:
    args = parse_args()
    if not args.game_pk.isdigit():
        raise ValueError("game-pk must contain only digits")

    graph = Graph()
    component_files = sorted(args.inputs.glob("*.ttl"))
    if not component_files:
        raise ValueError(f"No component Turtle files found in {args.inputs}")
    for component_file in component_files:
        graph.parse(component_file, format="turtle")

    if any(isinstance(term, BNode) for triple in graph for term in triple):
        raise ValueError("The query index must not contain blank nodes")

    allowed_predicates = {RDF.type, RDFS.label}
    unexpected = sorted(
        {predicate for _, predicate, _ in graph if predicate not in allowed_predicates and not str(predicate).startswith(str(IDX))},
        key=str,
    )
    if unexpected:
        raise ValueError(f"Unexpected non-index predicates: {', '.join(map(str, unexpected))}")

    index_resource = URIRef(args.index_resource)
    game = URIRef(f"https://baseballontology.org/data/game/{args.game_pk}")
    source_graph = URIRef(args.source_graph)
    if (index_resource, RDF.type, IDX.QueryIndex) not in graph:
        raise ValueError("QueryIndex metadata resource is missing")
    if (index_resource, IDX.sourceGraph, source_graph) not in graph:
        raise ValueError("QueryIndex metadata has the wrong source graph")
    if (index_resource, IDX.indexedGame, game) not in graph:
        raise ValueError("QueryIndex metadata has the wrong game")

    game_facts = set(graph.subjects(RDF.type, IDX.GameFact))
    if game_facts != {game}:
        raise ValueError(f"Expected exactly the indexed game as GameFact, got {len(game_facts)}")

    counts: Counter[str] = Counter()
    for fact_class, required_predicates in REQUIRED_PROPERTIES.items():
        subjects = set(graph.subjects(RDF.type, fact_class))
        counts[str(fact_class).removeprefix(str(IDX))] = len(subjects)
        for subject in subjects:
            require_values(graph, subject, required_predicates)
            if fact_class != IDX.GameFact and fact_class != IDX.AssignmentFact:
                if (subject, IDX.game, game) not in graph:
                    raise ValueError(f"{subject} is not assigned to the indexed game")

    lines = sorted(
        f"{subject.n3()} {predicate.n3()} {obj.n3()} ."
        for subject, predicate, obj in graph
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    stats = {
        "artifactType": "baseball-query-index-statistics",
        "gamePk": args.game_pk,
        "sourceGraph": args.source_graph,
        "indexResource": args.index_resource,
        "componentFiles": [path.name for path in component_files],
        "tripleCount": len(graph),
        "factCounts": dict(sorted(counts.items())),
    }
    args.stats.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Query-index triples: {len(graph)}")
    for name, count in sorted(counts.items()):
        print(f"{name}: {count}")


if __name__ == "__main__":
    main()
