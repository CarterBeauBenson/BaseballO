#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
MATERIALIZER = ROOT / "scripts" / "pipeline" / "materialize-serving-layer.py"
SPEC = importlib.util.spec_from_file_location("baseballo_serving_materializer", MATERIALIZER)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)

A573 = "a573269199d575f513a6481609dd101fd26da113ea8c3daef0b7daae35543629"
B966 = "b966f574263bf0be0e7925e99d4b49175a7056d469b664b7fc5044bda86a16ea"
V1_SEMANTIC = "6955ed9a27854f8e25dded72d13ab845b82d532d78578c6dc7ea8ac77a5abab4"


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def write_json(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="\n")


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_promotion(
    state: Path,
    game_pk: str,
    contract_sha256: str = A573,
    marker_name: str = "promotion.json",
    promoted_at: str = "2026-08-01T05:00:00Z",
    semantic_contract: bool = False,
) -> Path:
    graph = f"https://w3id.org/baseball/graph/game/{game_pk}"
    index_graph = f"https://w3id.org/baseball/graph/query-index/game/{game_pk}"
    raw_sha256 = digest(f"raw-{game_pk}")
    output_sha256 = digest(f"rdf-{game_pk}")
    manifests = state / "pipeline" / "manifests"
    rml_path = manifests / f"game-{game_pk}-rml.json"
    index_path = manifests / f"game-{game_pk}-query-index.json"
    index_artifact = state / "pipeline" / "query-index" / f"game-{game_pk}.nt"
    index_artifact.parent.mkdir(parents=True, exist_ok=True)
    index_artifact.write_bytes(f"index-{game_pk}\n".encode("utf-8"))
    write_json(
        rml_path,
        {
            "gamePk": game_pk,
            "graphIri": graph,
            "inputSha256": raw_sha256,
            "outputSha256": output_sha256,
            "shaclStatus": "validated",
        },
    )
    index_manifest: dict[str, object] = {
        "artifactType": "baseball-query-index-build",
        "contractVersion": 1,
        "gamePk": game_pk,
        "sourceGraph": graph,
        "indexGraph": index_graph,
        "indexResource": f"https://w3id.org/baseball/query-index-build/game/{game_pk}",
        "contractSha256": contract_sha256,
        "sourceRdfSha256": output_sha256,
        "sourceTripleCount": 10,
        "indexPath": str(index_artifact.resolve()),
        "indexSha256": file_sha(index_artifact),
        "indexTripleCount": 4,
    }
    if semantic_contract:
        semantic = json.loads(MODULE.QUERY_INDEX_SEMANTIC_CONTRACT.read_text(encoding="utf-8"))
        index_manifest.update(
            {
                "semanticContractId": semantic["semanticContractId"],
                "semanticContractPath": "sparql/query-index/semantic-contract.json",
                "semanticContractSha256": file_sha(MODULE.QUERY_INDEX_SEMANTIC_CONTRACT),
                "implementationSha256": contract_sha256,
                "implementationFingerprintAlgorithm": "query-index-generation-file-set-v1",
            }
        )
    write_json(index_path, index_manifest)
    marker_path = (
        state
        / "pipeline"
        / "evidence"
        / "nifi"
        / "game-promotion"
        / game_pk
        / marker_name
    )
    write_json(
        marker_path,
        {
            "artifactType": "baseball-nifi-game-promotion",
            "contractVersion": 1,
            "pipelineRunId": f"run-{game_pk}",
            "gamePk": game_pk,
            "promotedAtUtc": promoted_at,
            "rawSha256": raw_sha256,
            "authoritativeGraph": graph,
            "authoritativeTripleCount": 10,
            "queryIndexGraph": index_graph,
            "queryIndexTripleCount": 4,
            "rmlManifest": str(rml_path.resolve()),
            "rmlManifestSha256": file_sha(rml_path),
            "queryIndexManifest": str(index_path.resolve()),
            "queryIndexManifestSha256": file_sha(index_path),
        },
    )
    return marker_path


