#!/usr/bin/env python3
"""Focused positive and negative checks for the transactions SHACL profile."""

from __future__ import annotations

import argparse
from pathlib import Path

from pyshacl import validate
from rdflib import Graph, Namespace, RDF, URIRef


MODULE = Path(__file__).resolve().parents[1]
SHAPES = MODULE / "shacl" / "authoritative.ttl"
CCO = Namespace("https://www.commoncoreontologies.org/")
BFO = Namespace("http://purl.obolibrary.org/obo/")


def clone(graph: Graph) -> Graph:
    result = Graph()
    for triple in graph:
        result.add(triple)
    return result


def conforms(graph: Graph, shapes: Graph) -> bool:
    result, _, _ = validate(
        data_graph=graph,
        shacl_graph=shapes,
        inference="none",
        advanced=True,
        meta_shacl=True,
        abort_on_first=False,
    )
    return bool(result)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("data", type=Path)
    args = parser.parse_args()
    source = Graph().parse(args.data.resolve().as_uri(), format="turtle")
    shapes = Graph().parse(SHAPES.resolve().as_uri(), format="turtle")
    if not conforms(source, shapes):
        raise ValueError("unmodified one-record RDF does not conform")

    classification = next(source.subjects(RDF.type, CCO.ont00000293))
    row = source.value(classification, CCO.ont00001868)
    if row is None:
        raise ValueError("fixture RDF has no classified row")

    blocked_release = clone(source)
    blocked_release.add(
        (
            row,
            RDF.type,
            URIRef("https://baseballontology.org/BaseballPlayerReleaseAct"),
        )
    )

    persistent_entity = clone(source)
    person = next(
        value
        for value in persistent_entity.objects(row, CCO.ont00001808)
        if str(value).startswith("https://baseballontology.org/data/player/")
    )
    persistent_entity.add((person, RDF.type, CCO.ont00001262))

    missing_effective_date = clone(source)
    effective_date = next(
        value
        for value in missing_effective_date.objects(row, BFO.BFO_0000178)
        if str(value).endswith("/date/effectiveDate")
    )
    missing_effective_date.remove((row, BFO.BFO_0000178, effective_date))

    invented_boundary = clone(source)
    date_identifier = next(invented_boundary.objects(row, BFO.BFO_0000178))
    invented_boundary.add(
        (
            URIRef(f"{row}/process/unsupported"),
            BFO.BFO_0000066,
            date_identifier,
        )
    )

    mutations = {
        "ungrounded release type": blocked_release,
        "persistent Person assertion": persistent_entity,
        "missing effectiveDate output": missing_effective_date,
        "invented process/date boundary": invented_boundary,
    }
    for label, graph in mutations.items():
        rejected = not conforms(graph, shapes)
        print(f"{label}: rejected={str(rejected).lower()}")
        if not rejected:
            raise ValueError(f"SHACL failed to reject {label}")

    print(f"Transactions SHACL proof: base triples={len(source)}; mutations=4")


if __name__ == "__main__":
    main()
