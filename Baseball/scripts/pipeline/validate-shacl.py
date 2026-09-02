#!/usr/bin/env python3
"""Validate a BaseballO RDF graph against a pinned SHACL profile."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

from pyshacl import validate
from rdflib import Graph, Namespace, RDF


ROOT = Path(__file__).resolve().parents[2]
SH = Namespace("http://www.w3.org/ns/shacl#")
PROFILES = {
    "authoritative": ROOT / "sources" / "mlb-game" / "shacl" / "authoritative.ttl",
    "query-index": ROOT / "shacl" / "query-index.ttl",
    "reasoning-output": ROOT / "shacl" / "reasoning-output.ttl",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    shapes = parser.add_mutually_exclusive_group(required=True)
    shapes.add_argument("--profile", choices=sorted(PROFILES))
    shapes.add_argument(
        "--shape-file",
        type=Path,
        help="Explicit source-owned SHACL graph for a detachable source lane.",
    )
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--report-json", type=Path)
    parser.add_argument("--meta-shacl", action="store_true")
    parser.add_argument("--engine", choices=("pyshacl", "jena"), default="pyshacl")
    parser.add_argument("--java", type=Path)
    parser.add_argument("--jena-classpath", type=Path)
    parser.add_argument("--jena-max-heap", default="384m")
    return parser.parse_args()


def term_text(value) -> str | None:
    return None if value is None else str(value)


def validate_with_jena(
    *, data_path: Path, shape_path: Path, java: Path, classpath: Path, max_heap: str
) -> tuple[bool, Graph, str]:
    if not java.is_file():
        raise ValueError(f"Java executable does not exist: {java}")
    if not classpath.is_file():
        raise ValueError(f"Jena classpath does not exist: {classpath}")
    if not re.fullmatch(r"[1-9][0-9]*[mMgG]", max_heap):
        raise ValueError("Jena maximum heap must look like 384m or 1g")

    completed = subprocess.run(
        [
            str(java),
            "-Xms64m",
            f"-Xmx{max_heap}",
            "-cp",
            str(classpath),
            "shacl.shacl_validate",
            f"--shapes={shape_path.as_uri()}",
            f"--data={data_path.as_uri()}",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    standard_error = completed.stderr.decode("utf-8", errors="replace")
    if completed.returncode != 0:
        raise RuntimeError(
            f"Jena SHACL exited with status {completed.returncode}: {standard_error.strip()}"
        )
    report_graph = Graph()
    try:
        report_graph.parse(data=completed.stdout, format="turtle")
    except Exception as error:
        raise RuntimeError(
            "Jena SHACL did not return a Turtle validation report: "
            f"{standard_error.strip()}"
        ) from error
    conforms_value = next(report_graph.objects(None, SH.conforms), None)
    if conforms_value is None:
        raise RuntimeError("Jena SHACL report has no sh:conforms assertion")
    conforms = bool(conforms_value.toPython())
    report_text = completed.stdout.decode("utf-8", errors="replace")
    return conforms, report_graph, report_text


def main() -> None:
    args = parse_args()
    data_path = args.data.resolve()
    if not data_path.is_file():
        raise ValueError(f"SHACL data graph does not exist: {data_path}")
    shape_path = (
        args.shape_file.resolve()
        if args.shape_file is not None
        else PROFILES[args.profile].resolve()
    )
    if not shape_path.is_file():
        raise ValueError(f"SHACL shape graph does not exist: {shape_path}")

    data_graph = Graph().parse(data_path)
    shape_graph = Graph().parse(shape_path, format="turtle")
    if args.engine == "jena":
        if args.meta_shacl:
            raise ValueError("--meta-shacl is available only with the pyshacl engine")
        if args.java is None or args.jena_classpath is None:
            raise ValueError("Jena SHACL requires --java and --jena-classpath")
        conforms, report_graph, report_text = validate_with_jena(
            data_path=data_path,
            shape_path=shape_path,
            java=args.java.resolve(),
            classpath=args.jena_classpath.resolve(),
            max_heap=args.jena_max_heap,
        )
    else:
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
        "engine": args.engine,
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
        f"SHACL shapes {shape_path}: conforms={str(bool(conforms)).lower()}; "
        f"data triples={len(data_graph)}; results={len(results)}"
    )
    if not conforms:
        print(report_text)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
