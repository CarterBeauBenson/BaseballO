#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "scripts" / "pipeline" / "query-serving-layer.py"
CANDIDATE_ADAPTER = ROOT / "scripts" / "pipeline" / "query-serving-candidate.py"
ACCEPTANCE = ROOT / "scripts" / "pipeline" / "verify-explorer-serving.py"
REDUCERS = json.loads((ROOT / "serving" / "advanced-query-reducers.json").read_text(encoding="utf-8"))
CATALOG = json.loads((ROOT / "sparql" / "advanced" / "advanced-query-catalog.json").read_text(encoding="utf-8"))
SPEC = importlib.util.spec_from_file_location("baseballo_serving_adapter", ADAPTER)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)
CANDIDATE_SPEC = importlib.util.spec_from_file_location(
    "baseballo_serving_candidate_adapter", CANDIDATE_ADAPTER
)
CANDIDATE_MODULE = importlib.util.module_from_spec(CANDIDATE_SPEC)
assert CANDIDATE_SPEC and CANDIDATE_SPEC.loader
CANDIDATE_SPEC.loader.exec_module(CANDIDATE_MODULE)
ACCEPTANCE_SPEC = importlib.util.spec_from_file_location("baseballo_serving_acceptance", ACCEPTANCE)
ACCEPTANCE_MODULE = importlib.util.module_from_spec(ACCEPTANCE_SPEC)
assert ACCEPTANCE_SPEC and ACCEPTANCE_SPEC.loader
ACCEPTANCE_SPEC.loader.exec_module(ACCEPTANCE_MODULE)


def literal(value: object) -> dict[str, str]:
    return {"type": "literal", "value": str(value)}


