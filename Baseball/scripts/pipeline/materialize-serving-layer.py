#!/usr/bin/env python3
"""Build, validate, benchmark, and atomically promote the derived SQL store."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import sqlite3
import statistics
import tempfile
import time
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PROMOTION_INVENTORY_MODULE = ROOT / "scripts" / "pipeline" / "game_promotion_inventory.py"
_promotion_spec = importlib.util.spec_from_file_location(
    "baseballo_game_promotion_inventory", PROMOTION_INVENTORY_MODULE
)
if _promotion_spec is None or _promotion_spec.loader is None:
    raise RuntimeError("Cannot load the source-neutral game-promotion inventory module")
_promotion_inventory = importlib.util.module_from_spec(_promotion_spec)
_promotion_spec.loader.exec_module(_promotion_inventory)
SERVING_ROOT = ROOT / "serving"
SCHEMA = SERVING_ROOT / "schema.sql"
CONTRACT = SERVING_ROOT / "contract.json"
QUALITY_SPEC = SERVING_ROOT / "plate-appearance-quality-v1.json"
MATERIALIZER = Path(__file__).resolve()
MAPPING = ROOT / "sources" / "mlb-game" / "mapping" / "mlb-game.rml.ttl"
VALIDATOR = ROOT / "scripts" / "pipeline" / "query-serving-layer.py"
GOOD_AT_BAT_QUERY = ROOT / "sparql" / "advanced" / "plate-appearance-fingerprint.rq"
ADVANCED_CATALOG = ROOT / "sparql" / "advanced" / "advanced-query-catalog.json"
ADVANCED_REDUCERS = SERVING_ROOT / "advanced-query-reducers.json"
GAME_DIMENSION_QUERY = ROOT / "sparql" / "serving" / "game-dimension.rq"
EXPLORE_GRAIN_QUERIES = {
    "batting": ROOT / "sparql" / "serving" / "explore-batting-grain.rq",
    "pitching": ROOT / "sparql" / "serving" / "explore-pitching-grain.rq",
    "baserunning": ROOT / "sparql" / "serving" / "explore-baserunning-grain.rq",
    "assignments": ROOT / "sparql" / "serving" / "explore-assignment-grain.rq",
    "damage": ROOT / "sparql" / "serving" / "empty-damage-opportunity-grain.rq",
}
SERVING_QUERY_FILES = {**EXPLORE_GRAIN_QUERIES, "dimensions": GAME_DIMENSION_QUERY}
GRAPH_PREFIX = "https://w3id.org/baseball/graph/game/"
INDEX_GRAPH_PREFIX = "https://w3id.org/baseball/graph/query-index/game/"
GAME_IRI_PREFIX = "https://baseballontology.org/data/game/"
INDEX_RESOURCE_PREFIX = "https://w3id.org/baseball/query-index-build/game/"
GRAPH_GUARD = f'FILTER(STRSTARTS(STR(?graph), "{GRAPH_PREFIX}"))'
SHA256_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")
QUERY_INDEX_ROUTING = ROOT / "sparql" / "query-index" / "operational-query-routing.json"
QUERY_INDEX_SEMANTIC_CONTRACT = ROOT / "sparql" / "query-index" / "semantic-contract.json"
SUPPORTED_QUERY_INDEX_CONTRACT_VERSION = 1
GAME_SET_BY_MLB_GAME_TYPE = {
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
PERSISTENT_GAME_SETS = frozenset({*GAME_SET_BY_MLB_GAME_TYPE.values(), "fixture"})

INTEGER_FIELDS = {
    "wasHit", "pitches", "swings", "bunts", "contacts", "balls", "strikes",
    "fouls", "foulTips", "runnerRuns", "runnerOuts", "safeResolutions",
    "positiveOutcome", "productiveOtherRunner", "grindScore",
    "goodAtBatEvidenceCount", "goodAtBat",
}
FLOAT_FIELDS = {
    "durationMinutes", "outcomeRating", "grindRating", "situationalRating",
    "plateAppearanceQuality",
}
COLUMNS = [
    ("plateAppearance", "plate_appearance_iri"), ("game", "game_iri"),
    ("batter", "batter_iri"), ("batterLabel", "batter_label"),
    ("pitcher", "pitcher_iri"), ("pitcherLabel", "pitcher_label"),
    ("outcome", "outcome"), ("wasHit", "was_hit"), ("hitType", "hit_type"),
    ("startTime", "start_time"), ("endTime", "end_time"), ("duration", "duration"),
    ("durationMinutes", "duration_minutes"), ("pitches", "pitches"),
    ("swings", "swings"), ("bunts", "bunts"), ("contacts", "contacts"),
    ("balls", "balls"), ("strikes", "strikes"), ("fouls", "fouls"),
    ("foulTips", "foul_tips"), ("runnerRuns", "runner_runs"),
    ("runnerOuts", "runner_outs"), ("safeResolutions", "safe_resolutions"),
    ("positiveOutcome", "positive_outcome"),
    ("productiveOtherRunner", "productive_other_runner"),
    ("grindScore", "grind_score"), ("outcomeRating", "outcome_rating"),
    ("grindRating", "grind_rating"),
    ("situationalRating", "situational_rating"),
    ("plateAppearanceQuality", "plate_appearance_quality"),
    ("plateAppearanceQualityBand", "plate_appearance_quality_band"),
    ("plateAppearanceQualityVersion", "plate_appearance_quality_version"),
    ("goodAtBatEvidenceCount", "good_at_bat_evidence_count"),
    ("goodAtBat", "good_at_bat"),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def advanced_query_set_sha256(catalog: dict[str, Any]) -> str:
    digest = hashlib.sha256()
    for entry in sorted(catalog["queries"], key=lambda item: item["id"]):
        path = ROOT / entry["path"]
        digest.update(entry["id"].encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def file_set_sha256(paths: dict[str, Path]) -> str:
    digest = hashlib.sha256()
    for name, path in sorted(paths.items()):
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", delete=False, dir=path.parent) as output:
        json.dump(value, output, indent=2, ensure_ascii=False)
        output.write("\n")
        temporary = Path(output.name)
    os.replace(temporary, path)


def enforce_build_retention(
    store_root: Path, candidate: Path, retain_builds: int
) -> dict[str, Any]:
    if retain_builds < 2:
        raise ValueError("Serving retention must keep at least the new and prior current build")
    builds_root = (store_root / "builds").resolve()
    candidate = candidate.resolve()
    if candidate.parent != builds_root or not candidate.is_file():
        raise ValueError("Serving retention candidate is outside the build directory")

    protected = {candidate}
    pointer_path = store_root / "current.json"
    prior_pointer_status = "absent"
    if pointer_path.is_file():
        try:
            pointer = json_object(pointer_path)
            current = Path(str(pointer.get("databasePath", ""))).resolve()
            if current.parent == builds_root and current.is_file():
                protected.add(current)
                prior_pointer_status = "protected"
            else:
                prior_pointer_status = "invalid-path"
        except (OSError, ValueError, TypeError):
            prior_pointer_status = "invalid-json"

    builds = sorted(
        (path.resolve() for path in builds_root.glob("*.sqlite") if path.is_file()),
        key=lambda path: (path.stat().st_mtime_ns, path.name),
        reverse=True,
    )
    keep = set(protected)
    for path in builds:
        if len(keep) >= retain_builds:
            break
        keep.add(path)
    removable = [path for path in builds if path not in keep]
    removed_bytes = sum(path.stat().st_size for path in removable)
    for path in removable:
        path.unlink()
    return {
        "policy": "keep-current-candidate-and-most-recent",
        "retainedBuildLimit": retain_builds,
        "retainedBuildCount": len([path for path in builds if path in keep]),
        "removedBuildCount": len(removable),
        "removedBytes": removed_bytes,
        "priorPointerStatus": prior_pointer_status,
    }


def sparql(endpoint: str, query: str, timeout: int) -> dict[str, Any]:
    request = urllib.request.Request(
        endpoint,
        data=urllib.parse.urlencode({"query": query}).encode("utf-8"),
        headers={"Accept": "application/sparql-results+json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        result = json.load(response)
    if not isinstance(result, dict) or not isinstance(result.get("results", {}).get("bindings"), list):
        raise ValueError("Fuseki returned an invalid SPARQL result document")
    return result


def lexical(binding: dict[str, Any], field: str) -> str | None:
    value = binding.get(field)
    return value.get("value") if isinstance(value, dict) else None


def typed(binding: dict[str, Any], field: str) -> Any:
    value = lexical(binding, field)
    if value is None:
        return None
    if field in INTEGER_FIELDS:
        if value in {"true", "1"}:
            return 1
        if value in {"false", "0"}:
            return 0
        return int(value)
    if field in FLOAT_FIELDS:
        return float(value)
    return value


def provenance_game_set(game_type: object) -> str:
    """Translate only source-supported MLB game types admitted by the UI."""
    value = str(game_type or "")
    try:
        return GAME_SET_BY_MLB_GAME_TYPE[value]
    except KeyError as exc:
        raise ValueError(
            f"Unsupported or missing MLB game type in persistent provenance: {value!r}"
        ) from exc


def official_metadata(state_root: Path) -> dict[str, dict[str, str]]:
    """Read retained compact provenance, never transient API response bodies."""
    metadata: dict[str, dict[str, str]] = {}
    submissions = state_root / "pipeline" / "manifests" / "submissions"
    for path in sorted(submissions.glob("*.json"), key=lambda item: item.stat().st_mtime):
        try:
            value = json.loads(path.read_text(encoding="utf-8-sig"))
            for game in value.get("games", []):
                game_pk = str(game.get("gamePk", ""))
                date = str(game.get("officialDate", ""))
                if game_pk.isdigit() and len(date) == 10:
                    metadata[game_pk] = {
                        "officialDate": date,
                        "gameSet": provenance_game_set(game.get("gameType")),
                    }
        except (OSError, ValueError, TypeError):
            continue
    for path in sorted((state_root / "pipeline" / "manifests" / "runs" / "games").glob("*.json"), key=lambda item: item.stat().st_mtime):
        try:
            value = json.loads(path.read_text(encoding="utf-8-sig"))
            for game in value.get("games", []):
                game_pk = str(game.get("GamePk", ""))
                official_date = str(game.get("OfficialDate", ""))
                if game_pk.isdigit() and len(official_date) == 10:
                    metadata[game_pk] = {
                        "officialDate": official_date,
                        "gameSet": provenance_game_set(game.get("GameType")),
                    }
        except (OSError, ValueError, TypeError):
            continue
    for path in sorted((state_root / "pipeline" / "manifests" / "acquisition" / "games").glob("*/*/*.json"), key=lambda item: item.stat().st_mtime):
        try:
            value = json.loads(path.read_text(encoding="utf-8-sig"))
            game_pk = str(value.get("gamePk", ""))
            official_date = str(value.get("scheduleDate", ""))
            if game_pk.isdigit() and len(official_date) == 10:
                metadata[game_pk] = {
                    "officialDate": official_date,
                    "gameSet": provenance_game_set(value.get("gameType")),
                }
        except (OSError, ValueError, TypeError):
            continue
    for path in sorted(
        (state_root / "pipeline" / "control" / "mlb-game" / "batches").glob("*.json"),
        key=lambda item: item.stat().st_mtime,
    ):
        try:
            value = json.loads(path.read_text(encoding="utf-8-sig"))
            for game in value.get("games", []):
                game_pk = str(game.get("gamePk", ""))
                official_date = str(game.get("officialDate", ""))
                if game_pk.isdigit() and len(official_date) == 10:
                    metadata[game_pk] = {
                        "officialDate": official_date,
                        "gameSet": provenance_game_set(game.get("gameType")),
                    }
        except (OSError, ValueError, TypeError):
            continue
    for path in sorted(
        (state_root / "pipeline" / "manifests").glob("game-*-rml.json"),
        key=lambda item: item.stat().st_mtime,
    ):
        try:
            value = json.loads(path.read_text(encoding="utf-8-sig"))
            game_pk = str(value.get("gamePk", ""))
            official_date = str(value.get("officialDate", ""))
            if game_pk.isdigit() and len(official_date) == 10:
                metadata[game_pk] = {
                    "officialDate": official_date,
                    "gameSet": provenance_game_set(value.get("gameType")),
                }
        except (OSError, ValueError, TypeError):
            continue
    # Historical compact submissions predate gameType. Recover the checked
    # historical corpus from its accepted schedule evidence; new acquisitions
    # record gameType in compact run evidence and do not require retained API
    # response bodies.
    for path in (ROOT / "data" / "raw" / "samples").glob("*/schedule.json"):
        try:
            value = json.loads(path.read_text(encoding="utf-8-sig"))
            for block in value.get("dates", []):
                for game in block.get("games", []):
                    game_pk = str(game.get("gamePk", ""))
                    official_date = str(game.get("officialDate", ""))
                    if game_pk.isdigit() and len(official_date) == 10:
                        metadata[game_pk] = {
                            "officialDate": official_date,
                            "gameSet": provenance_game_set(game.get("gameType")),
                        }
        except (OSError, ValueError, TypeError):
            continue
    # The long-lived mapper fixture is outside the MLB regular-season corpus.
    metadata["566279"] = {"officialDate": "2019-04-01", "gameSet": "fixture"}
    return metadata


def json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


query_index_contract_admission = _promotion_inventory.query_index_contract_admission
resolve_query_index_manifest_admission = _promotion_inventory.resolve_query_index_manifest_admission
validated_promotion_record = _promotion_inventory.validated_promotion_record
promotion_inventory = _promotion_inventory.promotion_inventory


def live_graph_state_query(inventory: dict[str, Any]) -> str:
    rows = "\n".join(
        "    "
        f"(<{record['authoritativeGraph']}> <{record['queryIndexGraph']}> "
        f"<{record['gameIri']}> <{record['queryIndexResource']}>)"
        for record in (inventory["games"][game_pk] for game_pk in sorted(inventory["games"], key=int))
    )
    return f"""PREFIX base: <https://baseballontology.org/>
