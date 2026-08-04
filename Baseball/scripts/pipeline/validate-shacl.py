#!/usr/bin/env python3
"""Validate a BaseballO RDF graph against a pinned SHACL profile."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pyshacl import validate
from rdflib import Graph, Namespace, RDF


ROOT = Path(__file__).resolve().parents[2]
SH = Namespace("http://www.w3.org/ns/shacl#")
PROFILES = {
    "authoritative": ROOT / "shacl" / "authoritative.ttl",
    "query-index": ROOT / "shacl" / "query-index.ttl",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=sorted(PROFILES), required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--report-json", type=Path)
    parser.add_argument("--meta-shacl", action="store_true")
    return parser.parse_args()


def term_text(value) -> str | None:
    return None if value is None else str(value)


def main() -> None:
    args = parse_args()
    data_path = args.data.resolve()
    if not data_path.is_file():
        raise ValueError(f"SHACL data graph does not exist: {data_path}")
    shape_path = PROFILES[args.profile].resolve()

    data_graph = Graph().parse(data_path)
    shape_graph = Graph().parse(shape_path, format="turtle")
    conforms, report_graph, report_text = validate(
        data_graph=data_graph,
        shacl_graph=shape_graph,
        inference="none",
        advanced=True,
        meta_shacl=args.meta_shacl,
        allow_infos=True,
        allow_warnings=True,
        abort_on_first=False,
    )

    if not isinstance(report_graph, Graph):
        print(report_text)
        raise SystemExit(2)

    results = []
    for result in report_graph.subjects(RDF.type, SH.ValidationResult):
        results.append(
            {
                "severity": term_text(report_graph.value(result, SH.resultSeverity)),
                "focusNode": term_text(report_graph.value(result, SH.focusNode)),
                "path": term_text(report_graph.value(result, SH.resultPath)),
                "sourceShape": term_text(report_graph.value(result, SH.sourceShape)),
                "message": term_text(report_graph.value(result, SH.resultMessage)),
            }
        )
    results.sort(
        key=lambda item: tuple(item.get(key) or "" for key in ("severity", "focusNode", "path", "message"))
    )

    report = {
        "artifactType": "baseball-shacl-validation",
        "profile": args.profile,
        "dataPath": str(data_path),
        "shapePath": str(shape_path),
        "dataTripleCount": len(data_graph),
        "shapeTripleCount": len(shape_graph),
        "conforms": bool(conforms),
        "resultCount": len(results),
        "results": results,
    }
    if args.report_json:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    print(
        f"SHACL profile {args.profile}: conforms={str(bool(conforms)).lower()}; "
        f"data triples={len(data_graph)}; results={len(results)}"
    )
    if not conforms:
        print(report_text)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
