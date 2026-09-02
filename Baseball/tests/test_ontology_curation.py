from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

from owlrl import DeductiveClosure, OWLRL_Semantics
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, XSD


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "scripts" / "validate_ontology_curation.py"
SPEC = importlib.util.spec_from_file_location("validate_ontology_curation", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Could not load {SCRIPT}")
CURATION = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CURATION
SPEC.loader.exec_module(CURATION)


BASE = "https://baseballontology.org/"
BASE_ONTOLOGY = BASE + "baseball-event-ontology"
OVERLAY_ONTOLOGY = BASE + "baseball-event-ontology-axioms-overlay"
BFO_PROCESS = "http://purl.obolibrary.org/obo/BFO_0000015"
BFO_IMPORT = "http://purl.obolibrary.org/obo/bfo/2020/bfo-core.ttl"
CCO = Namespace("https://www.commoncoreontologies.org/")
MRO = Namespace("https://www.commoncoreontologies.org/mro/")
EX = Namespace("https://baseballontology.org/test/ice-direct/")


def reasoning_module(source: Graph, seeds: set[URIRef]) -> Graph:
    """Extract a small, transitive OWL-RL module around reviewed terms."""
    module = Graph()
    frontier = set(seeds)
    copied: set[URIRef] = set()
    followed = {
        RDF.type,
        RDFS.domain,
        RDFS.range,
        RDFS.subClassOf,
        RDFS.subPropertyOf,
        OWL.inverseOf,
    }
    while frontier:
        subject = frontier.pop()
        if subject in copied:
            continue
        copied.add(subject)
        for _, predicate, obj in source.triples((subject, None, None)):
            if predicate not in followed:
                continue
            module.add((subject, predicate, obj))
            if predicate in {
                RDFS.subClassOf,
                RDFS.subPropertyOf,
                OWL.inverseOf,
            } and isinstance(obj, URIRef):
                frontier.add(obj)
        for inverse_subject in source.subjects(OWL.inverseOf, subject):
            module.add((inverse_subject, OWL.inverseOf, subject))
            frontier.add(inverse_subject)
    return module


class CurationFixture:
    def __init__(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="baseballo-curation-test-")
        self.root = Path(self.temporary.name)
        self.ontology_dir = self.root / "ontology"
        self.ontology_dir.mkdir()
        self.base_file = self.ontology_dir / "BaseballO.ttl"
        self.overlay_file = self.ontology_dir / "BaseballO-axioms-overlay.ttl"
        self.manifest_file = self.root / "ontology-curation-debt.json"
        self.write_dependency()
        self.write_base()
        self.write_overlay()
        self.manifest = self.empty_manifest()
        self.write_manifest()

    def close(self) -> None:
        self.temporary.cleanup()

    def write_dependency(self, extra: str = "") -> None:
        (self.ontology_dir / "dependency.ttl").write_text(
            "\n".join(
                (
                    "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
                    "<http://purl.obolibrary.org/obo/BFO_0000015> a owl:Class .",
                    extra,
                    "",
                )
            ),
            encoding="utf-8",
        )

    def write_base(
        self,
        *,
        parent: str = BFO_PROCESS,
        include_label: bool = True,
        definition: str = "A Good Class is a Process that is used by a test.",
        include_example: bool = True,
        extra: str = "",
    ) -> None:
        annotations = []
        if include_label:
            annotations.append('    rdfs:label "Good Class"@en')
        annotations.append(f'    skos:definition "{definition}"@en')
        if include_example:
            annotations.append('    skos:example "A test process."@en')
        joined_annotations = " ;\n".join(annotations) + " ."
        self.base_file.write_text(
            "\n".join(
                (
                    "@prefix base: <https://baseballontology.org/> .",
                    "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
                    "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
                    "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
                    "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .",
                    "",
                    f"<{BASE_ONTOLOGY}> a owl:Ontology ;",
                    f"    owl:imports <{BFO_IMPORT}> .",
                    "",
                    "base:GoodClass a owl:Class ;",
                    f"    rdfs:subClassOf <{parent}> ;",
                    joined_annotations,
                    "",
                    extra,
                    "",
                )
            ),
            encoding="utf-8",
        )

    def write_overlay(self, extra: str = "") -> None:
        self.overlay_file.write_text(
            "\n".join(
                (
                    "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
                    f"<{OVERLAY_ONTOLOGY}> a owl:Ontology ;",
                    f"    owl:imports <{BASE_ONTOLOGY}> .",
                    extra,
                    "",
                )
            ),
            encoding="utf-8",
        )

    @staticmethod
    def empty_manifest() -> dict:
        return {
            "artifactType": "baseballo-ontology-curation-debt",
            "contractVersion": 1,
            "status": "frozen-unreviewed-not-accepted",
            "baseNamespace": BASE,
            "ontologyDocuments": {
                "base": {
                    "ontologyIri": BASE_ONTOLOGY,
                    "allowedImports": [BFO_IMPORT],
                },
                "overlay": {
                    "ontologyIri": OVERLAY_ONTOLOGY,
                    "allowedImports": [BASE_ONTOLOGY],
                },
            },
            "approvedLocalProperties": {"object": [], "datatype": []},
            "frozenDebt": {
                "danglingNamedParents": [],
                "multipleDirectNamedParents": [],
                "missingExampleOrEditorialNote": [],
                "notGroundedInBfoOrCco": [],
            },
        }

    def write_manifest(self) -> None:
        self.manifest_file.write_text(
            json.dumps(self.manifest, indent=2) + "\n", encoding="utf-8"
        )

    def validate(self):
        return CURATION.validate_curation(
            ontology_dir=self.ontology_dir,
            base_file=self.base_file,
            overlay_file=self.overlay_file,
            manifest_file=self.manifest_file,
        )


class OntologyCurationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = CurationFixture()

    def tearDown(self) -> None:
        self.fixture.close()

    def test_minimal_conforming_ontology_passes(self) -> None:
        summary = self.fixture.validate()
        self.assertEqual(summary.local_class_count, 1)
        self.assertEqual(summary.frozen_debt_count, 0)

    def test_current_repository_matches_frozen_debt_exactly(self) -> None:
        summary = CURATION.validate_curation()
        self.assertEqual(summary.local_class_count, 272)
        self.assertEqual(summary.frozen_debt_count, 3)
        self.assertEqual(summary.local_object_property_count, 0)
        self.assertEqual(summary.local_datatype_property_count, 0)

    def test_direct_ice_values_and_units_do_not_infer_an_information_bearing_entity(self) -> None:
        ontology_files = (
            (
                PROJECT_ROOT / "ontology" / "CommonCoreOntologiesMerged.ttl",
                CCO,
                URIRef("http://purl.obolibrary.org/obo/BFO_0000101"),
                URIRef("http://purl.obolibrary.org/obo/BFO_0000084"),
            ),
            (
                PROJECT_ROOT / "ontology" / "ModalRelationOntology.ttl",
                MRO,
                MRO.BFO_0000101,
                MRO.BFO_0000084,
            ),
        )
        information_content_entity = CCO.ont00000958
        information_bearing_entity = CCO.ont00000253
        measurement_ice = CCO.ont00001163
        measurement_unit = CCO.ont00000120
        reference_system = CCO.ont00000398

        for ontology_file, relation_namespace, carrier, carrier_inverse in ontology_files:
            with self.subTest(ontology=ontology_file.name):
                source = Graph().parse(ontology_file)
                for local_name in (
                    "ont00001763",
                    "ont00001764",
                    "ont00001765",
                    "ont00001766",
                    "ont00001767",
                    "ont00001768",
                    "ont00001769",
                    "ont00001770",
                    "ont00001771",
                    "ont00001772",
                    "ont00001773",
                ):
                    self.assertIn(
                        (relation_namespace[local_name], RDFS.domain, information_content_entity),
                        source,
                    )

                reviewed_relations = {
                    relation_namespace.ont00001863: (
                        information_content_entity,
                        measurement_unit,
                        relation_namespace.ont00001961,
                    ),
                    relation_namespace.ont00001961: (
                        measurement_unit,
                        information_content_entity,
                        relation_namespace.ont00001863,
                    ),
                    relation_namespace.ont00001912: (
                        information_content_entity,
                        reference_system,
                        relation_namespace.ont00001997,
                    ),
                    relation_namespace.ont00001997: (
                        reference_system,
                        information_content_entity,
                        relation_namespace.ont00001912,
                    ),
                    relation_namespace.ont00001913: (
                        information_content_entity,
                        CCO.ont00000469,
                        relation_namespace.ont00001900,
                    ),
                    relation_namespace.ont00001900: (
                        CCO.ont00000469,
                        information_content_entity,
                        relation_namespace.ont00001913,
                    ),
                }
                for relation, (domain, range_, inverse) in reviewed_relations.items():
                    self.assertIn((relation, RDFS.domain, domain), source)
                    self.assertIn((relation, RDFS.range, range_), source)
                    self.assertTrue(
                        (relation, OWL.inverseOf, inverse) in source
                        or (inverse, OWL.inverseOf, relation) in source
                    )

                self.assertNotIn(
                    (relation_namespace.ont00001863, RDFS.subPropertyOf, carrier), source
                )
                self.assertNotIn(
                    (relation_namespace.ont00001961, RDFS.subPropertyOf, carrier_inverse),
                    source,
                )
                self.assertNotIn(
                    (relation_namespace.ont00001912, RDFS.subPropertyOf, carrier), source
                )
                self.assertNotIn(
                    (relation_namespace.ont00001997, RDFS.subPropertyOf, carrier_inverse),
                    source,
                )
                properties = {
                    relation_namespace.ont00001769,
                    relation_namespace.ont00001863,
                    relation_namespace.ont00001961,
                    relation_namespace.ont00001912,
                    relation_namespace.ont00001997,
                    carrier,
                    carrier_inverse,
                    measurement_ice,
                    information_content_entity,
                    information_bearing_entity,
                }
                graph = reasoning_module(source, properties)
                sample = EX[f"measurement-{ontology_file.stem}"]
                unit = EX[f"unit-{ontology_file.stem}"]
                reference = EX[f"reference-{ontology_file.stem}"]
                bearer = EX[f"bearer-{ontology_file.stem}"]

                graph.add((sample, RDF.type, measurement_ice))
                graph.add((sample, relation_namespace.ont00001769, Literal("310", datatype=XSD.decimal)))
                graph.add((sample, relation_namespace.ont00001863, unit))
                graph.add((sample, relation_namespace.ont00001912, reference))
                graph.add((unit, RDF.type, measurement_unit))
                graph.add((reference, RDF.type, reference_system))
                graph.add((bearer, RDF.type, information_bearing_entity))
                graph.add((bearer, carrier, sample))

                DeductiveClosure(OWLRL_Semantics, axiomatic_triples=False).expand(graph)

                self.assertIn((sample, RDF.type, information_content_entity), graph)
                self.assertNotIn((sample, RDF.type, information_bearing_entity), graph)
                self.assertIn((unit, relation_namespace.ont00001961, sample), graph)
                self.assertIn((reference, relation_namespace.ont00001997, sample), graph)
                self.assertIn((bearer, carrier, sample), graph)
                self.assertIn((sample, carrier_inverse, bearer), graph)
                self.assertIn((bearer, RDF.type, information_bearing_entity), graph)
                self.assertNotIn(
                    (relation_namespace.ont00001863, RDFS.subPropertyOf, carrier), graph
                )
                self.assertNotIn(
                    (relation_namespace.ont00001912, RDFS.subPropertyOf, carrier), graph
                )

    def test_missing_english_label_is_rejected(self) -> None:
        self.fixture.write_base(include_label=False)
        with self.assertRaisesRegex(CURATION.OntologyCurationError, "English rdfs:label"):
            self.fixture.validate()

    def test_non_aristotelian_definition_prefix_is_rejected(self) -> None:
        self.fixture.write_base(definition="Reported by a convenient source field.")
        with self.assertRaisesRegex(CURATION.OntologyCurationError, "Aristotelian prefix"):
            self.fixture.validate()

    def test_new_multiple_parent_debt_is_rejected(self) -> None:
        self.fixture.write_dependency(
            "<https://www.commoncoreontologies.org/ont00000001> a "
            "<http://www.w3.org/2002/07/owl#Class> ."
        )
        self.fixture.write_base(
            extra=(
                "base:GoodClass rdfs:subClassOf "
                "<https://www.commoncoreontologies.org/ont00000001> ."
            )
        )
        with self.assertRaisesRegex(CURATION.OntologyCurationError, "new unreviewed findings"):
            self.fixture.validate()

    def test_resolved_multiple_parent_debt_requires_manifest_cleanup(self) -> None:
        second_parent = "https://www.commoncoreontologies.org/ont00000001"
        self.fixture.write_dependency(
            f"<{second_parent}> a <http://www.w3.org/2002/07/owl#Class> ."
        )
        self.fixture.write_base(
            extra=f"base:GoodClass rdfs:subClassOf <{second_parent}> ."
        )
        self.fixture.manifest["frozenDebt"]["multipleDirectNamedParents"] = [
            {
                "class": BASE + "GoodClass",
                "parents": sorted([BFO_PROCESS, second_parent]),
            }
        ]
        self.fixture.write_manifest()
        self.fixture.validate()

        self.fixture.write_base()
        with self.assertRaisesRegex(
            CURATION.OntologyCurationError, "resolved or changed findings"
        ):
            self.fixture.validate()

    def test_dangling_and_ungrounded_debt_is_exact_and_not_approval(self) -> None:
        missing_parent = BASE + "MissingParent"
        self.fixture.write_base(parent=missing_parent)
        self.fixture.manifest["frozenDebt"]["danglingNamedParents"] = [
            {"class": BASE + "GoodClass", "parents": [missing_parent]}
        ]
        self.fixture.manifest["frozenDebt"]["notGroundedInBfoOrCco"] = [
            BASE + "GoodClass"
        ]
        self.fixture.write_manifest()
        self.fixture.validate()

        declared_parent = "\n".join(
            (
                "base:MissingParent a owl:Class ;",
                f"    rdfs:subClassOf <{BFO_PROCESS}> ;",
                '    rdfs:label "Missing Parent"@en ;',
                '    skos:definition "A Missing Parent is a Process that is used by a test."@en ;',
                '    skos:example "A declared parent."@en .',
            )
        )
        self.fixture.write_base(parent=missing_parent, extra=declared_parent)
        with self.assertRaisesRegex(
            CURATION.OntologyCurationError, "resolved or changed findings"
        ):
            self.fixture.validate()

    def test_declared_local_cycle_without_bfo_or_cco_root_is_rejected(self) -> None:
        loop_class = "\n".join(
            (
                "base:LoopClass a owl:Class ;",
                "    rdfs:subClassOf base:GoodClass ;",
                '    rdfs:label "Loop Class"@en ;',
                '    skos:definition "A Loop Class is a Good Class that is cyclic."@en ;',
                '    skos:example "A deliberately invalid cycle."@en .',
            )
        )
        self.fixture.write_base(parent=BASE + "LoopClass", extra=loop_class)
        with self.assertRaisesRegex(CURATION.OntologyCurationError, "notGroundedInBfoOrCco"):
            self.fixture.validate()

    def test_resolved_missing_annotation_debt_requires_manifest_cleanup(self) -> None:
        self.fixture.write_base(include_example=False)
        self.fixture.manifest["frozenDebt"]["missingExampleOrEditorialNote"] = [
            BASE + "GoodClass"
        ]
        self.fixture.write_manifest()
        self.fixture.validate()

        self.fixture.write_base(include_example=True)
        with self.assertRaisesRegex(
            CURATION.OntologyCurationError, "resolved or changed findings"
        ):
            self.fixture.validate()

    def test_unapproved_local_object_property_is_rejected(self) -> None:
        self.fixture.write_base(extra="base:unapprovedRelation a owl:ObjectProperty .")
        with self.assertRaisesRegex(CURATION.OntologyCurationError, "object-property"):
            self.fixture.validate()

    def test_unapproved_local_datatype_property_is_rejected(self) -> None:
        self.fixture.write_base(extra="base:unapprovedValue a owl:DatatypeProperty .")
        with self.assertRaisesRegex(CURATION.OntologyCurationError, "datatype-property"):
            self.fixture.validate()

    def test_stale_property_approval_is_rejected(self) -> None:
        self.fixture.manifest = copy.deepcopy(self.fixture.manifest)
        self.fixture.manifest["approvedLocalProperties"]["object"] = [
            BASE + "approvedButAbsent"
        ]
        self.fixture.write_manifest()
        with self.assertRaisesRegex(CURATION.OntologyCurationError, "approval list"):
            self.fixture.validate()

    def test_unallowlisted_base_import_is_rejected(self) -> None:
        self.fixture.write_base(
            extra=f"<{BASE_ONTOLOGY}> owl:imports <https://example.org/unreviewed> ."
        )
        with self.assertRaisesRegex(CURATION.OntologyCurationError, "imports differ"):
            self.fixture.validate()

    def test_unallowlisted_overlay_import_is_rejected(self) -> None:
        self.fixture.write_overlay(
            extra=f"<{OVERLAY_ONTOLOGY}> owl:imports <https://example.org/proposal> ."
        )
        with self.assertRaisesRegex(CURATION.OntologyCurationError, "imports differ"):
            self.fixture.validate()


if __name__ == "__main__":
    unittest.main()