PREFIX idx: <https://w3id.org/baseball/query-index/>

SELECT ?sourceGraph ?indexGraph ?game ?indexResource
       (COUNT(?sourceObject) AS ?sourceCount)
       (COUNT(?indexObject) AS ?indexCount) WHERE {{
  VALUES (?sourceGraph ?indexGraph ?game ?indexResource) {{
{rows}
  }}
  {{
    GRAPH ?sourceGraph {{ ?sourceSubject ?sourcePredicate ?sourceObject }}
  }}
  UNION
  {{
    GRAPH ?indexGraph {{ ?indexSubject ?indexPredicate ?indexObject }}
  }}
  FILTER EXISTS {{ GRAPH ?sourceGraph {{ ?game a base:BaseballGame }} }}
  FILTER EXISTS {{ GRAPH ?indexGraph {{ ?indexResource a idx:QueryIndex ; idx:sourceGraph ?sourceGraph }} }}
}}
GROUP BY ?sourceGraph ?indexGraph ?game ?indexResource
ORDER BY ?sourceGraph
"""


def live_graph_state(endpoint: str, timeout: int, inventory: dict[str, Any]) -> dict[str, Any]:
    dimensions_payload = sparql(endpoint, GAME_DIMENSION_QUERY.read_text(encoding="utf-8"), timeout)
    dimensions = dimensions_payload["results"]["bindings"]
    by_graph = {record["authoritativeGraph"]: record for record in inventory["games"].values()}
    dimensions_by_graph: dict[str, dict[str, Any]] = {}
    unpromoted: list[str] = []
    for dimension in dimensions:
        graph = lexical(dimension, "graph") or ""
        record = by_graph.get(graph)
        if record is None:
            unpromoted.append(graph or "<missing graph binding>")
            continue
        if graph in dimensions_by_graph:
            raise ValueError(f"Authoritative graph has multiple game dimensions: {graph}")
        if lexical(dimension, "game") != record["gameIri"]:
            raise ValueError(f"Game dimension identity differs from promotion evidence: {graph}")
        dimensions_by_graph[graph] = dimension
    if unpromoted:
        raise ValueError(
            "Authoritative dimensions include graphs without valid promotion evidence: "
            + ", ".join(sorted(unpromoted)[:5])
        )
    missing_dimensions = sorted(set(by_graph) - set(dimensions_by_graph))
    if missing_dimensions:
        raise ValueError(
            "Valid promotion evidence has no authoritative game dimension: "
            + ", ".join(missing_dimensions[:5])
        )

    graph_payload = sparql(endpoint, live_graph_state_query(inventory), timeout)
    graph_states: dict[str, dict[str, Any]] = {}
    for binding in graph_payload["results"]["bindings"]:
        source_graph = lexical(binding, "sourceGraph") or ""
        record = by_graph.get(source_graph)
        if record is None:
            raise ValueError(f"Live graph-state query returned an unpromoted graph: {source_graph}")
        if source_graph in graph_states:
            raise ValueError(f"Live graph-state query returned duplicate state: {source_graph}")
        if (
            lexical(binding, "indexGraph") != record["queryIndexGraph"]
            or lexical(binding, "game") != record["gameIri"]
            or lexical(binding, "indexResource") != record["queryIndexResource"]
        ):
            raise ValueError(f"Live graph-pair identity differs from promotion evidence: {source_graph}")
        try:
            source_count = int(lexical(binding, "sourceCount") or "")
            index_count = int(lexical(binding, "indexCount") or "")
        except ValueError as exc:
            raise ValueError(f"Live graph counts are invalid for {source_graph}") from exc
        if source_count != record["authoritativeTripleCount"]:
            raise ValueError(f"Live authoritative triple count differs from promotion evidence: {source_graph}")
        if index_count != record["queryIndexTripleCount"]:
            raise ValueError(f"Live query-index triple count differs from promotion evidence: {source_graph}")
        graph_states[source_graph] = {
            "sourceGraph": source_graph,
            "indexGraph": record["queryIndexGraph"],
            "game": record["gameIri"],
            "indexResource": record["queryIndexResource"],
            "sourceCount": source_count,
            "indexCount": index_count,
        }
    missing_states = sorted(set(by_graph) - set(graph_states))
    if missing_states:
        raise ValueError(
            "Valid promotion evidence has no matching live graph pair: "
            + ", ".join(missing_states[:5])
        )

    ordered_dimensions = [dimensions_by_graph[graph] for graph in sorted(dimensions_by_graph)]
    canonical_state = {
        "dimensions": [canonical_binding(binding) for binding in ordered_dimensions],
        "graphStates": [graph_states[graph] for graph in sorted(graph_states)],
    }
    return {
        "fingerprint": sha256_bytes(
            json.dumps(canonical_state, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ),
        "dimensions": ordered_dimensions,
        "graphStates": canonical_state["graphStates"],
    }


def corpus_snapshot(state_root: Path, endpoint: str, timeout: int) -> dict[str, Any]:
    inventory_before = promotion_inventory(state_root)
    live = live_graph_state(endpoint, timeout, inventory_before)
    inventory_after = promotion_inventory(state_root)
    if inventory_after["fingerprint"] != inventory_before["fingerprint"]:
        raise RuntimeError("Promotion inventory changed while the live graph-state snapshot was captured")
    fingerprint = sha256_bytes(
        f"{inventory_before['fingerprint']}|{live['fingerprint']}".encode("utf-8")
    )
    return {"fingerprint": fingerprint, "inventory": inventory_before, "live": live}


def bounded_query(source: str, graph: str) -> str:
    if GRAPH_GUARD not in source:
        raise ValueError("Reviewed serving query has no authoritative graph guard")
    if not graph.startswith(GRAPH_PREFIX) or not graph[len(GRAPH_PREFIX):].isdigit():
        raise ValueError(f"Unsafe authoritative graph: {graph}")
    return source.replace(GRAPH_GUARD, f"{GRAPH_GUARD}\n  VALUES ?graph {{ <{graph}> }}")


def canonical_binding(binding: dict[str, Any]) -> str:
    return json.dumps(binding, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def canonical_row(values: list[Any] | tuple[Any, ...]) -> str:
    return json.dumps(values, ensure_ascii=False, separators=(",", ":"))


def update_row_sequence(hasher: Any, row: str) -> None:
    encoded = row.encode("utf-8")
    hasher.update(len(encoded).to_bytes(8, byteorder="big", signed=False))
    hasher.update(encoded)


def build(args: argparse.Namespace) -> dict[str, Any]:
    state_root = args.state_root.resolve()
    store_root = state_root / "serving"
    builds_root = store_root / "builds"
    evidence_root = store_root / "evidence"
    builds_root.mkdir(parents=True, exist_ok=True)
    evidence_root.mkdir(parents=True, exist_ok=True)
    build_id = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:12]}"
    database = builds_root / f"{build_id}.sqlite"
    schema_bytes = SCHEMA.read_bytes()
    query_source = GOOD_AT_BAT_QUERY.read_text(encoding="utf-8")
    catalog = json.loads(ADVANCED_CATALOG.read_text(encoding="utf-8"))
    reducers = json.loads(ADVANCED_REDUCERS.read_text(encoding="utf-8"))
    advanced_entries = catalog.get("queries", [])
    reducer_ids = set(reducers.get("detailQueries", [])) | set(reducers.get("additiveQueries", {}))
    query_ids = {entry.get("id") for entry in advanced_entries}
    ordering_ids = set(reducers.get("ordering", {}))
    if len(advanced_entries) != 17 or query_ids != reducer_ids or query_ids != ordering_ids:
        raise ValueError("Advanced serving reducers do not cover the reviewed query catalog exactly")
    advanced_sources = {
        entry["id"]: (ROOT / entry["path"]).read_text(encoding="utf-8")
        for entry in advanced_entries
    }
    explore_sources = {name: path.read_text(encoding="utf-8") for name, path in EXPLORE_GRAIN_QUERIES.items()}
    started = time.perf_counter()
    snapshot_started = time.perf_counter()
    initial_snapshot = corpus_snapshot(state_root, args.endpoint, args.timeout)
    initial_snapshot_ms = round((time.perf_counter() - snapshot_started) * 1000, 1)
    inventory = initial_snapshot["inventory"]
    inventory_by_graph = {
        record["authoritativeGraph"]: record for record in inventory["games"].values()
    }
    dimensions = initial_snapshot["live"]["dimensions"]
    metadata = official_metadata(state_root)
    if args.max_games:
        dimensions = dimensions[:args.max_games]
    if not dimensions:
        raise RuntimeError("Authoritative RDF has no materializable games")

    connection = sqlite3.connect(database)
    connection.executescript(schema_bytes.decode("utf-8"))
    rows = 0
    advanced_rows = 0
    advanced_counts = {entry["id"]: 0 for entry in advanced_entries}
    advanced_variables: dict[str, list[str]] = {}
    sparql_durations: list[float] = []
    advanced_sparql_durations: dict[str, list[float]] = {entry["id"]: [] for entry in advanced_entries}
    explore_sparql_durations: dict[str, list[float]] = {name: [] for name in EXPLORE_GRAIN_QUERIES}
    explore_counts = {name: 0 for name in EXPLORE_GRAIN_QUERIES}
    fingerprint_lines: list[str] = []
    preservation_tables = (
        "game_dimension",
        "plate_appearance_fact",
        "advanced_result_fact",
        "batting_result_fact",
        "pitch_fact",
        "runner_event_fact",
        "assignment_fact",
        "empty_damage_fact",
    )
    source_row_hashers = {table: hashlib.sha256() for table in preservation_tables}
    source_row_counts = {table: 0 for table in preservation_tables}

    def record_source_row(table: str, row: str) -> None:
        update_row_sequence(source_row_hashers[table], row)
        source_row_counts[table] += 1
    insert_columns = [column for _, column in COLUMNS]
    placeholders = ",".join("?" for _ in range(1 + len(COLUMNS) + 2))
    insert_sql = (
        f"INSERT INTO plate_appearance_fact (graph_iri,{','.join(insert_columns)},binding_json,binding_sha256) "
        f"VALUES ({placeholders})"
    )
    candidate_validated = False
    binding_preservation: dict[str, dict[str, Any]] = {}
    try:
        for entry in advanced_entries:
            reducer_mode = "detail" if entry["id"] in reducers["detailQueries"] else "additive"
            connection.execute(
                "INSERT INTO advanced_query_manifest VALUES (?,?,?,?,?)",
                (entry["id"], sha256_file(ROOT / entry["path"]), reducer_mode, "[]", 0),
            )
        for index, dimension in enumerate(dimensions, start=1):
            graph = lexical(dimension, "graph") or ""
            game = lexical(dimension, "game") or ""
            game_pk = game.rsplit("/", 1)[-1]
            source_meta = metadata.get(game_pk, {})
            official_date = source_meta.get("officialDate") or (lexical(dimension, "start") or "")[:10]
            provenance_set = source_meta.get("gameSet")
            rdf_game_set = lexical(dimension, "rdfGameSet")
            if provenance_set and rdf_game_set and provenance_set != rdf_game_set:
                raise ValueError(
                    f"Persistent game-set provenance conflicts with authoritative RDF for game {game_pk}: "
                    f"{provenance_set!r} != {rdf_game_set!r}"
                )
            game_set = provenance_set or rdf_game_set
            if len(official_date) != 10:
                raise ValueError(f"No official date provenance for game {game_pk}")
            if game_set not in PERSISTENT_GAME_SETS:
                raise ValueError(
                    f"No supported persistent game-set provenance for game {game_pk}; "
                    "authoritative RDF does not yet carry this classification"
                )
            dimension_values = (
                graph, game, game_pk, official_date, lexical(dimension, "start"),
                int(official_date[:4]), game_set, lexical(dimension, "venue"),
                lexical(dimension, "venueLabel"), lexical(dimension, "homeTeam"),
                lexical(dimension, "homeTeamLabel"), lexical(dimension, "awayTeam"),
                lexical(dimension, "awayTeamLabel"),
            )
            connection.execute(
                "INSERT INTO game_dimension VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                dimension_values,
            )
            record_source_row("game_dimension", canonical_row(dimension_values))
            promotion_record = inventory_by_graph.get(graph)
            if promotion_record is None or promotion_record["gamePk"] != game_pk:
                raise ValueError(f"Materialization escaped the validated promotion inventory: {graph}")
            artifact = promotion_record["authoritativeRdfSha256"]
            fingerprint_lines.append(f"{graph}|{official_date}|{game_set}|{artifact}")
            query_started = time.perf_counter()
            payload = sparql(args.endpoint, bounded_query(query_source, graph), args.timeout)
            paq_duration = (time.perf_counter() - query_started) * 1000
            sparql_durations.append(paq_duration)
            advanced_sparql_durations["plate-appearance-fingerprint"].append(paq_duration)
            for binding in payload["results"]["bindings"]:
                canonical = canonical_binding(binding)
                values = [typed(binding, field) for field, _ in COLUMNS]
                connection.execute(insert_sql, [graph, *values, canonical, sha256_bytes(canonical.encode("utf-8"))])
                record_source_row(
                    "plate_appearance_fact", canonical_row([graph, *values, canonical])
                )
                rows += 1
            for query_id, source in advanced_sources.items():
                if query_id == "plate-appearance-fingerprint":
                    advanced_payload = payload
                else:
                    advanced_started = time.perf_counter()
                    advanced_payload = sparql(args.endpoint, bounded_query(source, graph), args.timeout)
                    advanced_sparql_durations[query_id].append(
                        (time.perf_counter() - advanced_started) * 1000
                    )
                variables = advanced_payload.get("head", {}).get("vars", [])
                if not isinstance(variables, list) or not all(isinstance(value, str) for value in variables):
                    raise ValueError(f"Advanced query {query_id} returned an invalid variable contract")
                previous_variables = advanced_variables.setdefault(query_id, variables)
                if previous_variables != variables:
                    raise ValueError(f"Advanced query {query_id} changed variables between game graphs")
                for ordinal, binding in enumerate(advanced_payload["results"]["bindings"]):
                    canonical = canonical_binding(binding)
                    connection.execute(
                        "INSERT INTO advanced_result_fact VALUES (?,?,?,?,?)",
                        (query_id, graph, ordinal, canonical, sha256_bytes(canonical.encode("utf-8"))),
                    )
                    record_source_row(
                        "advanced_result_fact",
                        canonical_row((query_id, graph, ordinal, canonical)),
                    )
                    advanced_counts[query_id] += 1
                    advanced_rows += 1
            for grain_name, source in explore_sources.items():
                grain_started = time.perf_counter()
                try:
                    grain_payload = sparql(args.endpoint, bounded_query(source, graph), args.timeout)
                except Exception as exc:
                    raise RuntimeError(f"Serving grain {grain_name} failed for {graph}: {exc}") from exc
                explore_sparql_durations[grain_name].append((time.perf_counter() - grain_started) * 1000)
                for binding in grain_payload["results"]["bindings"]:
                    if grain_name == "batting":
                        grain_values = (
                            graph, lexical(binding, "result"), lexical(binding, "plateAppearance"),
                            lexical(binding, "player"), lexical(binding, "playerLabel"),
                            lexical(binding, "team"), lexical(binding, "teamLabel"),
                            lexical(binding, "eventType"),
                        )
                        connection.execute(
                            "INSERT INTO batting_result_fact VALUES (?,?,?,?,?,?,?,?)",
                            grain_values,
                        )
                        record_source_row("batting_result_fact", canonical_row(grain_values))
                    elif grain_name == "pitching":
                        grain_values = (
                            graph, lexical(binding, "pitch"), lexical(binding, "plateAppearance"),
                            lexical(binding, "pitcher"), lexical(binding, "pitcherLabel"),
                            lexical(binding, "team"), lexical(binding, "teamLabel"),
                            lexical(binding, "pitchCallCode"),
                        )
                        connection.execute(
                            "INSERT INTO pitch_fact VALUES (?,?,?,?,?,?,?,?)",
                            grain_values,
                        )
                        record_source_row("pitch_fact", canonical_row(grain_values))
                    elif grain_name == "baserunning":
                        grain_values = (
                            graph, lexical(binding, "resolution"), lexical(binding, "player"),
                            lexical(binding, "playerLabel"), lexical(binding, "team"),
                            lexical(binding, "teamLabel"), lexical(binding, "eventType"),
                            lexical(binding, "resolutionClass"), lexical(binding, "stolenBase"),
                        )
                        connection.execute(
                            "INSERT INTO runner_event_fact VALUES (?,?,?,?,?,?,?,?,?)",
                            grain_values,
                        )
                        record_source_row("runner_event_fact", canonical_row(grain_values))
                    elif grain_name == "assignments":
                        assignment_type = (lexical(binding, "assignmentType") or "").rsplit("/", 1)[-1]
                        assignment_type = {
                            "HomeTeam": "home", "AwayTeam": "away", "Umpire": "umpire",
                            "OfficialScorer": "official_scorer",
                        }.get(assignment_type, "")
                        if not assignment_type:
                            raise ValueError("Indexed assignment has an unsupported type")
                        grain_values = (
                            graph, lexical(binding, "assignment"), assignment_type,
                            lexical(binding, "assignee"), lexical(binding, "assigneeLabel"),
                        )
                        connection.execute(
                            "INSERT INTO assignment_fact VALUES (?,?,?,?,?)",
                            grain_values,
                        )
                        record_source_row("assignment_fact", canonical_row(grain_values))
                    else:
                        canonical = canonical_binding(binding)
                        grain_values = (
                            graph, lexical(binding, "player"), lexical(binding, "team"),
                            lexical(binding, "damagePitcher"),
                            lexical(binding, "damagePlateAppearance"), canonical,
                        )
                        connection.execute(
                            "INSERT INTO empty_damage_fact VALUES (?,?,?,?,?,?,?)",
                            (*grain_values, sha256_bytes(canonical.encode("utf-8"))),
                        )
                        record_source_row("empty_damage_fact", canonical_row(grain_values))
                    explore_counts[grain_name] += 1
            if index % 10 == 0:
                connection.commit()
        for query_id in sorted(advanced_counts):
            connection.execute(
                "UPDATE advanced_query_manifest SET variables_json=?,binding_count=? WHERE query_id=?",
                (json.dumps(advanced_variables.get(query_id, []), separators=(",", ":")), advanced_counts[query_id], query_id),
            )
        connection.execute(
            """INSERT INTO empty_player_game_fact
               SELECT b.graph_iri,b.player_iri,b.player_label,b.team_iri,b.team_label,
                      COALESCE(p.pitcher_iri,''),COALESCE(p.pitcher_label,''),
                      CASE WHEN EXISTS (
                        SELECT 1 FROM batting_result_fact contribution
                        WHERE contribution.graph_iri=b.graph_iri AND contribution.player_iri=b.player_iri
                          AND contribution.event_type IN ('single','double','triple','home_run','walk','sac_fly','fielders_choice')
                      ) OR EXISTS (
                        SELECT 1 FROM runner_event_fact steal
                        WHERE steal.graph_iri=b.graph_iri AND steal.player_iri=b.player_iri
                          AND steal.stolen_base_iri IS NOT NULL
                      ) THEN 0 ELSE 1 END
               FROM (SELECT DISTINCT graph_iri,player_iri,player_label,team_iri,team_label
                     FROM batting_result_fact) b
               LEFT JOIN (
                 SELECT DISTINCT br.graph_iri,br.player_iri,pf.pitcher_iri,pf.pitcher_label
                 FROM batting_result_fact br JOIN pitch_fact pf
                   ON pf.graph_iri=br.graph_iri AND pf.plate_appearance_iri=br.plate_appearance_iri
               ) p ON p.graph_iri=b.graph_iri AND p.player_iri=b.player_iri
               WHERE (SELECT COUNT(DISTINCT plate_appearance_iri) FROM plate_appearance_fact pa
                      WHERE pa.graph_iri=b.graph_iri)
                   = (SELECT COUNT(DISTINCT plate_appearance_iri) FROM batting_result_fact result
                      WHERE result.graph_iri=b.graph_iri)"""
        )
        empty_player_games = connection.execute(
            "SELECT COUNT(DISTINCT graph_iri || char(31) || player_iri) FROM empty_player_game_fact"
        ).fetchone()[0]
        corpus_fingerprint = sha256_bytes("\n".join(sorted(fingerprint_lines)).encode("utf-8"))
        connection.execute(
            "INSERT INTO serving_build VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (build_id, 5, utc_now(), corpus_fingerprint, sha256_file(GOOD_AT_BAT_QUERY),
             sha256_file(SCHEMA), sha256_file(MATERIALIZER), sha256_file(MAPPING),
             sha256_file(VALIDATOR), sha256_file(QUALITY_SPEC), len(dimensions), rows,
             len(advanced_entries), advanced_rows, explore_counts["batting"],
             explore_counts["pitching"], explore_counts["baserunning"],
             explore_counts["assignments"], empty_player_games, explore_counts["damage"], "candidate"),
        )
        connection.commit()
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_key_issues = connection.execute("PRAGMA foreign_key_check").fetchall()
        hash_mismatches = sum(
            sha256_bytes(binding.encode("utf-8")) != digest
            for binding, digest in connection.execute("SELECT binding_json,binding_sha256 FROM plate_appearance_fact")
        )
        advanced_hash_mismatches = sum(
            sha256_bytes(binding.encode("utf-8")) != digest
            for binding, digest in connection.execute("SELECT binding_json,binding_sha256 FROM advanced_result_fact")
        )
        damage_hash_mismatches = sum(
            sha256_bytes(binding.encode("utf-8")) != digest
            for binding, digest in connection.execute("SELECT binding_json,binding_sha256 FROM empty_damage_fact")
        )
        stored_queries = {
            "game_dimension": "SELECT * FROM game_dimension ORDER BY rowid",
            "plate_appearance_fact": (
                f"SELECT graph_iri,{','.join(insert_columns)},binding_json "
                "FROM plate_appearance_fact ORDER BY rowid"
            ),
            "advanced_result_fact": (
                "SELECT query_id,graph_iri,row_ordinal,binding_json "
                "FROM advanced_result_fact ORDER BY rowid"
            ),
            "batting_result_fact": "SELECT * FROM batting_result_fact ORDER BY rowid",
            "pitch_fact": "SELECT * FROM pitch_fact ORDER BY rowid",
            "runner_event_fact": "SELECT * FROM runner_event_fact ORDER BY rowid",
            "assignment_fact": "SELECT * FROM assignment_fact ORDER BY rowid",
            "empty_damage_fact": (
                "SELECT graph_iri,player_iri,team_iri,pitcher_iri,"
                "plate_appearance_iri,binding_json FROM empty_damage_fact ORDER BY rowid"
            ),
        }
        preservation_failures: list[str] = []
        for table, query in stored_queries.items():
            stored_hasher = hashlib.sha256()
            stored_count = 0
            for row in connection.execute(query):
                update_row_sequence(stored_hasher, canonical_row(tuple(row)))
                stored_count += 1
            source_hash = source_row_hashers[table].hexdigest()
            stored_hash = stored_hasher.hexdigest()
            matches = (
                source_row_counts[table] == stored_count
                and source_hash == stored_hash
            )
            binding_preservation[table] = {
                "sourceRowCount": source_row_counts[table],
                "storedRowCount": stored_count,
                "sourceRowSequenceSha256": source_hash,
                "storedRowSequenceSha256": stored_hash,
                "matches": matches,
            }
            if not matches:
                preservation_failures.append(table)
        if (
            integrity != "ok"
            or foreign_key_issues
            or hash_mismatches
            or advanced_hash_mismatches
            or damage_hash_mismatches
            or preservation_failures
        ):
            raise RuntimeError("Candidate SQLite validation failed")
        benchmark_times = []
        end_date = connection.execute(
            "SELECT MAX(official_date) FROM game_dimension WHERE game_set='regular_season'"
        ).fetchone()[0]
        for _ in range(7):
            benchmark_started = time.perf_counter()
            connection.execute(
                "SELECT binding_json FROM plate_appearance_fact p JOIN game_dimension g USING(graph_iri) "
                "WHERE g.game_set=? AND g.official_date BETWEEN date(?, '-6 days') AND ? "
                "ORDER BY p.game_iri,p.start_time LIMIT 1000",
                ("regular_season", end_date, end_date),
            ).fetchall()
            benchmark_times.append((time.perf_counter() - benchmark_started) * 1000)
        connection.execute("UPDATE serving_build SET status='validated' WHERE build_id=?", (build_id,))
        connection.commit()
        connection.execute("PRAGMA optimize")
        candidate_validated = True
    finally:
        connection.close()
        if not candidate_validated:
            database.unlink(missing_ok=True)

    evidence = {
        "artifactType": "baseball-analytical-serving-build-evidence",
        "contractVersion": 5,
        "evidenceSchemaVersion": 2,
        "buildId": build_id,
        "status": "validated",
        "createdAtUtc": utc_now(),
        "databasePath": str(database.resolve()),
        "databaseSha256": sha256_file(database),
        "corpusFingerprint": corpus_fingerprint,
        "gameCount": len(dimensions),
        "plateAppearanceCount": rows,
        "advancedQueryCount": len(advanced_entries),
        "advancedBindingCount": advanced_rows,
        "advancedBindingsByQuery": advanced_counts,
        "exploreCounts": explore_counts,
        "emptyPlayerGameCount": empty_player_games,
        "integrity": {
            "sqliteIntegrityCheck": integrity,
            "foreignKeyIssueCount": len(foreign_key_issues),
            "checkedBindingHashes": rows + advanced_rows + explore_counts["damage"],
            "bindingHashMismatches": hash_mismatches + advanced_hash_mismatches + damage_hash_mismatches,
            "sourceRowPreservation": binding_preservation,
        },
        "sourceCorpusIntegrity": {
            "snapshotSha256": initial_snapshot["fingerprint"],
            "promotionInventorySha256": inventory["fingerprint"],
            "liveGraphStateSha256": initial_snapshot["live"]["fingerprint"],
            "validatedPromotionGameCount": inventory["gameCount"],
            "supersededPromotionManifestCount": inventory["supersededManifestCount"],
            "queryIndexRoutingSha256": inventory["queryIndexRoutingSha256"],
            "queryIndexSemanticContractId": inventory["queryIndexSemanticContractId"],
            "queryIndexSemanticContractSha256": inventory[
                "queryIndexSemanticContractSha256"
            ],
            "legacyQueryIndexImplementationBridgeSha256Set": inventory[
                "legacyQueryIndexImplementationBridgeSha256Set"
            ],
            "queryIndexImplementationSha256Set": inventory[
                "queryIndexImplementationSha256Set"
            ],
        },
        "benchmark": {
            "engine": "sqlite",
            "initialCorpusSnapshotMs": initial_snapshot_ms,
            "boundedAuthoritativeSparqlTotalMs": round(sum(sparql_durations), 1),
            "boundedAuthoritativeSparqlMedianPerGameMs": round(statistics.median(sparql_durations), 1),
            "sqlSevenDayMedianMs": round(statistics.median(benchmark_times), 3),
            "sqlSevenDayRunsMs": [round(value, 3) for value in benchmark_times],
            "reviewedSparqlByQuery": {
                query_id: {
                    "calls": len(durations),
                    "totalMs": round(sum(durations), 1),
                    "medianPerGameMs": round(statistics.median(durations), 1),
                }
                for query_id, durations in sorted(advanced_sparql_durations.items())
            },
            "exploreSparqlByGrain": {
                name: {"calls": len(durations), "totalMs": round(sum(durations), 1),
                       "medianPerGameMs": round(statistics.median(durations), 1)}
                for name, durations in sorted(explore_sparql_durations.items())
            },
            "duckdbAvailability": "not-installed",
        },
        "totalBuildMs": round((time.perf_counter() - started) * 1000, 1),
        "sourceQuerySha256": sha256_file(GOOD_AT_BAT_QUERY),
        "advancedQuerySetSha256": advanced_query_set_sha256(catalog),
        "advancedReducerSha256": sha256_file(ADVANCED_REDUCERS),
        "exploreQuerySetSha256": file_set_sha256(SERVING_QUERY_FILES),
        "schemaSha256": sha256_file(SCHEMA),
        "materializerSha256": sha256_file(MATERIALIZER),
        "mappingSha256": sha256_file(MAPPING),
        "validationSha256": sha256_file(VALIDATOR),
        "ratingSpecSha256": sha256_file(QUALITY_SPEC),
        "contractSha256": sha256_file(CONTRACT),
    }
    evidence_path = evidence_root / f"{build_id}.json"
    atomic_json(evidence_path, evidence)
    if not args.no_promote and not args.max_games:
        promotion_snapshot = corpus_snapshot(state_root, args.endpoint, args.timeout)
        if promotion_snapshot["fingerprint"] != initial_snapshot["fingerprint"]:
            raise RuntimeError(
                "Serving promotion refused because the promotion inventory or live graph state drifted during materialization"
            )
        evidence["sourceCorpusIntegrity"]["promotionSnapshotSha256"] = promotion_snapshot["fingerprint"]
        evidence["sourceCorpusIntegrity"]["promotionInventoryRechecked"] = True
        evidence["sourceCorpusIntegrity"]["liveGraphStateRechecked"] = True
        promotion_time = utc_now()
        evidence["promotionReadyAtUtc"] = promotion_time
        evidence["retention"] = enforce_build_retention(
            store_root, database, getattr(args, "retain_builds", 3)
        )
        atomic_json(evidence_path, evidence)
        pointer = {
            "artifactType": "baseball-analytical-serving-pointer",
            "contractVersion": 5,
            "promotedAtUtc": promotion_time,
            "buildId": build_id,
            "databasePath": str(database.resolve()),
            "databaseSha256": evidence["databaseSha256"],
            "corpusFingerprint": corpus_fingerprint,
            "sourceQuerySha256": evidence["sourceQuerySha256"],
            "advancedQuerySetSha256": evidence["advancedQuerySetSha256"],
            "advancedReducerSha256": evidence["advancedReducerSha256"],
            "exploreQuerySetSha256": evidence["exploreQuerySetSha256"],
            "schemaSha256": evidence["schemaSha256"],
            "materializerSha256": evidence["materializerSha256"],
            "mappingSha256": evidence["mappingSha256"],
            "validationSha256": evidence["validationSha256"],
            "ratingSpecSha256": evidence["ratingSpecSha256"],
            "contractSha256": evidence["contractSha256"],
            "gameCount": len(dimensions),
            "plateAppearanceCount": rows,
            "advancedQueryCount": len(advanced_entries),
            "advancedBindingCount": advanced_rows,
            "exploreCounts": explore_counts,
            "emptyPlayerGameCount": empty_player_games,
            "evidencePath": str(evidence_path.resolve()),
        }
        # This is deliberately the final filesystem mutation. Any failure before
        # this atomic swap leaves the prior validated pointer active.
        atomic_json(store_root / "current.json", pointer)
        return {**evidence, "status": "promoted", "promotedAtUtc": promotion_time}
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    default_state = Path(os.environ.get("BASEBALLO_STATE_ROOT") or Path(os.environ.get("LOCALAPPDATA", ".")) / "BaseballO" / "state")
    parser.add_argument("--state-root", type=Path, default=default_state)
    parser.add_argument("--endpoint", default="http://127.0.0.1:3031/baseball-dev/query")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--max-games", type=int)
    parser.add_argument("--no-promote", action="store_true")
    parser.add_argument(
        "--retain-builds",
        type=int,
        default=3,
        help="Keep the promoted candidate, prior current build, and newest rollback builds (minimum 2)",
    )
    args = parser.parse_args()
    try:
        print(json.dumps(build(args), separators=(",", ":")))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, separators=(",", ":")))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
