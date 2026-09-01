#!/usr/bin/env python3
"""Validate the optional BaseballO axiom overlay and its module boundary."""

from __future__ import annotations

from pathlib import Path

from rdflib import BNode, Graph, OWL, RDF, RDFS, URIRef
from rdflib.collection import Collection


ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY_DIR = ROOT / "ontology"
BASE_FILE = ONTOLOGY_DIR / "BaseballO.ttl"
OVERLAY_FILE = ONTOLOGY_DIR / "BaseballO-axioms-overlay.ttl"
BASE_NAMESPACE = "https://baseballontology.org/"
CCO_STASIS = URIRef("https://www.commoncoreontologies.org/ont00000819")
BFO_REALIZES = URIRef("http://purl.obolibrary.org/obo/BFO_0000055")
# BaseballO normally axiomatizes only its own classes. This one reviewed,
# fail-closed exception constrains imported CCO Stasis itself.
REVIEWED_EXTERNAL_AXIOM_TARGETS = {CCO_STASIS}
OVERLAY_IRI = URIRef(
    "https://baseballontology.org/baseball-event-ontology-axioms-overlay"
)
REQUIRED_IMPORTS = {
    URIRef("https://baseballontology.org/baseball-event-ontology"),
    URIRef(
        "http://www.ontologyrepository.com/CommonCoreOntologies/Domain/"
        "CognitiveProcessOntology"
    ),
    URIRef("https://www.commoncoreontologies.org/ModalRelationOntology"),
}
CLASS_FILLER_PREDICATES = (
    OWL.someValuesFrom,
    OWL.allValuesFrom,
    OWL.onClass,
)
CARDINALITY_PREDICATES = (
    OWL.cardinality,
    OWL.minCardinality,
    OWL.maxCardinality,
    OWL.qualifiedCardinality,
    OWL.minQualifiedCardinality,
    OWL.maxQualifiedCardinality,
)


def parse(path: Path) -> Graph:
    return Graph().parse(path, format="turtle")


def repository_vocabulary() -> Graph:
    graph = Graph()
    for path in sorted(ONTOLOGY_DIR.glob("*.ttl")):
        if path != OVERLAY_FILE:
            graph.parse(path, format="turtle")
    return graph


def restriction_class_fillers(overlay: Graph) -> set[URIRef]:
    fillers: set[URIRef] = set()
    for predicate in CLASS_FILLER_PREDICATES:
        fillers.update(
            value
            for value in overlay.objects(None, predicate)
            if isinstance(value, URIRef)
        )

    for list_head in overlay.objects(None, OWL.unionOf):
        if not isinstance(list_head, BNode):
            raise ValueError("owl:unionOf must point to an RDF list")
        fillers.update(
            value for value in Collection(overlay, list_head) if isinstance(value, URIRef)
        )
    for list_head in overlay.objects(None, OWL.intersectionOf):
        if not isinstance(list_head, BNode):
            raise ValueError("owl:intersectionOf must point to an RDF list")
        fillers.update(
            value for value in Collection(overlay, list_head) if isinstance(value, URIRef)
        )
    return fillers


def named_superclasses(graph: Graph, class_iri: URIRef) -> set[URIRef]:
    """Return the named superclass closure, including the class itself."""
    result = {class_iri}
    pending = [class_iri]
    while pending:
        current = pending.pop()
        for parent in graph.objects(current, RDFS.subClassOf):
            if isinstance(parent, URIRef) and parent not in result:
                result.add(parent)
                pending.append(parent)
    return result


def disjoint_superclass_pair(
    graph: Graph, left: URIRef, right: URIRef
) -> tuple[URIRef, URIRef] | None:
    for left_parent in named_superclasses(graph, left):
        for right_parent in named_superclasses(graph, right):
            if (
                (left_parent, OWL.disjointWith, right_parent) in graph
                or (right_parent, OWL.disjointWith, left_parent) in graph
            ):
                return left_parent, right_parent
    return None


