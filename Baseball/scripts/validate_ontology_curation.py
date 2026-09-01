#!/usr/bin/env python3
"""Fail-closed structural gate for BaseballO ontology curation.

The project ontologist decides whether a model is semantically correct. This
validator enforces the structural parts of that review contract and freezes
known defects without treating them as accepted modeling decisions.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rdflib import Graph, Literal, OWL, RDF, RDFS, SKOS, URIRef


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ONTOLOGY_DIR = ROOT / "ontology"
DEFAULT_BASE_FILE = DEFAULT_ONTOLOGY_DIR / "BaseballO.ttl"
DEFAULT_OVERLAY_FILE = DEFAULT_ONTOLOGY_DIR / "BaseballO-axioms-overlay.ttl"
DEFAULT_MANIFEST_FILE = ROOT / "governance" / "ontology-curation-debt.json"

EXPECTED_ARTIFACT_TYPE = "baseballo-ontology-curation-debt"
EXPECTED_CONTRACT_VERSION = 1
EXPECTED_STATUS = "frozen-unreviewed-not-accepted"
EXTERNAL_FOUNDATION_PREFIXES = (
    "http://purl.obolibrary.org/obo/BFO_",
    "https://www.commoncoreontologies.org/",
    "http://www.ontologyrepository.com/CommonCoreOntologies/",
)
DEBT_KEYS = (
    "danglingNamedParents",
    "multipleDirectNamedParents",
    "missingExampleOrEditorialNote",
    "notGroundedInBfoOrCco",
)


class OntologyCurationError(ValueError):
    """Raised when the ontology curation contract is violated."""


@dataclass(frozen=True)
class CurationSummary:
    local_class_count: int
    frozen_debt_count: int
    local_object_property_count: int
    local_datatype_property_count: int


def parse_graph(path: Path) -> Graph:
    if not path.is_file():
        raise OntologyCurationError(f"Required ontology file is missing: {path}")
    try:
        return Graph().parse(path, format="turtle")
    except Exception as error:  # rdflib exposes several parser exception types
        raise OntologyCurationError(f"Could not parse Turtle file {path}: {error}") from error


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise OntologyCurationError(f"Ontology curation manifest is missing: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise OntologyCurationError(
            f"Could not read ontology curation manifest {path}: {error}"
        ) from error
    if not isinstance(value, dict):
        raise OntologyCurationError("Ontology curation manifest root must be an object")
    if value.get("artifactType") != EXPECTED_ARTIFACT_TYPE:
        raise OntologyCurationError("Ontology curation manifest artifactType is invalid")
    if value.get("contractVersion") != EXPECTED_CONTRACT_VERSION:
        raise OntologyCurationError("Ontology curation manifest contractVersion is invalid")
    if value.get("status") != EXPECTED_STATUS:
        raise OntologyCurationError(
            "Ontology debt must remain explicitly frozen, unreviewed, and not accepted"
        )
    return value


def uri_strings(values: set[URIRef] | list[URIRef]) -> list[str]:
    return sorted(str(value) for value in values)


def require_string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise OntologyCurationError(f"Manifest field {field} must be an array of strings")
    if len(value) != len(set(value)):
        raise OntologyCurationError(f"Manifest field {field} contains duplicate values")
    return sorted(value)


def require_parent_debt(value: Any, field: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise OntologyCurationError(f"Manifest field {field} must be an array")
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in value:
        if not isinstance(entry, dict) or set(entry) != {"class", "parents"}:
            raise OntologyCurationError(
                f"Every {field} entry must contain exactly class and parents"
            )
        class_iri = entry["class"]
        if not isinstance(class_iri, str) or not class_iri:
            raise OntologyCurationError(f"Every {field} class must be a non-empty IRI")
        parents = require_string_list(entry["parents"], f"{field}.{class_iri}.parents")
        if not parents:
            raise OntologyCurationError(f"Every {field} entry must name at least one parent")
        key = json.dumps({"class": class_iri, "parents": parents}, sort_keys=True)
        if key in seen:
            raise OntologyCurationError(f"Manifest field {field} contains duplicate entries")
        seen.add(key)
        normalized.append({"class": class_iri, "parents": parents})
    return sorted(normalized, key=lambda item: item["class"])


def normalized_debt(manifest: dict[str, Any]) -> dict[str, Any]:
    debt = manifest.get("frozenDebt")
    if not isinstance(debt, dict) or set(debt) != set(DEBT_KEYS):
        raise OntologyCurationError(
            "Manifest frozenDebt must contain exactly: " + ", ".join(DEBT_KEYS)
        )
    return {
        "danglingNamedParents": require_parent_debt(
            debt["danglingNamedParents"], "frozenDebt.danglingNamedParents"
        ),
        "multipleDirectNamedParents": require_parent_debt(
            debt["multipleDirectNamedParents"],
            "frozenDebt.multipleDirectNamedParents",
        ),
        "missingExampleOrEditorialNote": require_string_list(
            debt["missingExampleOrEditorialNote"],
            "frozenDebt.missingExampleOrEditorialNote",
        ),
        "notGroundedInBfoOrCco": require_string_list(
            debt["notGroundedInBfoOrCco"],
            "frozenDebt.notGroundedInBfoOrCco",
        ),
    }


def validate_imports(
    graph: Graph, document_name: str, contract: Any
) -> None:
    if not isinstance(contract, dict) or set(contract) != {"ontologyIri", "allowedImports"}:
        raise OntologyCurationError(
            f"Manifest ontologyDocuments.{document_name} must contain exactly "
            "ontologyIri and allowedImports"
        )
    ontology_iri_text = contract["ontologyIri"]
    if not isinstance(ontology_iri_text, str) or not ontology_iri_text:
        raise OntologyCurationError(
            f"Manifest ontologyDocuments.{document_name}.ontologyIri is invalid"
        )
    allowed = set(
        require_string_list(
            contract["allowedImports"],
            f"ontologyDocuments.{document_name}.allowedImports",
        )
    )
    ontology_iri = URIRef(ontology_iri_text)
    declared_ontologies = {
        subject
        for subject in graph.subjects(RDF.type, OWL.Ontology)
        if isinstance(subject, URIRef)
    }
    if declared_ontologies != {ontology_iri}:
        raise OntologyCurationError(
            f"{document_name} ontology declaration differs from its frozen contract: "
            f"{uri_strings(declared_ontologies)}"
        )
    actual = {
        str(value)
        for value in graph.objects(ontology_iri, OWL.imports)
        if isinstance(value, URIRef)
    }
    non_iri_imports = [
        value
        for value in graph.objects(ontology_iri, OWL.imports)
        if not isinstance(value, URIRef)
    ]
    if non_iri_imports or actual != allowed:
        raise OntologyCurationError(
            f"{document_name} imports differ from the allowlist; "
            f"expected={sorted(allowed)}, actual={sorted(actual)}"
        )


def is_foundation_class(value: URIRef) -> bool:
    return str(value).startswith(EXTERNAL_FOUNDATION_PREFIXES)


def has_foundation_closure(
    class_iri: URIRef, vocabulary: Graph, declared_classes: set[URIRef]
) -> bool:
    pending = [class_iri]
    visited: set[URIRef] = set()
    while pending:
        current = pending.pop()
        if current in visited:
            continue
        visited.add(current)
        if current in declared_classes and is_foundation_class(current):
            return True
        pending.extend(
            parent
            for parent in vocabulary.objects(current, RDFS.subClassOf)
            if isinstance(parent, URIRef)
            and parent in declared_classes
            and parent not in visited
        )
    return False


def compare_frozen_debt(field: str, expected: Any, actual: Any) -> None:
    expected_items = {
        json.dumps(item, sort_keys=True, separators=(",", ":")) for item in expected
    }
    actual_items = {
        json.dumps(item, sort_keys=True, separators=(",", ":")) for item in actual
    }
    new_debt = sorted(actual_items - expected_items)
    stale_debt = sorted(expected_items - actual_items)
    if new_debt or stale_debt:
        details: list[str] = []
        if new_debt:
            details.append(f"new unreviewed findings={new_debt}")
        if stale_debt:
            details.append(
                "resolved or changed findings still frozen in the manifest="
                f"{stale_debt}"
            )
        raise OntologyCurationError(
            f"Frozen ontology debt mismatch for {field}; " + "; ".join(details)
        )


def validate_curation(
    *,
    ontology_dir: Path = DEFAULT_ONTOLOGY_DIR,
    base_file: Path = DEFAULT_BASE_FILE,
    overlay_file: Path = DEFAULT_OVERLAY_FILE,
    manifest_file: Path = DEFAULT_MANIFEST_FILE,
) -> CurationSummary:
    ontology_dir = Path(ontology_dir)
    base_file = Path(base_file)
    overlay_file = Path(overlay_file)
    manifest_file = Path(manifest_file)

    manifest = load_manifest(manifest_file)
    base_namespace = manifest.get("baseNamespace")
    if not isinstance(base_namespace, str) or not base_namespace:
        raise OntologyCurationError("Manifest baseNamespace must be a non-empty IRI")

    base = parse_graph(base_file)
    overlay = parse_graph(overlay_file)
    ontology_documents = manifest.get("ontologyDocuments")
    if not isinstance(ontology_documents, dict) or set(ontology_documents) != {
        "base",
        "overlay",
    }:
        raise OntologyCurationError(
            "Manifest ontologyDocuments must contain exactly base and overlay"
        )
    validate_imports(base, "base", ontology_documents["base"])
    validate_imports(overlay, "overlay", ontology_documents["overlay"])

    turtle_files = sorted(ontology_dir.glob("*.ttl"))
    if not turtle_files:
        raise OntologyCurationError(f"No ontology vocabulary files found in {ontology_dir}")
    vocabulary = Graph()
    for path in turtle_files:
        vocabulary.parse(path, format="turtle")

    local_classes = sorted(
        {
            value
            for value in base.subjects(RDF.type, OWL.Class)
            if isinstance(value, URIRef) and str(value).startswith(base_namespace)
        },
        key=str,
    )
    if not local_classes:
        raise OntologyCurationError("BaseballO declares no local owl:Class vocabulary")

    declared_classes = {
        value
        for class_type in (OWL.Class, RDFS.Class)
        for value in vocabulary.subjects(RDF.type, class_type)
        if isinstance(value, URIRef)
    }

    dangling: list[dict[str, Any]] = []
    multiple: list[dict[str, Any]] = []
    missing_annotation: list[str] = []
    ungrounded: list[str] = []
    immediate_errors: list[str] = []

    for class_iri in local_classes:
        labels = [
            value
            for value in base.objects(class_iri, RDFS.label)
            if isinstance(value, Literal) and value.language == "en"
        ]
        definitions = [
            value
            for value in base.objects(class_iri, SKOS.definition)
            if isinstance(value, Literal) and value.language == "en"
        ]
        if len(labels) != 1:
            immediate_errors.append(
                f"{class_iri} must have exactly one English rdfs:label; found {len(labels)}"
            )
        if len(definitions) != 1:
            immediate_errors.append(
                f"{class_iri} must have exactly one English skos:definition; "
                f"found {len(definitions)}"
            )
        if len(labels) == 1 and len(definitions) == 1:
            label = str(labels[0])
            definition = str(definitions[0])
            prefix = re.compile(
                rf"^(?:A|An) {re.escape(label)} is (?:a|an) \S",
                flags=re.UNICODE,
            )
            if prefix.match(definition) is None:
                immediate_errors.append(
                    f"{class_iri} definition does not begin with the required "
                    f"Aristotelian prefix for label {label!r}"
                )

        parents = sorted(
            {
                parent
                for parent in base.objects(class_iri, RDFS.subClassOf)
                if isinstance(parent, URIRef)
            },
            key=str,
        )
        if not parents:
            immediate_errors.append(f"{class_iri} has no direct named superclass")
        elif len(parents) > 1:
            multiple.append(
                {"class": str(class_iri), "parents": uri_strings(parents)}
            )

        missing_parents = [parent for parent in parents if parent not in declared_classes]
        if missing_parents:
            dangling.append(
                {"class": str(class_iri), "parents": uri_strings(missing_parents)}
            )

        examples = [
            value
            for value in base.objects(class_iri, SKOS.example)
            if isinstance(value, Literal) and value.language == "en"
        ]
        editorial_notes = [
            value
            for value in base.objects(class_iri, SKOS.editorialNote)
            if isinstance(value, Literal) and value.language == "en"
        ]
        if not examples and not editorial_notes:
            missing_annotation.append(str(class_iri))

        if not has_foundation_closure(class_iri, vocabulary, declared_classes):
            ungrounded.append(str(class_iri))

    if immediate_errors:
        raise OntologyCurationError(
            "Ontology class authoring violations:\n- " + "\n- ".join(immediate_errors)
        )

    property_contract = manifest.get("approvedLocalProperties")
    if not isinstance(property_contract, dict) or set(property_contract) != {
        "object",
        "datatype",
    }:
        raise OntologyCurationError(
            "Manifest approvedLocalProperties must contain exactly object and datatype"
        )
    approved_object = set(
        require_string_list(
            property_contract["object"], "approvedLocalProperties.object"
        )
    )
    approved_datatype = set(
        require_string_list(
            property_contract["datatype"], "approvedLocalProperties.datatype"
        )
    )
    actual_object = {
        str(value)
        for value in vocabulary.subjects(RDF.type, OWL.ObjectProperty)
        if isinstance(value, URIRef) and str(value).startswith(base_namespace)
    }
    actual_datatype = {
        str(value)
        for value in vocabulary.subjects(RDF.type, OWL.DatatypeProperty)
        if isinstance(value, URIRef) and str(value).startswith(base_namespace)
    }
    generic_local_properties = {
        str(value)
        for value in vocabulary.subjects(RDF.type, RDF.Property)
        if isinstance(value, URIRef)
        and str(value).startswith(base_namespace)
        and str(value) not in actual_object | actual_datatype
    }
    if generic_local_properties:
        raise OntologyCurationError(
            "Undifferentiated local rdf:Property declarations are not approved: "
            + ", ".join(sorted(generic_local_properties))
        )
    if actual_object != approved_object:
        raise OntologyCurationError(
            "Local object-property declarations differ from the explicit approval list; "
            f"approved={sorted(approved_object)}, actual={sorted(actual_object)}"
        )
    if actual_datatype != approved_datatype:
        raise OntologyCurationError(
            "Local datatype-property declarations differ from the explicit approval list; "
            f"approved={sorted(approved_datatype)}, actual={sorted(actual_datatype)}"
        )

    expected_debt = normalized_debt(manifest)
    actual_debt = {
        "danglingNamedParents": sorted(dangling, key=lambda item: item["class"]),
        "multipleDirectNamedParents": sorted(
            multiple, key=lambda item: item["class"]
        ),
        "missingExampleOrEditorialNote": sorted(missing_annotation),
        "notGroundedInBfoOrCco": sorted(ungrounded),
    }
    for field in DEBT_KEYS:
        compare_frozen_debt(field, expected_debt[field], actual_debt[field])

    return CurationSummary(
        local_class_count=len(local_classes),
        frozen_debt_count=sum(len(actual_debt[field]) for field in DEBT_KEYS),
        local_object_property_count=len(actual_object),
        local_datatype_property_count=len(actual_datatype),
    )


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate the fail-closed BaseballO ontology curation contract."
    )
    parser.add_argument("--ontology-dir", type=Path, default=DEFAULT_ONTOLOGY_DIR)
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE_FILE)
    parser.add_argument("--overlay", type=Path, default=DEFAULT_OVERLAY_FILE)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST_FILE)
    return parser.parse_args()


def main() -> None:
    options = arguments()
    summary = validate_curation(
        ontology_dir=options.ontology_dir,
        base_file=options.base,
        overlay_file=options.overlay,
        manifest_file=options.manifest,
    )
    print(f"Local BaseballO classes checked: {summary.local_class_count}")
    print(
        "Approved local properties checked: "
        f"{summary.local_object_property_count} object, "
        f"{summary.local_datatype_property_count} datatype"
    )
    print(
        f"Frozen unresolved findings matched exactly: {summary.frozen_debt_count}"
    )
    print("Ontology curation validation passed.")


if __name__ == "__main__":
    main()
