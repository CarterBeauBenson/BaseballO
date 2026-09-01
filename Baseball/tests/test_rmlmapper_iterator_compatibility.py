#!/usr/bin/env python3
"""Execute the MLB-game JSONPath and Triples Map surface in production RMLMapper."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from rdflib import Graph, Literal, RDF, URIRef


ROOT = Path(__file__).resolve().parents[1]
RML = "http://semweb.mmlab.be/ns/rml#"
RR = "http://www.w3.org/ns/r2rml#"


def local_root() -> Path:
    configured = os.environ.get("BASEBALLO_LOCAL_ROOT")
    if configured:
        return Path(configured).resolve()
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise RuntimeError("LOCALAPPDATA is unavailable")
    return Path(local_app_data) / "BaseballO"


def installed_tools() -> tuple[Path, Path]:
    runtimes = local_root() / "runtimes"
    java_candidates = sorted(runtimes.glob("*/bin/java.exe"))
    mapper_candidates = sorted(runtimes.glob("*/rmlmapper-*.jar"))
    if len(java_candidates) != 1:
        raise RuntimeError(f"Expected one installed Java runtime; found {java_candidates}")
    if len(mapper_candidates) != 1:
        raise RuntimeError(f"Expected one installed RMLMapper; found {mapper_candidates}")
    return java_candidates[0], mapper_candidates[0]


def mapping_for(iterators: list[str]) -> str:
    declarations: list[str] = [
        "@base <https://baseballontology.org/mapping/iterator-proof/> .",
        "@prefix rml: <http://semweb.mmlab.be/ns/rml#> .",
        "@prefix ql: <http://semweb.mmlab.be/ns/ql#> .",
        "@prefix rr: <http://www.w3.org/ns/r2rml#> .",
        "",
    ]
    for position, iterator in enumerate(iterators):
        encoded = json.dumps(iterator, ensure_ascii=False)
        declarations.extend(
            [
                f"<#Source{position}> a rml:LogicalSource ;",
                '  rml:source "game-context.json" ;',
                "  rml:referenceFormulation ql:JSONPath ;",
                f"  rml:iterator {encoded} .",
                "",
                f"<#Map{position}> a rr:TriplesMap ;",
                f"  rml:logicalSource <#Source{position}> ;",
                f"  rr:subjectMap [ rr:constant <https://example.org/rml-proof/{position}> ; rr:termType rr:IRI ] ;",
                '  rr:predicateObjectMap [ rr:predicate <https://example.org/proof> ; rr:objectMap [ rr:constant "proof" ] ] .',
                "",
            ]
        )
    return "\n".join(declarations)


def execute_file(java: Path, mapper: Path, workspace: Path, mapping: Path) -> bool:
    output = workspace / "mapping-proof.ttl"
    result = subprocess.run(
        [
            str(java),
            "-Xmx512m",
            "-jar",
            str(mapper),
            "-m",
            str(mapping),
            "-o",
            str(output),
            "-s",
            "turtle",
            "-b",
            "https://baseballontology.org/mapping/iterator-proof",
            "--strict",
        ],
        cwd=workspace,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.returncode == 0


def execute(java: Path, mapper: Path, workspace: Path, iterators: list[str]) -> bool:
    mapping = workspace / "iterator-proof.rml.ttl"
    mapping.write_text(mapping_for(iterators), encoding="utf-8")
    return execute_file(java, mapper, workspace, mapping)


def failing_iterators(
    java: Path, mapper: Path, workspace: Path, iterators: list[str]
) -> list[str]:
    if not iterators or execute(java, mapper, workspace, iterators):
        return []
    if len(iterators) == 1:
        return iterators
    midpoint = len(iterators) // 2
    return failing_iterators(java, mapper, workspace, iterators[:midpoint]) + failing_iterators(
        java, mapper, workspace, iterators[midpoint:]
    )


def materialized_subset(graph: Graph, triples_maps: list[URIRef], workspace: Path) -> Path:
    subset = Graph()
    for prefix, namespace in graph.namespaces():
        subset.bind(prefix, namespace)
    logical_source = URIRef(RML + "logicalSource")
    for triples_map in triples_maps:
        for triple in graph.cbd(triples_map):
            subset.add(triple)
        for source in graph.objects(triples_map, logical_source):
            for triple in graph.cbd(source):
                subset.add(triple)
    text = subset.serialize(format="turtle")
    document = json.loads((workspace / "game.json").read_text(encoding="utf-8"))
    home_plate_umpire = next(
        official
        for official in document["liveData"]["boxscore"]["officials"]
        if official["officialType"] == "Home Plate"
    )
    replacements = {
        "{$.gamePk}": str(document["gamePk"]),
        "{$.gameData.venue.id}": str(document["gameData"]["venue"]["id"]),
        "{$.gameData.teams.away.id}": str(document["gameData"]["teams"]["away"]["id"]),
        "{$.gameData.teams.home.id}": str(document["gameData"]["teams"]["home"]["id"]),
        "{$.gameData.officialScorer.id}": str(document["gameData"]["officialScorer"]["id"]),
        "{$.homePlateUmpire.id}": str(home_plate_umpire["official"]["id"]),
    }
    for reference, value in replacements.items():
        text = text.replace(reference, value)
    mapping = workspace / "triples-map-proof.rml.ttl"
    mapping.write_text(text, encoding="utf-8")
    return mapping


def failing_triples_maps(
    java: Path,
    mapper: Path,
    workspace: Path,
    graph: Graph,
    triples_maps: list[URIRef],
) -> list[URIRef]:
    mapping = materialized_subset(graph, triples_maps, workspace)
    if not triples_maps or execute_file(java, mapper, workspace, mapping):
        return []
    if len(triples_maps) == 1:
        return triples_maps
    midpoint = len(triples_maps) // 2
    return failing_triples_maps(
        java, mapper, workspace, graph, triples_maps[:midpoint]
    ) + failing_triples_maps(java, mapper, workspace, graph, triples_maps[midpoint:])


def main() -> None:
    mapping_path = ROOT / "sources" / "mlb-game" / "mapping" / "mlb-game.rml.ttl"
    source_path = ROOT / "data" / "raw" / "game-566279.json"
    context_builder = ROOT / "scripts" / "pipeline" / "prepare-rml-context.py"
    graph = Graph().parse(mapping_path, format="turtle")
    iterator_predicate = URIRef(RML + "iterator")
    iterators = sorted(
        {
            str(value)
            for value in graph.objects(None, iterator_predicate)
            if isinstance(value, Literal)
        }
    )
    java, mapper = installed_tools()
    with tempfile.TemporaryDirectory(prefix="baseballo-rmlmapper-proof-") as temporary:
        workspace = Path(temporary)
        shutil.copy2(source_path, workspace / "game.json")
        subprocess.run(
            [sys.executable, str(context_builder), "game.json", "game-context.json"],
            cwd=workspace,
            check=True,
        )
        failures = failing_iterators(java, mapper, workspace, iterators)
        triples_maps = sorted(
            {
                subject
                for subject in graph.subjects(RDF.type, URIRef(RR + "TriplesMap"))
                if isinstance(subject, URIRef)
            },
            key=str,
        )
        map_failures = failing_triples_maps(
            java, mapper, workspace, graph, triples_maps
        )
    if failures:
        raise SystemExit(
            "RMLMapper rejected these MLB-game JSONPath iterators:\n- "
            + "\n- ".join(failures)
        )
    if map_failures:
        raise SystemExit(
            "RMLMapper rejected these MLB-game Triples Maps:\n- "
            + "\n- ".join(map(str, map_failures))
        )
    print(
        f"RMLMapper accepted {len(iterators)} unique MLB-game JSONPath iterators "
        f"and executed {len(triples_maps)} Triples Maps."
    )


if __name__ == "__main__":
    main()