def validate() -> tuple[int, int, int]:
    base = parse(BASE_FILE)
    overlay = parse(OVERLAY_FILE)
    vocabulary = repository_vocabulary()

    base_restrictions = set(base.subjects(RDF.type, OWL.Restriction))
    if base_restrictions:
        raise ValueError(
            "BaseballO.ttl contains anonymous OWL restrictions; class restrictions "
            "belong in BaseballO-axioms-overlay.ttl"
        )
    if any(base.triples((None, OWL.equivalentClass, None))):
        raise ValueError(
            "BaseballO.ttl contains owl:equivalentClass axioms; logical class "
            "definitions belong in the overlay"
        )

    imports = set(overlay.objects(OVERLAY_IRI, OWL.imports))
    missing_imports = REQUIRED_IMPORTS - imports
    if missing_imports:
        raise ValueError(
            "Overlay is missing required imports: "
            + ", ".join(sorted(map(str, missing_imports)))
        )

    declared_base_classes = {
        value
        for value in base.subjects(RDF.type, OWL.Class)
        if isinstance(value, URIRef)
    }
    declared_classes = {
        value
        for value in vocabulary.subjects(RDF.type, OWL.Class)
        if isinstance(value, URIRef)
    }
    declared_object_properties = {
        value
        for value in vocabulary.subjects(RDF.type, OWL.ObjectProperty)
        if isinstance(value, URIRef)
    }
    declared_data_properties = {
        value
        for value in vocabulary.subjects(RDF.type, OWL.DatatypeProperty)
        if isinstance(value, URIRef)
    }
    declared_properties = declared_object_properties | declared_data_properties

    local_declarations = {
        value
        for value in overlay.subjects(RDF.type, OWL.Class)
        if isinstance(value, URIRef)
    }
    local_property_declarations = {
        value
        for property_type in (OWL.ObjectProperty, OWL.DatatypeProperty)
        for value in overlay.subjects(RDF.type, property_type)
        if isinstance(value, URIRef)
    }
    if local_declarations or local_property_declarations:
        raise ValueError(
            "The overlay must reuse vocabulary and may not declare named classes "
            "or object properties"
        )

    axiom_subjects = {
        subject
        for subject in overlay.subjects(RDFS.subClassOf, None)
        if isinstance(subject, URIRef)
    }
    external_axiom_targets = axiom_subjects - declared_base_classes
    unknown_subjects = external_axiom_targets - REVIEWED_EXTERNAL_AXIOM_TARGETS
    if unknown_subjects:
        raise ValueError(
            "Overlay axioms target unreviewed classes not declared in BaseballO.ttl: "
            + ", ".join(sorted(map(str, unknown_subjects)))
        )

    if CCO_STASIS in external_axiom_targets:
        stasis_restrictions = {
            restriction
            for restriction in overlay.objects(CCO_STASIS, RDFS.subClassOf)
            if isinstance(restriction, BNode)
        }
        prohibited_realization_restrictions = {
            restriction
            for restriction in stasis_restrictions
            if (restriction, RDF.type, OWL.Restriction) in overlay
            and (restriction, OWL.onProperty, BFO_REALIZES) in overlay
            and any(
                str(cardinality) == "0"
                for cardinality in overlay.objects(restriction, OWL.maxCardinality)
            )
        }
        if len(stasis_restrictions) != 1 or len(prohibited_realization_restrictions) != 1:
            raise ValueError(
                "The reviewed external CCO Stasis axiom must be exactly one "
                "owl:maxCardinality 0 restriction on BFO realizes"
            )

    named_superclasses = {
        value
        for value in overlay.objects(None, RDFS.subClassOf)
        if isinstance(value, URIRef)
    }
    fillers = restriction_class_fillers(overlay)
    datatype_fillers = {
        value for value in fillers
        if str(value).startswith("http://www.w3.org/2001/XMLSchema#")
    }
    unknown_classes = (named_superclasses | fillers) - declared_classes - datatype_fillers
    if unknown_classes:
        raise ValueError(
            "Overlay uses classes not declared in the repository: "
            + ", ".join(sorted(map(str, unknown_classes)))
        )

    restrictions = set(overlay.subjects(RDF.type, OWL.Restriction))
    if not restrictions:
        raise ValueError("Overlay contains no OWL restrictions")

    used_properties: set[URIRef] = set()
    for restriction in restrictions:
        properties = list(overlay.objects(restriction, OWL.onProperty))
        if len(properties) != 1 or not isinstance(properties[0], URIRef):
            raise ValueError(
                "Every overlay restriction must have exactly one named owl:onProperty"
            )
        used_properties.add(properties[0])

        has_cardinality = any(
            next(overlay.objects(restriction, predicate), None) is not None
            for predicate in CARDINALITY_PREDICATES
        )
        if has_cardinality:
            if (properties[0], RDF.type, OWL.TransitiveProperty) in vocabulary:
                raise ValueError(
                    "OWL cardinality restriction uses a transitive, non-simple property: "
                    f"{properties[0]}"
                )

    unknown_properties = used_properties - declared_properties
    if unknown_properties:
        raise ValueError(
            "Overlay uses properties not declared in the repository: "
            + ", ".join(sorted(map(str, unknown_properties)))
        )

    semantic_graph = vocabulary + overlay
    for restriction in restrictions:
        property_iri = next(overlay.objects(restriction, OWL.onProperty))
        axiom_subjects_for_restriction = {
            subject
            for subject in overlay.subjects(RDFS.subClassOf, restriction)
            if isinstance(subject, URIRef)
        }
        named_domains = {
            value
            for value in vocabulary.objects(property_iri, RDFS.domain)
            if isinstance(value, URIRef)
        }
        for subject in axiom_subjects_for_restriction:
            for domain in named_domains:
                conflict = disjoint_superclass_pair(semantic_graph, subject, domain)
                if conflict:
                    raise ValueError(
                        f"Overlay restriction on {subject} conflicts with the domain "
                        f"of {property_iri}; disjoint classes: {conflict[0]}, {conflict[1]}"
                    )

        named_fillers = {
            value
            for predicate in CLASS_FILLER_PREDICATES
            for value in overlay.objects(restriction, predicate)
            if isinstance(value, URIRef)
        }
        named_ranges = {
            value
            for value in vocabulary.objects(property_iri, RDFS.range)
            if isinstance(value, URIRef)
        }
        for filler in named_fillers:
            for range_class in named_ranges:
                conflict = disjoint_superclass_pair(
                    semantic_graph, filler, range_class
                )
                if conflict:
                    raise ValueError(
                        f"Overlay filler {filler} conflicts with the range of "
                        f"{property_iri}; disjoint classes: {conflict[0]}, {conflict[1]}"
                    )

    return len(axiom_subjects), len(restrictions), len(used_properties)


def main() -> None:
    class_count, restriction_count, property_count = validate()
    print(f"Overlay classes axiomatized: {class_count}")
    print(f"Overlay restrictions: {restriction_count}")
    print(f"Reused object and datatype properties: {property_count}")
    print("BaseballO contains no optional class restrictions.")
    print("Ontology overlay validation passed.")


if __name__ == "__main__":
    main()