class ServingLayerTests(unittest.TestCase):
    def test_candidate_adapter_bypasses_pending_route_admission_only(self) -> None:
        contract = MODULE.load_object(MODULE.CONTRACT)
        CANDIDATE_MODULE.allow_candidate_route(
            {"id": "swing-to-result-funnel"}, contract
        )
        CANDIDATE_MODULE.allow_candidate_route(
            {"route": "options", "family": "baserunning", "dimension": "player"},
            contract,
        )
        with self.assertRaisesRegex(ValueError, "Unsupported materialized route"):
            CANDIDATE_MODULE.allow_candidate_route({"route": "unknown"}, contract)

    def test_serving_contract_admits_only_paq_and_its_required_options(self) -> None:
        contract = MODULE.load_object(MODULE.CONTRACT)
        self.assertEqual(
            MODULE.GAME_SETS,
            frozenset(contract["gameSets"]["uiSelectable"]),
        )
        self.assertEqual(contract["gameSets"]["default"], "regular_season")
        admitted_requests = [
            {"id": "plate-appearance-fingerprint"},
            {"id": "plate-appearance-fingerprint", "view": "player_averages"},
            {"route": "options", "family": "games", "dimension": "season"},
            {"route": "options", "family": "games", "dimension": "game"},
            {"route": "options", "family": "games", "dimension": "team"},
            {"route": "options", "family": "games", "dimension": "venue"},
            {"route": "options", "family": "batting", "dimension": "player"},
            {"route": "options", "family": "pitching", "dimension": "pitcher"},
        ]
        for request in admitted_requests:
            with self.subTest(request=request):
                MODULE.require_materialized_route_admission(request, contract)

        pending_contract = json.loads(json.dumps(contract))
        pending_contract["routes"]["plate-appearance-fingerprint"]["status"] = (
            "pending-end-to-end-equivalence"
        )
        with self.assertRaisesRegex(ValueError, "not admitted"):
            MODULE.require_materialized_route_admission(
                {"id": "plate-appearance-fingerprint"}, pending_contract
            )

    def test_pending_routes_are_rejected_before_serving_state_or_sql_access(self) -> None:
        pending_requests = [
            {"id": "swing-to-result-funnel"},
            {"route": "explore", "family": "batting"},
            {"route": "empty-games", "analysis": "players"},
            {
                "route": "derived",
                "numerator": "empty_games",
                "denominator": "offensive_games_played",
            },
        ]
        with tempfile.TemporaryDirectory() as temporary:
            args = SimpleNamespace(state_root=Path(temporary))
            for request in pending_requests:
                with self.subTest(request=request):
                    with self.assertRaisesRegex(ValueError, "not admitted"):
                        MODULE.query(args, request)

    def test_non_paq_options_are_rejected_before_serving_state_or_sql_access(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            args = SimpleNamespace(state_root=Path(temporary))
            with self.assertRaisesRegex(ValueError, "only for the PAQ/Good At Bat"):
                MODULE.query(
                    args,
                    {
                        "route": "options",
                        "family": "baserunning",
                        "dimension": "player",
                    },
                )

    def test_database_hash_cache_rejects_same_size_timestamp_preserving_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            database = Path(temporary) / "build.sqlite"
            cache = Path(temporary) / "database-verification-cache.json"
            database.write_bytes(b"original-database")
            expected = MODULE.sha(database)

            with patch.object(
                MODULE,
                "hash_database_stream",
                wraps=MODULE.hash_database_stream,
            ) as hasher:
                first = MODULE.verify_database(database, expected, cache)
                # The second call reloads the on-disk cache, matching a fresh
                # query-serving subprocess rather than relying on process memory.
                self.assertEqual(MODULE.verify_database(database, expected, cache), first)
                self.assertEqual(hasher.call_count, 1)
                self.assertTrue(cache.is_file())

                replacement = database.with_suffix(".replacement")
                replacement.write_bytes(b"tampered-database")
                metadata = database.stat()
                os.utime(
                    replacement,
                    ns=(metadata.st_atime_ns, metadata.st_mtime_ns),
                )
                os.replace(replacement, database)

                with self.assertRaisesRegex(ValueError, "hash does not match"):
                    MODULE.verify_database(database, expected, cache)
                self.assertEqual(hasher.call_count, 2)

    def test_database_hash_verification_rejects_invalid_pointer_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            database = Path(temporary) / "build.sqlite"
            database.write_bytes(b"database")
            with self.assertRaisesRegex(ValueError, "invalid databaseSha256"):
                MODULE.verify_database(
                    database,
                    "not-a-sha256",
                    Path(temporary) / "database-verification-cache.json",
                )

    def test_acceptance_gate_covers_every_routine_route_shape(self) -> None:
        family_dimensions = {
            "batting": {"player": {"input": "iri", "hasOptions": True}},
            "pitching": {"pitcher": {"input": "iri", "hasOptions": True}},
            "baserunning": {"player": {"input": "iri", "hasOptions": True}},
            "games": {"team": {"input": "iri", "hasOptions": True}},
        }
        catalogs = {
            "explore": {"families": {
                family: {
                    "dimensions": dimensions,
                    "metrics": {metric: {} for metric in ACCEPTANCE_MODULE.EXPLORE_PROBES[family]["metrics"]},
                }
                for family, dimensions in family_dimensions.items()
            }},
            "advanced": {"queries": [{"id": entry["id"]} for entry in CATALOG["queries"]]},
            "empty": {"analyses": {name: {} for name in (
                "players", "teams", "stretches", "pitcher_matchups", "games", "damage",
            )}},
            "derived": {"measures": {
                "empty_games": {"unit": "player-games", "grain": "player-game", "dimensions": ["player"], "evidenceUniverse": "reviewed"},
                "offensive_games_played": {"unit": "player-games", "grain": "player-game", "dimensions": ["player"], "evidenceUniverse": "reviewed"},
            }},
        }
        probes = ACCEPTANCE_MODULE.build_probes(catalogs)
        names = {probe["name"] for probe in probes}
        self.assertEqual(len(probes), 34)
        self.assertTrue({f"advanced:{entry['id']}" for entry in CATALOG["queries"]}.issubset(names))
        self.assertIn("advanced:plate-appearance-fingerprint:player-averages", names)
        self.assertIn("empty-games:damage", names)
        self.assertIn("derived:empty_games:offensive_games_played", names)
        self.assertIn("derived:offensive_games_played:empty_games", names)

    def test_acceptance_gate_rejects_fallback_and_build_drift(self) -> None:
        coverage = {key: 1 for key in ACCEPTANCE_MODULE.POSITIVE_COVERAGE}
        coverage["advancedQueries"] = len(CATALOG["queries"])
        run = ACCEPTANCE_MODULE.AcceptanceRun(len(CATALOG["queries"]), False, None)
        probe = {"name": "explore:batting", "kind": "result"}

        def payload(build: str = "build-5", layer: str = "materialized") -> dict[str, object]:
            return {
                "results": {"bindings": []},
                "meta": {
                    "layer": layer,
                    "servingBuildId": build,
                    "corpusFingerprint": "f" * 64,
                    "servingCoverage": coverage,
                    "durationMs": 0.1,
                },
            }

        run.record(probe, payload(), 1.0)
        with self.assertRaisesRegex(ACCEPTANCE_MODULE.AcceptanceError, "instead of materialized SQL"):
            run.record(probe, payload(layer="authoritative"), 1.0)
        with self.assertRaisesRegex(ACCEPTANCE_MODULE.AcceptanceError, "same immutable serving build"):
            run.record(probe, payload(build="build-6"), 1.0)

    def test_reviewed_catalog_has_reducer_and_ordering_contracts(self) -> None:
        query_ids = {entry["id"] for entry in CATALOG["queries"]}
        reducer_ids = set(REDUCERS["detailQueries"]) | set(REDUCERS["additiveQueries"])
        self.assertEqual(len(query_ids), 17)
        self.assertEqual(query_ids, reducer_ids)
        self.assertEqual(query_ids, set(REDUCERS["ordering"]))

    def test_additive_reducer_combines_games_and_uses_reviewed_sort(self) -> None:
        rows = [
            {"batter": literal("p1"), "batterLabel": literal("One"), "pitches": literal(20),
             "swings": literal(10), "contacts": literal(4), "fairBalls": literal(0),
             "foulBalls": literal(0), "foulTips": literal(0), "terminalResults": literal(0),
             "hits": literal(0), "battedOutcomes": literal(0)},
            {"batter": literal("p1"), "batterLabel": literal("One"), "pitches": literal(5),
             "swings": literal(5), "contacts": literal(3), "fairBalls": literal(0),
             "foulBalls": literal(0), "foulTips": literal(0), "terminalResults": literal(0),
             "hits": literal(0), "battedOutcomes": literal(0)},
            {"batter": literal("p2"), "batterLabel": literal("Two"), "pitches": literal(30),
             "swings": literal(5), "contacts": literal(6), "fairBalls": literal(0),
             "foulBalls": literal(0), "foulTips": literal(0), "terminalResults": literal(0),
             "hits": literal(0), "battedOutcomes": literal(0)},
        ]
        reduced = MODULE.reduce_advanced("swing-to-result-funnel", rows, REDUCERS)
        self.assertEqual(reduced[0]["batter"]["value"], "p1")
        self.assertEqual(reduced[0]["pitches"]["value"], "25")
        self.assertEqual(reduced[0]["contacts"]["value"], "7")

    def test_steal_reducer_recalculates_derived_values(self) -> None:
        rows = [
            {"player": literal("p1"), "playerLabel": literal("Runner"),
             "attempts": literal(2), "successfulSteals": literal(1), "caughtStealing": literal(1)},
            {"player": literal("p1"), "playerLabel": literal("Runner"),
             "attempts": literal(3), "successfulSteals": literal(3), "caughtStealing": literal(0)},
        ]
        reduced = MODULE.reduce_advanced("steal-attempt-efficiency", rows, REDUCERS)
        self.assertEqual(reduced[0]["attempts"]["value"], "5")
        self.assertEqual(reduced[0]["unresolvedAttempts"]["value"], "0")
        self.assertEqual(reduced[0]["successPercent"]["value"], "80.00")

    def test_routine_explorer_routes_aggregate_shared_sql_grains(self) -> None:
        connection = sqlite3.connect(":memory:")
        connection.executescript((ROOT / "serving" / "schema.sql").read_text(encoding="utf-8"))
        graph = "https://w3id.org/baseball/graph/game/1"
        game = "https://baseballontology.org/data/game/1"
        player = "https://baseballontology.org/data/player/1"
        team = "https://baseballontology.org/data/team/1"
        pitcher = "https://baseballontology.org/data/player/2"
        connection.execute("INSERT INTO game_dimension VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                           (graph, game, "1", "2026-08-01", "2026-08-01T19:00:00Z", 2026,
                            "regular_season", "https://baseballontology.org/data/venue/1", "Park",
                            team, "Home", "https://baseballontology.org/data/team/2", "Away"))
        connection.executemany("INSERT INTO batting_result_fact VALUES (?,?,?,?,?,?,?,?)", [
            (graph, "result/1", "pa/1", player, "Batter", team, "Home", "single"),
            (graph, "result/2", "pa/2", player, "Batter", team, "Home", "strikeout"),
        ])
        connection.execute("INSERT INTO pitch_fact VALUES (?,?,?,?,?,?,?,?)",
                           (graph, "pitch/1", "pa/1", pitcher, "Pitcher", team, "Home", "B"))
        connection.execute("INSERT INTO runner_event_fact VALUES (?,?,?,?,?,?,?,?,?)",
                           (graph, "runner/1", player, "Batter", team, "Home", "advance", "https://baseballontology.org/RunProcess", None))
        connection.execute("INSERT INTO assignment_fact VALUES (?,?,?,?,?)",
                           (graph, "role/1", "home", team, "Home"))
        connection.execute("INSERT INTO empty_player_game_fact VALUES (?,?,?,?,?,?,?,?)",
                           (graph, player, "Batter", team, "Home", pitcher, "Pitcher", 0))
        build = ("build", "f" * 64, "validated", 17, 100, 2, 1, 1, 1, 1, 0)
        scope = {"gameSet": "regular_season", "startDate": "2026-08-01", "endDate": "2026-08-01"}
        batting = MODULE.query_explore(connection, {
            "route": "explore", "family": "batting", "dimensions": ["player"],
            "metrics": ["hits", "plate_appearances"], "limit": 250,
        }, build, dict(scope), time.perf_counter())
        self.assertEqual(batting["results"]["bindings"][0]["hits"]["value"], "1")
        self.assertEqual(batting["results"]["bindings"][0]["plateAppearances"]["value"], "2")
        derived = MODULE.query_derived(connection, {
            "route": "derived", "numerator": "empty_games", "denominator": "offensive_games_played",
        }, build, dict(scope), time.perf_counter())
        self.assertEqual(derived["results"]["bindings"][0]["derivedValue"]["value"], "0.0")
        connection.close()


if __name__ == "__main__":
    unittest.main()