def term(value: str, kind: str = "uri") -> dict[str, str]:
    return {"type": kind, "value": value}


def dimension(
    game_pk: str, rdf_game_set: str | None = None
) -> dict[str, dict[str, str]]:
    value = {
        "graph": term(f"https://w3id.org/baseball/graph/game/{game_pk}"),
        "game": term(f"https://baseballontology.org/data/game/{game_pk}"),
        "start": term("2026-08-01T19:00:00Z", "literal"),
    }
    if rdf_game_set is not None:
        value["rdfGameSet"] = term(rdf_game_set, "literal")
    return value


def live_pair(game_pk: str, source_count: int = 10, index_count: int = 4) -> dict[str, dict[str, str]]:
    return {
        "sourceGraph": term(f"https://w3id.org/baseball/graph/game/{game_pk}"),
        "indexGraph": term(f"https://w3id.org/baseball/graph/query-index/game/{game_pk}"),
        "game": term(f"https://baseballontology.org/data/game/{game_pk}"),
        "indexResource": term(f"https://w3id.org/baseball/query-index-build/game/{game_pk}"),
        "sourceCount": term(str(source_count), "literal"),
        "indexCount": term(str(index_count), "literal"),
    }


def result(bindings: list[dict[str, object]], variables: list[str] | None = None) -> dict[str, object]:
    return {"head": {"vars": variables or []}, "results": {"bindings": bindings}}


