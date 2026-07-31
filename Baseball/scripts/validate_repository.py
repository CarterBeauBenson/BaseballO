#!/usr/bin/env python3
"""Validate repository structure and the active direct RML mapping."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

from rdflib import Graph
from rdflib.plugins.sparql import prepareQuery


ROOT = Path(__file__).resolve().parents[1]
ACTIVE_MAPPING = ROOT / "mappings" / "direct" / "mlb-direct.rml.ttl"
MAPPING_VALIDATOR = ROOT / "mappings" / "direct" / "validate_direct_mapping.py"
ONTOLOGY_OVERLAY_VALIDATOR = ROOT / "scripts" / "validate_ontology_overlay.py"
RML_MERMAID_GENERATOR = ROOT / "scripts" / "generate_rml_mermaid.py"
SAMPLE = ROOT / "data" / "raw" / "game-566279.json"
SPARQL_ROOT = ROOT / "sparql"
QUERY_BUILDERS = (
    ROOT / "web" / "query-builder" / "analytics-query-builder.js",
    ROOT / "web" / "query-builder" / "hit-query-builder.js",
)

REQUIRED_PATHS = (
    ROOT / "README.md",
    ROOT / "NEXT-PHASE.md",
    ROOT / "ontology" / "BaseballO.ttl",
    ROOT / "ontology" / "BaseballO-axioms-overlay.ttl",
    ACTIVE_MAPPING,
    ROOT / "mappings" / "policies" / "modeling-choices.yaml",
    ROOT / "mappings" / "policies" / "iri-policy.yaml",
    ROOT / "mermaid" / "README.md",
    ROOT / "mermaid" / "rml-mermaid-manifest.yaml",
    ROOT / "mermaid" / "patterns" / "README.md",
    ROOT / "infra" / "README.md",
    ROOT / "infra" / "fuseki" / "configuration" / "baseball-dev.ttl",
    ROOT / "infra" / "versions.psd1",
    ROOT / "scripts" / "infra" / "configure-nifi-foundation.ps1",
    ROOT / "scripts" / "infra" / "configure-nifi-rdf-skeleton.ps1",
    ROOT / "scripts" / "infra" / "configure-nifi-games-manual.ps1",
    ROOT / "scripts" / "infra" / "configure-nifi-games-daily.ps1",
    ROOT / "scripts" / "pipeline" / "import-game-json.ps1",
    ROOT / "scripts" / "pipeline" / "process-staged-game-json.ps1",
    ROOT / "scripts" / "pipeline" / "test-manual-vertical-slice.ps1",
    ROOT / "scripts" / "pipeline" / "run-rml.ps1",
    ROOT / "scripts" / "pipeline" / "prepare-rml-context.py",
    ROOT / "scripts" / "pipeline" / "acquire-daily-games.ps1",
    ROOT / "scripts" / "pipeline" / "load-game-graph.ps1",
    ROOT / "scripts" / "pipeline" / "validate-generated-rdf.py",
    ROOT / "scripts" / "pipeline" / "build-query-index.ps1",
    ROOT / "scripts" / "pipeline" / "compile-query-index.py",
    ROOT / "scripts" / "pipeline" / "query-index-common.ps1",
    ROOT / "scripts" / "pipeline" / "test-query-index.ps1",
    RML_MERMAID_GENERATOR,
    ROOT / "sparql" / "empty-games-prototype.rq",
    ROOT / "sparql" / "query-inventory.md",
    ROOT / "sparql" / "graph-condensation-requirements.md",
    ROOT / "sparql" / "query-index" / "README.md",
    SAMPLE,
)

OFFLINE_PIPELINE_PATHS = (
    ROOT / "scripts" / "infra" / "configure-nifi-games-manual.ps1",
    ROOT / "scripts" / "pipeline" / "import-game-json.ps1",
    ROOT / "scripts" / "pipeline" / "process-staged-game-json.ps1",
)

MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
REMOTE_PREFIXES = ("http://", "https://", "mailto:", "#")
MERMAID_DIAGRAM_TYPES = (
    "flowchart",
    "graph",
    "sequenceDiagram",
    "classDiagram",
    "stateDiagram",
    "erDiagram",
    "journey",
    "gantt",
    "pie",
    "mindmap",
    "timeline",
    "gitGraph",
)


def require_layout() -> None:
    missing = [path.relative_to(ROOT) for path in REQUIRED_PATHS if not path.exists()]
    if missing:
        raise ValueError("Missing required paths: " + ", ".join(map(str, missing)))


def validate_json() -> int:
    files = list(ROOT.rglob("*.json"))
    for path in files:
        with path.open(encoding="utf-8") as stream:
            json.load(stream)
    return len(files)


def validate_turtle() -> int:
    files = list(ROOT.rglob("*.ttl"))
    for path in files:
        Graph().parse(path, format="turtle")
    return len(files)


def validate_sparql() -> int:
    files = list(SPARQL_ROOT.rglob("*.rq"))
    component_files = list((SPARQL_ROOT / "query-index" / "components").glob("*.rq"))
    canned_files = [path for path in files if path not in component_files]
    if len(canned_files) != 48 or len(component_files) != 12:
        raise ValueError(
            "Expected 48 canned SPARQL queries and 12 query-index components, "
            f"found {len(canned_files)} and {len(component_files)}"
        )
    for path in files:
        try:
            prepareQuery(path.read_text(encoding="utf-8"))
        except Exception as error:
            raise ValueError(
                f"SPARQL parse failed in {path.relative_to(ROOT)}: {error}"
            ) from error
    return len(files)


def validate_query_contract() -> None:
    query_files = list(SPARQL_ROOT.rglob("*.rq")) + list(QUERY_BUILDERS)
    prohibited = (
        ("removed participant predicate", "cco:ont00001833"),
        ("outcome-specific runner identity path", "runner-act/advance"),
        ("outcome-specific runner identity path", "runner-act/score"),
        ("outcome-specific runner identity path", "runner-act/out"),
    )
    for path in query_files:
        text = path.read_text(encoding="utf-8")
        for description, fragment in prohibited:
            if fragment in text:
                raise ValueError(
                    f"Query contract contains {description} in "
                    f"{path.relative_to(ROOT)}: {fragment}"
                )


def validate_markdown() -> tuple[int, int]:
    markdown_files = list(ROOT.rglob("*.md"))
    mermaid_blocks = 0

    for path in markdown_files:
        text = path.read_text(encoding="utf-8")
        if r"\`\`\`mermaid" in text:
            raise ValueError(
                f"Escaped Mermaid fence cannot render in a browser: {path.relative_to(ROOT)}"
            )
        for match in MARKDOWN_LINK.finditer(text):
            target = match.group(1).strip("<>")
            if target.startswith(REMOTE_PREFIXES):
                continue
            relative_target = unquote(target.split("#", 1)[0])
            if relative_target and not (path.parent / relative_target).resolve().exists():
                raise ValueError(
                    f"Broken Markdown link in {path.relative_to(ROOT)}: {target}"
                )

        fence_language: str | None = None
        fence_body: list[str] = []
        for line in text.splitlines():
            if line.startswith("```"):
                if fence_language is None:
                    fence_language = line[3:].strip()
                    fence_body = []
                else:
                    if fence_language == "mermaid":
                        mermaid_blocks += 1
                        first = next((item.strip() for item in fence_body if item.strip()), "")
                        if not first.startswith(MERMAID_DIAGRAM_TYPES):
                            raise ValueError(
                                f"Unknown Mermaid diagram start in {path.relative_to(ROOT)}: "
                                f"{first!r}"
                            )
                    fence_language = None
                    fence_body = []
            elif fence_language is not None:
                fence_body.append(line)
        if fence_language is not None:
            raise ValueError(f"Unclosed code fence in {path.relative_to(ROOT)}")

    return len(markdown_files), mermaid_blocks


def validate_active_mapping() -> None:
    subprocess.run(
        [sys.executable, str(MAPPING_VALIDATOR), str(SAMPLE)],
        cwd=MAPPING_VALIDATOR.parent,
        check=True,
    )


def validate_ontology_overlay() -> None:
    subprocess.run(
        [sys.executable, str(ONTOLOGY_OVERLAY_VALIDATOR)],
        cwd=ROOT,
        check=True,
    )


def validate_rml_mermaid() -> None:
    subprocess.run(
        [sys.executable, str(RML_MERMAID_GENERATOR), "--check"],
        cwd=ROOT,
        check=True,
    )


def validate_offline_pipeline_boundary() -> None:
    prohibited = ("statsapi.mlb.com", "acquire-daily-games.ps1")
    for path in OFFLINE_PIPELINE_PATHS:
        text = path.read_text(encoding="utf-8").lower()
        matches = [value for value in prohibited if value.lower() in text]
        if matches:
            raise ValueError(
                "Active offline pipeline references external acquisition in "
                f"{path.relative_to(ROOT)}: {', '.join(matches)}"
            )


def main() -> None:
    require_layout()
    json_count = validate_json()
    turtle_count = validate_turtle()
    sparql_count = validate_sparql()
    validate_query_contract()
    markdown_count, mermaid_count = validate_markdown()
    validate_ontology_overlay()
    validate_active_mapping()
    validate_rml_mermaid()
    validate_offline_pipeline_boundary()
    print(f"JSON files parsed: {json_count}")
    print(f"Turtle files parsed: {turtle_count}")
    print(f"SPARQL queries parsed: {sparql_count}")
    print(f"Markdown files checked: {markdown_count}")
    print(f"Mermaid blocks checked: {mermaid_count}")
    print("Active manual pipeline contains no MLB acquisition endpoint or command.")
    print("Repository validation passed.")


if __name__ == "__main__":
    main()
