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


ROOT = Path(__file__).resolve().parents[1]
ACTIVE_MAPPING = ROOT / "mappings" / "direct" / "mlb-direct.rml.ttl"
MAPPING_VALIDATOR = ROOT / "mappings" / "direct" / "validate_direct_mapping.py"
SAMPLE = ROOT / "data" / "raw" / "game-566279.json"

REQUIRED_PATHS = (
    ROOT / "README.md",
    ROOT / "ontology" / "BaseballO.ttl",
    ACTIVE_MAPPING,
    ROOT / "mappings" / "policies" / "modeling-choices.yaml",
    ROOT / "mappings" / "policies" / "iri-policy.yaml",
    ROOT / "mermaid" / "README.md",
    ROOT / "infra" / "README.md",
    ROOT / "infra" / "fuseki" / "configuration" / "baseball-dev.ttl",
    ROOT / "infra" / "versions.psd1",
    ROOT / "scripts" / "infra" / "configure-nifi-foundation.ps1",
    ROOT / "scripts" / "infra" / "configure-nifi-rdf-skeleton.ps1",
    ROOT / "scripts" / "infra" / "configure-nifi-games-daily.ps1",
    ROOT / "scripts" / "pipeline" / "run-rml.ps1",
    ROOT / "scripts" / "pipeline" / "acquire-daily-games.ps1",
    ROOT / "scripts" / "pipeline" / "load-game-graph.ps1",
    ROOT / "scripts" / "pipeline" / "validate-generated-rdf.py",
    SAMPLE,
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


def validate_markdown() -> tuple[int, int]:
    markdown_files = list(ROOT.rglob("*.md"))
    mermaid_blocks = 0

    for path in markdown_files:
        text = path.read_text(encoding="utf-8")
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


def main() -> None:
    require_layout()
    json_count = validate_json()
    turtle_count = validate_turtle()
    markdown_count, mermaid_count = validate_markdown()
    validate_active_mapping()
    print(f"JSON files parsed: {json_count}")
    print(f"Turtle files parsed: {turtle_count}")
    print(f"Markdown files checked: {markdown_count}")
    print(f"Mermaid blocks checked: {mermaid_count}")
    print("Repository validation passed.")


if __name__ == "__main__":
    main()
