#!/usr/bin/env python3
from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
import warnings
from pathlib import Path

from rdflib import Dataset, Literal, Namespace, RDF, URIRef, XSD
from rdflib.plugins.sparql import prepareQuery


ROOT = Path(__file__).resolve().parents[1]
COMPILER = ROOT / "scripts" / "pipeline" / "compile-dsq-query.py"
CATALOG_PATH = ROOT / "sparql" / "query-modules" / "catalog.json"
SPEC_ROOT = ROOT / "sparql" / "query-modules" / "specs"
AUTHORITY_CATALOG_PATH = ROOT / "sparql" / "query-modules" / "authority" / "catalog.json"
AUTHORITY_SPEC_ROOT = ROOT / "sparql" / "query-modules" / "authority" / "specs"
SPEC = importlib.util.spec_from_file_location("baseballo_dsq_compiler", COMPILER)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class DsqQueryModuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.modules = MODULE.load_catalog(CATALOG_PATH)

    def load_spec(self, name: str = "hits-by-season.json") -> dict[str, object]:
        return json.loads((SPEC_ROOT / name).read_text(encoding="utf-8"))

    def test_catalog_exposes_each_current_query_index_fact_grain(self) -> None:
        contract = json.loads(
            (ROOT / "sparql" / "query-index" / "semantic-contract.json").read_text(
                encoding="utf-8"
            )
        )
        expected = {grain["name"] for grain in contract["factGrains"]}
        exposed = {module.fact_grain for module in self.modules.values()}
        self.assertEqual(expected | {"QueryIndex"}, exposed)
        self.assertEqual(len(self.modules), 15)

    def test_checked_in_specs_compile_to_parseable_scoped_sparql(self) -> None:
        paths = sorted(SPEC_ROOT.glob("*.json"))
        self.assertEqual(
            [path.name for path in paths],
            [
                "games-by-team-and-season.json",
                "hits-by-season.json",
                "plate-appearances-by-player-and-season.json",
            ],
        )
        for path in paths:
            with self.subTest(path=path.name):
                query = MODULE.compile_query(
                    json.loads(path.read_text(encoding="utf-8")),
                    self.catalog,
                    self.modules,
                )
                prepareQuery(query)
                self.assertIn("GRAPH ?indexGraph", query)
                self.assertIn(MODULE.INDEX_GRAPH_PREFIX, query)
                self.assertIn(MODULE.SOURCE_GRAPH_PREFIX, query)
                self.assertIn("module: index-scope (QueryIndex)", query)
                self.assertIn("COUNT(DISTINCT", query)

    def test_fact_to_fact_join_is_rejected_until_a_bridge_is_reviewed(self) -> None:
        spec = self.load_spec()
        spec["enrichments"] = ["plate-appearance"]
        with self.assertRaisesRegex(MODULE.ContractError, "not admitted"):
            MODULE.compile_query(spec, self.catalog, self.modules)

    def test_one_game_scope_uses_a_concrete_named_graph(self) -> None:
        graph = MODULE.INDEX_GRAPH_PREFIX + "566279"
        query = MODULE.compile_query(
            self.load_spec(), self.catalog, self.modules, index_graphs=[graph]
        )
        self.assertIn(f"GRAPH <{graph}>", query)
        self.assertNotIn("GRAPH ?indexGraph", query)
        self.assertNotIn("VALUES ?indexGraph", query)
        prepareQuery(query)

    def test_batch_scope_deduplicates_and_binds_named_graphs(self) -> None:
        first = MODULE.INDEX_GRAPH_PREFIX + "1"
        second = MODULE.INDEX_GRAPH_PREFIX + "2"
        query = MODULE.compile_query(
            self.load_spec(),
            self.catalog,
            self.modules,
            index_graphs=[first, second, first],
        )
        self.assertIn(f"VALUES ?indexGraph {{ <{first}> <{second}> }}", query)
        self.assertEqual(query.count(f"<{first}>") , 1)
        prepareQuery(query)

    def test_batch_scope_rejects_non_game_graph(self) -> None:
        with self.assertRaisesRegex(MODULE.ContractError, "Invalid query-index game graph"):
            MODULE.compile_query(
                self.load_spec(),
                self.catalog,
                self.modules,
                index_graphs=["https://w3id.org/baseball/graph/query-index/team/1"],
            )

    def test_compiled_query_preserves_additive_results_across_graph_partitions(self) -> None:
        idx = Namespace("https://w3id.org/baseball/query-index/")
        dataset = Dataset()
        graph_iris: list[str] = []
        for game_pk in ("1", "2"):
            graph_iri = MODULE.INDEX_GRAPH_PREFIX + game_pk
            graph_iris.append(graph_iri)
            graph = dataset.graph(URIRef(graph_iri))
            game = URIRef(f"https://baseballontology.org/data/game/{game_pk}")
            source = URIRef(MODULE.SOURCE_GRAPH_PREFIX + game_pk)
            index = URIRef(f"https://w3id.org/baseball/query-index-build/game/{game_pk}")
            hit = URIRef(f"https://baseballontology.org/data/game/{game_pk}/hit/1")
            graph.add((index, RDF.type, idx.QueryIndex))
            graph.add((index, idx.sourceGraph, source))
            graph.add((index, idx.indexedGame, game))
            graph.add((index, idx.contractVersion, Literal("1")))
            graph.add((game, RDF.type, idx.GameFact))
            graph.add((game, idx.season, Literal(2026)))
            graph.add((hit, RDF.type, idx.HitFact))
            graph.add((hit, idx.game, game))
            graph.add((hit, idx.plateAppearance, URIRef(f"urn:pa:{game_pk}")))
            graph.add((hit, idx.agent, URIRef(f"urn:batter:{game_pk}")))
            graph.add((hit, idx.venue, URIRef("urn:venue:1")))
            graph.add((hit, idx.hitType, URIRef("urn:hit-type:single")))

        spec = self.load_spec()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            whole = list(dataset.query(MODULE.compile_query(spec, self.catalog, self.modules)))
            first = list(
                dataset.query(
                    MODULE.compile_query(
                        spec, self.catalog, self.modules, index_graphs=[graph_iris[0]]
                    )
                )
            )
            second = list(
                dataset.query(
                    MODULE.compile_query(
                        spec, self.catalog, self.modules, index_graphs=[graph_iris[1]]
                    )
                )
            )
        self.assertEqual(len(whole), 1)
        self.assertEqual(int(whole[0].hits), int(first[0].hits) + int(second[0].hits))
        self.assertEqual(
            int(whole[0].gamesWithHits),
            int(first[0].gamesWithHits) + int(second[0].gamesWithHits),
        )

    def test_average_is_rejected_in_favor_of_additive_inputs(self) -> None:
        spec = self.load_spec()
        spec["measures"][0]["aggregate"] = "average"
        with self.assertRaisesRegex(MODULE.ContractError, "count-distinct"):
            MODULE.compile_query(spec, self.catalog, self.modules)

    def test_merge_contract_must_cover_measures_exactly(self) -> None:
        spec = self.load_spec()
        del spec["materialization"]["merge"]["hits"]
        with self.assertRaisesRegex(MODULE.ContractError, "every measure exactly"):
            MODULE.compile_query(spec, self.catalog, self.modules)

    def test_unbound_projection_is_rejected(self) -> None:
        spec = self.load_spec()
        spec["dimensions"] = ["season", "weather"]
        spec["materialization"]["dimensions"] = ["season", "weather"]
        with self.assertRaisesRegex(MODULE.ContractError, "not bound"):
            MODULE.compile_query(spec, self.catalog, self.modules)

    def test_values_iri_cannot_inject_sparql(self) -> None:
        spec = self.load_spec("games-by-team-and-season.json")
        spec["values"][0]["terms"][0]["value"] = (
            "https://w3id.org/baseball/query-index/HomeTeam> } DROP ALL #"
        )
        with self.assertRaisesRegex(MODULE.ContractError, "VALUES IRI"):
            MODULE.compile_query(spec, self.catalog, self.modules)

    def test_catalog_fails_closed_when_query_index_contract_drifts(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        catalog["semanticContract"]["textSha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "catalog.json"
            path.write_text(json.dumps(catalog), encoding="utf-8")
            with self.assertRaisesRegex(MODULE.ContractError, "hash is stale"):
                MODULE.load_catalog(path)

    def test_catalog_fails_closed_when_fragment_hash_drifts(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        catalog["modules"][0]["textSha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "catalog.json"
            path.write_text(json.dumps(catalog), encoding="utf-8")
            with self.assertRaisesRegex(MODULE.ContractError, "fragment hash is stale"):
                MODULE.load_catalog(path)

    def test_cli_writes_deterministic_compilation_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "query.rq"
            manifest_path = Path(temporary) / "manifest.json"
            graph = MODULE.INDEX_GRAPH_PREFIX + "566279"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(COMPILER),
                    "--spec",
                    str(SPEC_ROOT / "hits-by-season.json"),
                    "--index-graph",
                    graph,
                    "--output",
                    str(output),
                    "--manifest",
                    str(manifest_path),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertIn("Compiled DSQ query", completed.stdout)
            self.assertEqual(manifest["dsqId"], "hits-by-season-modular")
            self.assertEqual(manifest["indexGraphs"], [graph])
            self.assertEqual(manifest["compiledQuerySha256"], MODULE.text_sha256(output))
            self.assertEqual(
                [item["id"] for item in manifest["modules"]],
                ["index-scope", "hit", "game-season"],
            )


class AuthorityQueryModuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.modules = MODULE.load_catalog(AUTHORITY_CATALOG_PATH)

    def load_spec(self, name: str) -> dict[str, object]:
        return json.loads((AUTHORITY_SPEC_ROOT / name).read_text(encoding="utf-8"))

    def test_catalog_exposes_reusable_identity_and_attribute_nodes(self) -> None:
        self.assertEqual(len(self.modules), 18)
        self.assertTrue(
            {
                "person",
                "organization",
                "venue",
                "calendar-date-day",
                "proper-name",
                "provider-identifier",
                "height-quality",
                "mass-quality",
                "decimal-measurement",
                "batting-side-disposition",
                "throwing-side-disposition",
                "position-description",
                "venue-coordinate",
                "venue-capacity-quality",
            }.issubset(self.modules)
        )

    def test_checked_in_authority_specs_compile_to_scoped_sparql(self) -> None:
        paths = sorted(AUTHORITY_SPEC_ROOT.glob("*.json"))
        self.assertEqual(
            [path.name for path in paths],
            [
                "calendar-days.json",
                "organization-proper-names.json",
                "organization-provider-identifiers.json",
                "people-batting-sides.json",
                "people-heights.json",
                "people-masses.json",
                "people-nicknames.json",
                "people-positions.json",
                "people-proper-names.json",
                "people-provider-identifiers.json",
                "people-throwing-sides.json",
                "venue-capacities.json",
                "venue-coordinates.json",
                "venue-playing-surfaces.json",
                "venue-proper-names.json",
                "venue-provider-identifiers.json",
            ],
        )
        for path in paths:
            with self.subTest(path=path.name):
                query = MODULE.compile_query(
                    json.loads(path.read_text(encoding="utf-8")),
                    self.catalog,
                    self.modules,
                )
                prepareQuery(query)
                self.assertIn("SELECT DISTINCT ?authorityGraph", query)
                self.assertIn("GRAPH ?authorityGraph", query)
                self.assertIn("STRSTARTS(STR(?authorityGraph)", query)

    def test_proper_name_node_preserves_name_ice_and_unicode(self) -> None:
        cco = Namespace("https://www.commoncoreontologies.org/")
        graph_iri = "https://w3id.org/baseball/graph/authority/mlb-people/2026-09-03"
        dataset = Dataset()
        graph = dataset.graph(URIRef(graph_iri))
        person = URIRef("https://baseballontology.org/data/person/553993")
        name = URIRef("https://baseballontology.org/data/person/553993/name/full")
        graph.add((person, RDF.type, cco.ont00001262))
        graph.add((name, RDF.type, cco.ont00001014))
        graph.add((name, cco.ont00001916, person))
        graph.add((name, cco.ont00001765, Literal("Eugenio Suárez")))

        query = MODULE.compile_query(
            self.load_spec("people-proper-names.json"),
            self.catalog,
            self.modules,
            authority_graphs=[graph_iri],
        )
        self.assertNotIn("rdfs:label", query)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            rows = list(dataset.query(query))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].authorityGraph, URIRef(graph_iri))
        self.assertEqual(rows[0].entity, person)
        self.assertEqual(rows[0].nameICE, name)
        self.assertEqual(str(rows[0].nameText), "Eugenio Suárez")

    def test_height_node_preserves_quality_measurement_value_and_unit(self) -> None:
        cco = Namespace("https://www.commoncoreontologies.org/")
        obo = Namespace("http://purl.obolibrary.org/obo/")
        graph_iri = "https://w3id.org/baseball/graph/authority/mlb-people/2026-09-03"
        dataset = Dataset()
        graph = dataset.graph(URIRef(graph_iri))
        person = URIRef("https://baseballontology.org/data/person/1")
        quality = URIRef("https://baseballontology.org/data/person/1/quality/height")
        measurement = URIRef("https://baseballontology.org/data/person/1/measurement/height/1")
        unit = cco.ont00001677
        graph.add((person, RDF.type, cco.ont00001262))
        graph.add((quality, RDF.type, cco.ont00000967))
        graph.add((quality, obo.BFO_0000197, person))
        graph.add((measurement, RDF.type, cco.ont00001163))
        graph.add((measurement, cco.ont00001966, quality))
        graph.add((measurement, cco.ont00001769, Literal("76.0", datatype=XSD.decimal)))
        graph.add((measurement, cco.ont00001863, unit))

        query = MODULE.compile_query(
            self.load_spec("people-heights.json"),
            self.catalog,
            self.modules,
            authority_graphs=[graph_iri],
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            rows = list(dataset.query(query))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].measuredEntity, quality)
        self.assertEqual(rows[0].measurementICE, measurement)
        self.assertEqual(rows[0].measurementUnit, unit)
        self.assertEqual(rows[0].decimalValue, Literal("76.0", datatype=XSD.decimal))

    def test_venue_capacity_node_uses_the_accepted_baseballo_namespace(self) -> None:
        base = Namespace("https://baseballontology.org/")
        cco = Namespace("https://www.commoncoreontologies.org/")
        obo = Namespace("http://purl.obolibrary.org/obo/")
        graph_iri = "https://w3id.org/baseball/graph/authority/mlb-venues/2026"
        dataset = Dataset()
        graph = dataset.graph(URIRef(graph_iri))
        venue = URIRef("https://baseballontology.org/data/venue/1")
        quality = URIRef("https://baseballontology.org/data/venue/1/quality/capacity")
        measurement = URIRef("https://baseballontology.org/data/venue/1/measurement/capacity/1")
        graph.add((venue, RDF.type, base.BaseballVenue))
        graph.add((quality, RDF.type, base.SpectatorAccommodationAmount))
        graph.add((quality, obo.BFO_0000197, venue))
        graph.add((measurement, RDF.type, cco.ont00001163))
        graph.add((measurement, cco.ont00001966, quality))
        graph.add((measurement, cco.ont00001773, Literal(42000)))

        query = MODULE.compile_query(
            self.load_spec("venue-capacities.json"),
            self.catalog,
            self.modules,
            authority_graphs=[graph_iri],
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            rows = list(dataset.query(query))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].entity, venue)
        self.assertEqual(rows[0].measuredEntity, quality)
        self.assertEqual(int(rows[0].integerValue), 42000)

    def test_authority_graph_must_belong_to_selected_source(self) -> None:
        with self.assertRaisesRegex(MODULE.ContractError, "Invalid authority graph"):
            MODULE.compile_query(
                self.load_spec("people-proper-names.json"),
                self.catalog,
                self.modules,
                authority_graphs=[
                    "https://w3id.org/baseball/graph/authority/mlb-venues/2026"
                ],
            )

    def test_incompatible_enrichment_is_rejected(self) -> None:
        spec = self.load_spec("people-proper-names.json")
        spec["enrichments"] = ["venue-coordinate"]
        with self.assertRaisesRegex(MODULE.ContractError, "not admitted"):
            MODULE.compile_query(spec, self.catalog, self.modules)

    def test_authority_catalog_fails_closed_when_source_contract_drifts(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        catalog["sourceContracts"][0]["rml"]["textSha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "catalog.json"
            path.write_text(json.dumps(catalog), encoding="utf-8")
            with self.assertRaisesRegex(MODULE.ContractError, "rml hash is stale"):
                MODULE.load_catalog(path)

    def test_authority_cli_writes_source_contract_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "query.rq"
            manifest_path = Path(temporary) / "manifest.json"
            graph = "https://w3id.org/baseball/graph/authority/mlb-people/2026-09-03"
            subprocess.run(
                [
                    sys.executable,
                    str(COMPILER),
                    "--catalog",
                    str(AUTHORITY_CATALOG_PATH),
                    "--spec",
                    str(AUTHORITY_SPEC_ROOT / "people-heights.json"),
                    "--authority-graph",
                    graph,
                    "--output",
                    str(output),
                    "--manifest",
                    str(manifest_path),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["authorityGraphs"], [graph])
            self.assertEqual([item["id"] for item in manifest["sourceContracts"]], ["mlb-people"])
            self.assertEqual(
                [item["id"] for item in manifest["modules"]],
                ["person", "height-quality", "decimal-measurement"],
            )


if __name__ == "__main__":
    unittest.main()
