#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

import yaml
from rdflib import Graph, URIRef

ROOT = Path(__file__).resolve().parent
DATA = ROOT.parent.parent
MAPPING = ROOT / "mlb-stage1.yml"
INPUT = ROOT / "current-game.json"

PREFIXES = {
    "base": "https://baseballontology.org/",
    "obo": "http://purl.obolibrary.org/obo/",
    "cco": "https://www.commoncoreontologies.org/",
}

ONTOLOGY_FILES = [
    DATA / "BaseballO.ttl",
    DATA / "bfo-core(1).ttl",
    DATA / "ExtendedRelationOntology(1).ttl",
    DATA / "AgentOntology.ttl",
    DATA / "InformationEntityOntology.ttl",
]


def collect_prefixed_terms(value: object) -> set[str]:
    text = yaml.safe_dump(value, sort_keys=False)
    return set(re.findall(r"\b(?:base|obo|cco):[A-Za-z0-9_]+", text))


def main() -> None:
    mapping = yaml.safe_load(MAPPING.read_text(encoding="utf-8"))
    source = json.loads(INPUT.read_text(encoding="utf-8"))

    graph = Graph()
    for ontology_file in ONTOLOGY_FILES:
        graph.parse(ontology_file)

    missing: list[tuple[str, str]] = []
    for term in sorted(collect_prefixed_terms(mapping)):
        prefix, local = term.split(":", 1)
        iri = URIRef(PREFIXES[prefix] + local)
        if not any(graph.triples((iri, None, None))):
            missing.append((term, str(iri)))

    event_types = sorted({
        pa.get("eventType") for pa in source["plateAppearances"] if pa.get("eventType")
    })
    specifically_typed = {
        "home_run",
        "single",
        "double",
        "triple",
        "walk",
        "hit_by_pitch",
        "strikeout",
        "field_out",
        "force_out",
        "sac_fly",
        "sac_bunt",
        "fielders_choice",
        "error",
        "field_error",
    }
    generic_only = sorted(set(event_types) - specifically_typed)

    print(f"Mappings: {len(mapping['mappings'])}")
    print(f"Players: {len(source['players'])}")
    print(f"Plate appearances: {len(source['plateAppearances'])}")
    print(f"Pitches: {len(source['pitches'])}")
    print(f"Source result eventTypes: {', '.join(event_types)}")
    print(f"Generic-only eventTypes: {', '.join(generic_only) or 'none'}")

    if missing:
        print("\nMissing ontology IRIs:")
        for term, iri in missing:
            print(f"  {term}: {iri}")
        raise SystemExit(1)

    print("All referenced BFO, CCO, and BaseballO IRIs were found in the local ontology sources.")


if __name__ == "__main__":
    main()