class ServingMaterializerTests(unittest.TestCase):
    def test_baserunning_grain_correlates_stolen_base_through_the_resolution_record(self) -> None:
        source = MODULE.EXPLORE_GRAIN_QUERIES["baserunning"].read_text(encoding="utf-8")

        self.assertIn("idx:derivedFrom ?record", source)
        self.assertIn("?record a base:BaseballEventRecord", source)
        self.assertIn("cco:ont00001808 ?resolution", source)
        self.assertIn("?record cco:ont00001808 ?stolenBase", source)
        self.assertNotIn(
            "OPTIONAL {\n      ?stolenBase a base:StolenBaseProcess",
            source,
        )

    def test_per_game_query_uses_exact_named_graphs_and_restores_projected_scope(self) -> None:
        graph = f"{MODULE.GRAPH_PREFIX}822687"
        source = MODULE.EXPLORE_GRAIN_QUERIES["pitching"].read_text(encoding="utf-8")

        query = MODULE.bounded_query(source, graph)

        self.assertNotIn("GRAPH ?graph", query)
        self.assertNotIn("GRAPH ?indexGraph", query)
        self.assertNotIn(MODULE.GRAPH_GUARD, query)
        self.assertNotIn(MODULE.INDEX_GRAPH_GUARD, query)
        self.assertIn(f"GRAPH <{graph}>", query)
        self.assertIn(
            "GRAPH <https://w3id.org/baseball/graph/query-index/game/822687>",
            query,
        )
        self.assertIn(f"idx:sourceGraph <{graph}>", query)

        payload = result([{}], ["graph", "indexGraph", "game"])
        restored = MODULE.restore_scoped_graph_bindings(payload, graph)
        binding = restored["results"]["bindings"][0]
        self.assertEqual(binding["graph"], term(graph))
        self.assertEqual(
            binding["indexGraph"],
            term("https://w3id.org/baseball/graph/query-index/game/822687"),
        )

    def test_mlb_game_types_map_to_five_disjoint_serving_pools(self) -> None:
        expected = {
            "R": "regular_season",
            "S": "preseason",
            "E": "exhibition",
            "F": "postseason",
            "D": "postseason",
            "L": "postseason",
            "W": "postseason",
            "C": "postseason",
            "P": "postseason",
            "A": "all_star",
        }
        self.assertEqual(
            {code: MODULE.provenance_game_set(code) for code in expected},
            expected,
        )
        with self.assertRaisesRegex(ValueError, "Unsupported or missing MLB game type"):
            MODULE.provenance_game_set("unknown")

    def test_official_metadata_reads_compact_batch_and_rml_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            write_json(
                state / "pipeline" / "control" / "mlb-game" / "batches" / "batch.json",
                {
                    "games": [
                        {
                            "gamePk": "1",
                            "officialDate": "2026-03-03",
                            "gameType": "E",
                        }
                    ]
                },
            )
            write_json(
                state / "pipeline" / "manifests" / "game-2-rml.json",
                {
                    "gamePk": "2",
                    "officialDate": "2026-03-04",
                    "gameType": "S",
                },
            )

            metadata = MODULE.official_metadata(state)

            self.assertEqual(
                metadata["1"],
                {"officialDate": "2026-03-03", "gameSet": "exhibition"},
            )
            self.assertEqual(
                metadata["2"],
                {"officialDate": "2026-03-04", "gameSet": "preseason"},
            )

    def test_build_retention_keeps_candidate_prior_current_and_newest_rollback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = Path(temporary) / "serving"
            builds = store / "builds"
            builds.mkdir(parents=True)
            paths = [builds / f"{name}.sqlite" for name in ("oldest", "rollback", "current", "candidate")]
            for order, path in enumerate(paths, start=1):
                path.write_bytes(path.name.encode("utf-8"))
                os.utime(path, ns=(order, order))
            write_json(
                store / "current.json",
                {"databasePath": str(paths[2].resolve())},
            )

            result = MODULE.enforce_build_retention(store, paths[3], 3)

            self.assertFalse(paths[0].exists())
            self.assertTrue(all(path.exists() for path in paths[1:]))
            self.assertEqual(result["removedBuildCount"], 1)
            self.assertEqual(result["retainedBuildCount"], 3)
            self.assertEqual(result["priorPointerStatus"], "protected")

    def test_inventory_selects_newest_marker_and_accepts_fixed_legacy_bridge(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            make_promotion(state, "1", A573, "old.json", "2026-08-01T05:00:00Z")
            newest = make_promotion(state, "1", A573, "new.json", "2026-08-02T05:00:00Z")
            make_promotion(state, "2", B966)

            inventory = MODULE.promotion_inventory(state.resolve())

            self.assertEqual(inventory["gameCount"], 2)
            self.assertEqual(inventory["supersededManifestCount"], 1)
            self.assertEqual(Path(inventory["games"]["1"]["promotionManifest"]), newest.resolve())
            self.assertEqual(inventory["queryIndexImplementationSha256Set"], [A573, B966])
            routing = json.loads(MODULE.QUERY_INDEX_ROUTING.read_text(encoding="utf-8"))
            semantic = json.loads(
                MODULE.QUERY_INDEX_SEMANTIC_CONTRACT.read_text(encoding="utf-8")
            )
            self.assertEqual(
                inventory["queryIndexSemanticContractId"],
                semantic["semanticContractId"],
            )
            self.assertEqual(
                inventory["queryIndexSemanticContractSha256"],
                file_sha(MODULE.QUERY_INDEX_SEMANTIC_CONTRACT),
            )
            self.assertEqual(
                inventory["legacyQueryIndexImplementationBridgeSha256Set"],
                sorted(routing["legacyManifestBridge"]["fixedImplementationSha256"]),
            )

    def test_inventory_accepts_new_semantic_manifest_without_admitting_implementation_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            unreviewed_implementation = digest("new-generator-implementation")
            make_promotion(
                state,
                "1",
                unreviewed_implementation,
                semantic_contract=True,
            )

            inventory = MODULE.promotion_inventory(state.resolve())

            self.assertEqual(
                inventory["games"]["1"]["queryIndexAdmissionMode"],
                "semantic-contract",
            )
            self.assertEqual(
                inventory["queryIndexImplementationSha256Set"],
                [unreviewed_implementation],
            )

    def test_inventory_accepts_reviewed_backward_compatible_v1_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            marker = make_promotion(
                state,
                "1",
                digest("v1-generator-implementation"),
                semantic_contract=True,
            )
            index_path = state / "pipeline" / "manifests" / "game-1-query-index.json"
            index = json.loads(index_path.read_text(encoding="utf-8"))
            index["semanticContractId"] = "baseball-query-index-v1"
            index["semanticContractSha256"] = V1_SEMANTIC
            write_json(index_path, index)
            marker_value = json.loads(marker.read_text(encoding="utf-8"))
            marker_value["queryIndexManifestSha256"] = file_sha(index_path)
            write_json(marker, marker_value)

            inventory = MODULE.promotion_inventory(state.resolve())

            self.assertEqual(
                inventory["games"]["1"]["queryIndexAdmissionMode"],
                "compatible-semantic-contract",
            )

    def test_inventory_keeps_promoted_pair_while_replacement_rml_is_staged(self) -> None:
        for shacl_status in ("deferred-to-nifi", "validated"):
            with self.subTest(shacl_status=shacl_status), tempfile.TemporaryDirectory() as temporary:
                state = Path(temporary)
                marker = make_promotion(state, "1", A573)
                promoted_inventory = MODULE.promotion_inventory(state.resolve())
                marker_value = json.loads(marker.read_text(encoding="utf-8"))
                index_path = state / "pipeline" / "manifests" / "game-1-query-index.json"
                index = json.loads(index_path.read_text(encoding="utf-8"))
                staged_input = (
                    state / "pipeline" / "transient" / "mlb-game" / "game-1-abcd-1234.json"
                )
                staged_output = state / "pipeline" / "rdf" / "game-1.ttl"
                staged_input.parent.mkdir(parents=True, exist_ok=True)
                staged_output.parent.mkdir(parents=True, exist_ok=True)
                staged_input.write_bytes(b"replacement payload\n")
                staged_output.write_bytes(b"replacement RDF\n")
                rml_path = state / "pipeline" / "manifests" / "game-1-rml.json"
                write_json(
                    rml_path,
                    {
                        "gamePk": "1",
                        "graphIri": "https://w3id.org/baseball/graph/game/1",
                        "inputPath": str(staged_input.resolve()),
                        "inputSha256": file_sha(staged_input),
                        "outputPath": str(staged_output.resolve()),
                        "outputSha256": file_sha(staged_output),
                        "shaclStatus": shacl_status,
                    },
                )

                inventory = MODULE.promotion_inventory(state.resolve())

                game = inventory["games"]["1"]
                self.assertEqual(
                    game["rmlManifestAdmissionMode"],
                    "pending-staging-over-current-promotion",
                )
                self.assertEqual(game["rmlManifestSha256"], marker_value["rmlManifestSha256"])
                self.assertEqual(game["authoritativeRdfSha256"], index["sourceRdfSha256"])
                self.assertEqual(inventory["fingerprint"], promoted_inventory["fingerprint"])

    def test_inventory_does_not_admit_staged_rml_when_promoted_index_manifest_changed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            make_promotion(state, "1", A573)
            staged_input = (
                state / "pipeline" / "transient" / "mlb-game" / "game-1-abcd-1234.json"
            )
            staged_output = state / "pipeline" / "rdf" / "game-1.ttl"
            staged_input.parent.mkdir(parents=True, exist_ok=True)
            staged_output.parent.mkdir(parents=True, exist_ok=True)
            staged_input.write_bytes(b"replacement payload\n")
            staged_output.write_bytes(b"replacement RDF\n")
            write_json(
                state / "pipeline" / "manifests" / "game-1-rml.json",
                {
                    "gamePk": "1",
                    "graphIri": "https://w3id.org/baseball/graph/game/1",
                    "inputPath": str(staged_input.resolve()),
                    "inputSha256": file_sha(staged_input),
                    "outputPath": str(staged_output.resolve()),
                    "outputSha256": file_sha(staged_output),
                    "shaclStatus": "validated",
                },
            )
            index_path = state / "pipeline" / "manifests" / "game-1-query-index.json"
            index = json.loads(index_path.read_text(encoding="utf-8"))
            index["sourceTripleCount"] = 11
            write_json(index_path, index)

            with self.assertRaisesRegex(ValueError, "query-index manifest hash mismatch"):
                MODULE.promotion_inventory(state.resolve())

    def test_inventory_does_not_fall_back_when_newest_marker_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            old = make_promotion(state, "1", A573, "old.json", "2026-08-01T05:00:00Z")
            invalid_new = old.parent / "new.json"
            invalid_value = json.loads(old.read_text(encoding="utf-8"))
            invalid_value["promotedAtUtc"] = "2026-08-02T05:00:00Z"
            invalid_value["rmlManifestSha256"] = "f" * 64
            write_json(invalid_new, invalid_value)

            with self.assertRaisesRegex(ValueError, "Newest promotion evidence is invalid"):
                MODULE.promotion_inventory(state.resolve())

    def test_inventory_rejects_unknown_hash_and_unsupported_index_contract_version(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            make_promotion(state, "1", digest("unknown-query-index-contract"))
            with self.assertRaisesRegex(ValueError, "not in the fixed reviewed bridge"):
                MODULE.promotion_inventory(state.resolve())

        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            marker = make_promotion(state, "1", A573)
            index_path = state / "pipeline" / "manifests" / "game-1-query-index.json"
            index = json.loads(index_path.read_text(encoding="utf-8"))
            index["contractVersion"] = 2
            write_json(index_path, index)
            marker_value = json.loads(marker.read_text(encoding="utf-8"))
            marker_value["queryIndexManifestSha256"] = file_sha(index_path)
            write_json(marker, marker_value)
            with self.assertRaisesRegex(ValueError, "contractVersion is not supported"):
                MODULE.promotion_inventory(state.resolve())

    def test_inventory_rejects_partial_semantic_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            marker = make_promotion(state, "1")
            index_path = state / "pipeline" / "manifests" / "game-1-query-index.json"
            index = json.loads(index_path.read_text(encoding="utf-8"))
            index["semanticContractId"] = "baseball-query-index-v1"
            write_json(index_path, index)
            marker_value = json.loads(marker.read_text(encoding="utf-8"))
            marker_value["queryIndexManifestSha256"] = file_sha(index_path)
            write_json(marker, marker_value)

            with self.assertRaisesRegex(ValueError, "partial semantic-contract identity"):
                MODULE.promotion_inventory(state.resolve())

    def test_inventory_rejects_manifest_hash_and_count_relationship_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            marker = make_promotion(state, "1")
            rml_path = state / "pipeline" / "manifests" / "game-1-rml.json"
            rml = json.loads(rml_path.read_text(encoding="utf-8"))
            rml["outputSha256"] = digest("tampered")
            write_json(rml_path, rml)
            with self.assertRaisesRegex(ValueError, "RML manifest hash mismatch"):
                MODULE.promotion_inventory(state.resolve())

            marker_value = json.loads(marker.read_text(encoding="utf-8"))
            marker_value["rmlManifestSha256"] = file_sha(rml_path)
            write_json(marker, marker_value)
            index_path = state / "pipeline" / "manifests" / "game-1-query-index.json"
            index = json.loads(index_path.read_text(encoding="utf-8"))
            index["sourceRdfSha256"] = rml["outputSha256"]
            index["sourceTripleCount"] = 11
            write_json(index_path, index)
            marker_value["queryIndexManifestSha256"] = file_sha(index_path)
            write_json(marker, marker_value)
            with self.assertRaisesRegex(ValueError, "triple count differs"):
                MODULE.promotion_inventory(state.resolve())

    def test_live_snapshot_rejects_unpromoted_missing_and_stale_graph_pairs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            make_promotion(state, "1")
            inventory = MODULE.promotion_inventory(state.resolve())
            cases = (
                (
                    [
                        result([dimension("1"), dimension("2")]),
                        result([live_pair("1")]),
                        result([live_pair("1")]),
                    ],
                    "without valid promotion evidence",
                ),
                ([result([]), result([live_pair("1")]), result([live_pair("1")])], "no authoritative game dimension"),
                (
                    [
                        result([dimension("1")]),
                        result([live_pair("1", source_count=11)]),
                        result([live_pair("1")]),
                    ],
                    "triple count differs",
                ),
            )
            for responses, message in cases:
                with self.subTest(message=message), patch.object(MODULE, "sparql", side_effect=responses):
                    with self.assertRaisesRegex(ValueError, message):
                        MODULE.live_graph_state("offline", 1, inventory)

    def test_live_graph_state_preflight_batches_all_promoted_graphs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            for game_pk in ("1", "2", "3"):
                make_promotion(state, game_pk)
            inventory = MODULE.promotion_inventory(state.resolve())
            requested_batches: list[tuple[str, ...]] = []

            def offline_sparql(_endpoint: str, query: str, _timeout: int) -> dict[str, object]:
                graph_ids = tuple(
                    game_pk
                    for game_pk in ("1", "2", "3")
                    if f"<{MODULE.GRAPH_PREFIX}{game_pk}>" in query
                )
                requested_batches.append(graph_ids)
                if "?rdfGameSet ?venue ?venueLabel" in query:
                    return result([dimension(game_pk) for game_pk in graph_ids])
                if "COUNT(?sourceObject)" in query:
                    return result([live_pair(game_pk) for game_pk in graph_ids])
                if "COUNT(?indexObject)" in query:
                    return result([live_pair(game_pk) for game_pk in graph_ids])
                raise AssertionError("unexpected preflight query")

            with (
                patch.object(MODULE, "LIVE_PREFLIGHT_BATCH_SIZE", 2),
                patch.object(MODULE, "sparql", side_effect=offline_sparql),
            ):
                live = MODULE.live_graph_state("offline", 1, inventory)

            self.assertEqual(len(live["dimensions"]), 3)
            self.assertEqual(len(live["graphStates"]), 3)
            self.assertEqual(
                requested_batches,
                [("1", "2"), ("1", "2"), ("1", "2"), ("3",), ("3",), ("3",)],
            )

    def test_corpus_snapshot_rechecks_inventory_around_live_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            make_promotion(state, "1", marker_name="old.json")

            def mutate_inventory(*_args: object) -> dict[str, object]:
                make_promotion(
                    state,
                    "1",
                    marker_name="new.json",
                    promoted_at="2026-08-02T05:00:00Z",
                )
                return {"fingerprint": "a" * 64, "dimensions": [], "graphStates": []}

            with patch.object(MODULE, "live_graph_state", side_effect=mutate_inventory):
                with self.assertRaisesRegex(RuntimeError, "Promotion inventory changed"):
                    MODULE.corpus_snapshot(state.resolve(), "offline", 1)

    def test_build_emits_integrity_evidence_without_equivalence_claim(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            make_promotion(state, "1", B966)
            def offline_sparql(_endpoint: str, query: str, _timeout: int) -> dict[str, object]:
                if "?rdfGameSet ?venue ?venueLabel" in query:
                    return result([dimension("1")])
                if "COUNT(?sourceObject)" in query or "COUNT(?indexObject)" in query:
                    return result([live_pair("1")])
                return result([])

            args = argparse.Namespace(
                state_root=state,
                endpoint="offline",
                timeout=1,
                max_games=None,
                no_promote=True,
            )
            with (
                patch.object(MODULE, "sparql", side_effect=offline_sparql),
                patch.object(
                    MODULE,
                    "official_metadata",
                    return_value={"1": {"gameSet": "regular_season"}},
                ),
            ):
                evidence = MODULE.build(args)

            self.assertEqual(evidence["status"], "validated")
            self.assertEqual(evidence["evidenceSchemaVersion"], 2)
            self.assertIn("integrity", evidence)
            self.assertNotIn("equivalence", evidence)
            preservation = evidence["integrity"]["sourceRowPreservation"]
            self.assertEqual(preservation["game_dimension"]["sourceRowCount"], 1)
            self.assertTrue(all(proof["matches"] for proof in preservation.values()))
            self.assertEqual(
                evidence["sourceCorpusIntegrity"]["queryIndexImplementationSha256Set"],
                [B966],
            )
            self.assertEqual(
                evidence["sourceCorpusIntegrity"]["queryIndexSemanticContractId"],
                "baseball-query-index-v2",
            )
            self.assertEqual(evidence["sourceCorpusIntegrity"]["validatedPromotionGameCount"], 1)

    def test_build_fails_closed_without_game_set_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            make_promotion(state, "1", B966)
            def offline_sparql(_endpoint: str, query: str, _timeout: int) -> dict[str, object]:
                if "?rdfGameSet ?venue ?venueLabel" in query:
                    return result([dimension("1")])
                if "COUNT(?sourceObject)" in query or "COUNT(?indexObject)" in query:
                    return result([live_pair("1")])
                return result([])

            args = argparse.Namespace(
                state_root=state,
                endpoint="offline",
                timeout=1,
                max_games=None,
                no_promote=True,
            )
            with (
                patch.object(MODULE, "sparql", side_effect=offline_sparql),
                patch.object(MODULE, "official_metadata", return_value={}),
            ):
                with self.assertRaisesRegex(ValueError, "No supported persistent game-set provenance"):
                    MODULE.build(args)

    def test_build_uses_authoritative_rdf_game_set_when_compact_provenance_predates_it(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            make_promotion(state, "1", B966)
            def offline_sparql(_endpoint: str, query: str, _timeout: int) -> dict[str, object]:
                if "?rdfGameSet ?venue ?venueLabel" in query:
                    return result([dimension("1", "preseason")])
                if "COUNT(?sourceObject)" in query or "COUNT(?indexObject)" in query:
                    return result([live_pair("1")])
                return result([])

            args = argparse.Namespace(
                state_root=state,
                endpoint="offline",
                timeout=1,
                max_games=None,
                no_promote=True,
            )
            with (
                patch.object(MODULE, "sparql", side_effect=offline_sparql),
                patch.object(MODULE, "official_metadata", return_value={}),
            ):
                evidence = MODULE.build(args)

            self.assertEqual(evidence["status"], "validated")

    def test_second_live_snapshot_drift_preserves_existing_pointer(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            make_promotion(state, "1")
            pointer = state / "serving" / "current.json"
            write_json(pointer, {"artifactType": "prior-pointer", "buildId": "prior"})
            pointer_before = pointer.read_bytes()
            dimension_calls = 0

            def drifting_sparql(_endpoint: str, query: str, _timeout: int) -> dict[str, object]:
                nonlocal dimension_calls
                if "?rdfGameSet ?venue ?venueLabel" in query:
                    dimension_calls += 1
                    return result([dimension("1")]) if dimension_calls == 1 else result([])
                if "COUNT(?sourceObject)" in query or "COUNT(?indexObject)" in query:
                    return result([live_pair("1")])
                return result([])

            args = argparse.Namespace(
                state_root=state,
                endpoint="offline",
                timeout=1,
                max_games=None,
                no_promote=False,
            )
            with (
                patch.object(MODULE, "sparql", side_effect=drifting_sparql),
                patch.object(
                    MODULE,
                    "official_metadata",
                    return_value={"1": {"gameSet": "regular_season"}},
                ),
            ):
                with self.assertRaisesRegex(ValueError, "no authoritative game dimension"):
                    MODULE.build(args)

            self.assertEqual(dimension_calls, 2)
            self.assertEqual(pointer.read_bytes(), pointer_before)


if __name__ == "__main__":
    unittest.main()
