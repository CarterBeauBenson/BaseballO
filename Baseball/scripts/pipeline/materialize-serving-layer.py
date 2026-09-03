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
import urllib.error
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rdflib.plugins.sparql.processor import prepareQuery


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
DSQ_MATERIALIZATIONS = SERVING_ROOT / "dsq-materializations.json"
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
INDEX_GRAPH_GUARD = f'FILTER(STRSTARTS(STR(?indexGraph), "{INDEX_GRAPH_PREFIX}"))'
LIVE_PREFLIGHT_BATCH_SIZE = 200
SHA256_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")
SQL_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
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


def dsq_query_set_sha256(entries: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for entry in sorted(entries, key=lambda item: item["id"]):
        digest.update(entry["id"].encode("utf-8"))
        digest.update(b"\0")
        digest.update((ROOT / entry["path"]).read_bytes())
        digest.update(b"\0")
        digest.update(entry["executionLayer"].encode("utf-8"))
        digest.update(b"\0")
        digest.update((ROOT / entry["executionPath"]).read_bytes())
        digest.update(b"\0")
        digest.update(
            json.dumps(entry["reducer"], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        )
        digest.update(b"\0")
    return digest.hexdigest()


def _checked_identifier(value: object, label: str) -> str:
    text_value = str(value)
    if not SQL_IDENTIFIER_PATTERN.fullmatch(text_value):
        raise ValueError(f"Invalid {label}: {text_value!r}")
    return text_value


def _relative_query_path(value: object) -> str:
    relative = str(value).replace("\\", "/")
    path = (ROOT / relative).resolve()
    sparql_root = (ROOT / "sparql").resolve()
    if path.suffix != ".rq" or sparql_root not in path.parents or not path.is_file():
        raise ValueError(f"DSQ query path is missing or outside sparql/: {relative}")
    return relative


def projected_variables(path: str) -> list[str]:
    query = prepareQuery((ROOT / path).read_text(encoding="utf-8"))
    variables = [str(variable) for variable in query.algebra.PV]
    if not variables or any(not SQL_IDENTIFIER_PATTERN.fullmatch(variable) for variable in variables):
        raise ValueError(f"DSQ has an invalid projected-variable contract: {path}")
    return variables


def load_dsq_entries(
    catalog: dict[str, Any], advanced_catalog: dict[str, Any], advanced_reducers: dict[str, Any]
) -> list[dict[str, Any]]:
    if (
        catalog.get("artifactType") != "baseballo-dsq-sql-materialization-catalog"
        or catalog.get("contractVersion") != 1
    ):
        raise ValueError("Unsupported DSQ SQL materialization catalog")
    advanced = catalog.get("advanced")
    if not isinstance(advanced, dict) or advanced != {
        "catalog": "sparql/advanced/advanced-query-catalog.json",
        "reducers": "serving/advanced-query-reducers.json",
        "tablePrefix": "dsq_advanced_",
    }:
        raise ValueError("DSQ catalog does not bind the reviewed advanced query contract exactly")
    routing = json.loads(QUERY_INDEX_ROUTING.read_text(encoding="utf-8"))
    routes = {
        str(route["authoritative"]): route
        for route in routing.get("routes", [])
        if isinstance(route, dict) and route.get("authoritative")
    }
    entries: list[dict[str, Any]] = []
    detail_ids = set(advanced_reducers.get("detailQueries", []))
    additive = advanced_reducers.get("additiveQueries", {})
    for query in advanced_catalog.get("queries", []):
        query_id = _checked_identifier(str(query.get("id", "")).replace("-", "_"), "advanced DSQ id")
        source_id = str(query["id"])
        if source_id in detail_ids:
            filter_dimensions = [
                str(value["variable"])
                for value in query.get("resultFilters", [])
                if isinstance(value, dict) and value.get("variable")
            ]
            reducer: dict[str, Any] = {
                "mode": "detail",
                "dimensions": list(dict.fromkeys(filter_dimensions)),
                "sums": [],
            }
        elif source_id in additive and isinstance(additive[source_id], dict):
            reducer = {"mode": "additive", **additive[source_id]}
        else:
            raise ValueError(f"Advanced DSQ has no reducer: {source_id}")
        path = _relative_query_path(query["path"])
        variables = projected_variables(path)
        if not set(reducer.get("dimensions", []) + reducer.get("sums", [])).issubset(variables):
            raise ValueError(f"Advanced DSQ reducer fields are not projected: {source_id}")
        entries.append(
            {
                "id": source_id,
                "family": "advanced",
                "kind": "advanced",
                "path": path,
                "executionLayer": "authoritative",
                "executionPath": path,
                "table": f"dsq_advanced_{query_id}",
                "reducer": reducer,
                "variables": variables,
            }
        )
    canned = catalog.get("cannedQueries")
    if not isinstance(canned, list):
        raise ValueError("DSQ catalog cannedQueries must be a list")
    expected_canned = {
        path.relative_to(ROOT).as_posix()
        for directory in (
            ROOT / "sparql",
            ROOT / "sparql" / "batting",
            ROOT / "sparql" / "pitching",
            ROOT / "sparql" / "baserunning",
            ROOT / "sparql" / "games",
        )
        for path in directory.glob("*.rq")
    }
    catalog_canned: set[str] = set()
    for query in canned:
        if not isinstance(query, dict):
            raise ValueError("DSQ catalog entries must be objects")
        query_id = str(query.get("id", ""))
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", query_id):
            raise ValueError(f"Invalid canned DSQ id: {query_id!r}")
        path = _relative_query_path(query.get("path"))
        variables = projected_variables(path)
        route = routes.get(path)
        execution_layer = "indexed" if route and route.get("autoLayer") == "indexed" else "authoritative"
        execution_path = (
            _relative_query_path(route["indexed"])
            if execution_layer == "indexed"
            else path
        )
        if projected_variables(execution_path) != variables:
            raise ValueError(f"DSQ execution query changes projected variables: {query_id}")
        catalog_canned.add(path)
        reducer = query.get("reducer")
        if not isinstance(reducer, dict) or reducer.get("mode") not in {"additive", "detail"}:
            raise ValueError(f"Canned DSQ reducer is invalid: {query_id}")
        dimensions = reducer.get("dimensions")
        sums = reducer.get("sums")
        if (
            not isinstance(dimensions, list)
            or not isinstance(sums, list)
            or not all(isinstance(value, str) and SQL_IDENTIFIER_PATTERN.fullmatch(value) for value in dimensions + sums)
            or set(dimensions) & set(sums)
            or (reducer["mode"] == "additive" and not sums)
            or (reducer["mode"] == "detail" and sums)
            or not set(dimensions + sums).issubset(variables)
        ):
            raise ValueError(f"Canned DSQ reducer fields are invalid: {query_id}")
        family = str(query.get("family", ""))
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", family):
            raise ValueError(f"Invalid DSQ family: {family!r}")
        entries.append(
            {
                "id": query_id,
                "family": family,
                "kind": "canned",
                "path": path,
                "executionLayer": execution_layer,
                "executionPath": execution_path,
                "table": _checked_identifier(query.get("table"), "DSQ result table"),
                "reducer": reducer,
                "variables": variables,
            }
        )
    if catalog_canned != expected_canned:
        raise ValueError(
            "Canned DSQ SQL coverage differs from the approved query surface: "
            f"missing={sorted(expected_canned - catalog_canned)}, extra={sorted(catalog_canned - expected_canned)}"
        )
    ids = [entry["id"] for entry in entries]
    tables = [entry["table"] for entry in entries]
    if len(entries) != 56 or len(ids) != len(set(ids)) or len(tables) != len(set(tables)):
        raise ValueError("DSQ SQL catalog must name 56 unique questions and result tables")
    return entries


def create_dsq_table(
    connection: sqlite3.Connection, entry: dict[str, Any], variables: list[str]
) -> None:
    table = _checked_identifier(entry["table"], "DSQ result table")
    checked_variables = [_checked_identifier(variable, "DSQ result variable") for variable in variables]
    if (
        len(checked_variables) != len(set(checked_variables))
        or set(checked_variables) & {"graph_iri", "row_ordinal", "binding_json", "binding_sha256"}
    ):
        raise ValueError(f"DSQ query returned duplicate variables: {entry['id']}")
    generated = [
        f'"{variable}" TEXT GENERATED ALWAYS AS '
        f'(json_extract(binding_json, \'$."{variable}".value\')) STORED'
        for variable in checked_variables
    ]
    columns = [
        "graph_iri TEXT NOT NULL REFERENCES game_dimension(graph_iri)",
        "row_ordinal INTEGER NOT NULL",
        "binding_json TEXT NOT NULL CHECK (json_valid(binding_json))",
        "binding_sha256 TEXT NOT NULL",
        *generated,
        "PRIMARY KEY (graph_iri, row_ordinal)",
    ]
    connection.execute(f'CREATE TABLE "{table}" ({",".join(columns)}) STRICT')
    connection.execute(f'CREATE INDEX "{table}_graph_idx" ON "{table}" (graph_iri)')
    for variable in entry["reducer"].get("dimensions", []):
        if variable in checked_variables:
            connection.execute(
                f'CREATE INDEX "{table}_{variable}_idx" ON "{table}" ("{variable}")'
            )


def insert_dsq_payload(
    connection: sqlite3.Connection,
    entry: dict[str, Any],
    graph: str,
    payload: dict[str, Any],
    state: dict[str, Any],
    record_source_row: Any,
) -> int:
    variables = payload.get("head", {}).get("vars", [])
    expected_variables = entry["variables"]
    bindings = payload.get("results", {}).get("bindings", [])
    if not isinstance(variables, list) or not all(isinstance(value, str) for value in variables):
        raise ValueError(f"DSQ query {entry['id']} returned an invalid variable contract")
    if not isinstance(bindings, list) or not all(isinstance(value, dict) for value in bindings):
        raise ValueError(f"DSQ query {entry['id']} returned invalid bindings")
    if variables and variables != expected_variables:
        raise ValueError(f"DSQ query {entry['id']} changed its projected-variable contract")
    if state["variables"] is None:
        state["variables"] = expected_variables
        create_dsq_table(connection, entry, expected_variables)
    elif state["variables"] != expected_variables:
        raise ValueError(f"DSQ query {entry['id']} changed variables between game graphs")
    table = _checked_identifier(entry["table"], "DSQ result table")
    for ordinal, binding in enumerate(bindings):
        if set(binding) - set(expected_variables):
            raise ValueError(f"DSQ query {entry['id']} returned an undeclared binding")
        canonical = canonical_binding(binding)
        row = (graph, ordinal, canonical, sha256_bytes(canonical.encode("utf-8")))
        connection.execute(
            f'INSERT INTO "{table}" (graph_iri,row_ordinal,binding_json,binding_sha256) VALUES (?,?,?,?)',
            row,
        )
        record_source_row(table, canonical_row((graph, ordinal, canonical)))
    state["count"] += len(bindings)
    return len(bindings)


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
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read(2048).decode("utf-8", errors="replace").strip()
        message = detail or str(exc.reason)
        raise RuntimeError(f"SPARQL endpoint returned HTTP {exc.code}: {message}") from exc
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


def graph_batches(
    records: list[dict[str, Any]], batch_size: int = LIVE_PREFLIGHT_BATCH_SIZE
) -> list[list[dict[str, Any]]]:
    if batch_size <= 0:
        raise ValueError("Live graph-state batch size must be positive")
    return [records[offset : offset + batch_size] for offset in range(0, len(records), batch_size)]


def bounded_query_for_graphs(source: str, graphs: list[str]) -> str:
    if GRAPH_GUARD not in source:
        raise ValueError("Reviewed serving query has no authoritative graph guard")
    if not graphs:
        raise ValueError("A bounded serving query requires at least one graph")
    if len(graphs) > LIVE_PREFLIGHT_BATCH_SIZE:
        raise ValueError("A bounded serving query exceeds the live preflight batch limit")
    for graph in graphs:
        if not graph.startswith(GRAPH_PREFIX) or not graph[len(GRAPH_PREFIX):].isdigit():
            raise ValueError(f"Unsafe authoritative graph: {graph}")
    values = " ".join(f"<{graph}>" for graph in graphs)
    return source.replace(GRAPH_GUARD, f"{GRAPH_GUARD}\n  VALUES ?graph {{ {values} }}")


def live_source_graph_state_query(records: list[dict[str, Any]]) -> str:
    if not records:
        raise ValueError("A live source graph-state query requires at least one promoted graph")
    if len(records) > LIVE_PREFLIGHT_BATCH_SIZE:
        raise ValueError("A live source graph-state query exceeds the live preflight batch limit")
    rows = "\n".join(
        f"    (<{record['authoritativeGraph']}> <{record['gameIri']}>)"
        for record in records
    )
    return f"""SELECT ?sourceGraph ?game (COUNT(?sourceObject) AS ?sourceCount) WHERE {{
  VALUES (?sourceGraph ?game) {{
{rows}
  }}
  GRAPH ?sourceGraph {{ ?sourceSubject ?sourcePredicate ?sourceObject }}
}}
GROUP BY ?sourceGraph ?game
ORDER BY ?sourceGraph
"""


def live_index_graph_state_query(records: list[dict[str, Any]]) -> str:
    if not records:
        raise ValueError("A live index graph-state query requires at least one promoted graph")
    if len(records) > LIVE_PREFLIGHT_BATCH_SIZE:
        raise ValueError("A live index graph-state query exceeds the live preflight batch limit")
    rows = "\n".join(
        "    "
        f"(<{record['queryIndexGraph']}> <{record['authoritativeGraph']}> "
        f"<{record['gameIri']}> <{record['queryIndexResource']}>)"
        for record in records
    )
    return f"""PREFIX idx: <https://w3id.org/baseball/query-index/>

SELECT ?indexGraph ?sourceGraph ?game ?indexResource
       (COUNT(?indexObject) AS ?indexCount) WHERE {{
  VALUES (?indexGraph ?sourceGraph ?game ?indexResource) {{
{rows}
  }}
  GRAPH ?indexGraph {{ ?indexSubject ?indexPredicate ?indexObject }}
  FILTER EXISTS {{
    GRAPH ?indexGraph {{
      ?indexResource a idx:QueryIndex ;
          idx:sourceGraph ?sourceGraph ;
          idx:indexedGame ?game .
    }}
  }}
}}
GROUP BY ?indexGraph ?sourceGraph ?game ?indexResource
ORDER BY ?indexGraph
"""


def adaptive_preflight_query(
    endpoint: str,
    timeout: int,
    records: list[dict[str, Any]],
    label: str,
    query_factory: Any,
) -> list[dict[str, Any]]:
    try:
        payload = sparql(endpoint, query_factory(records), timeout)
        return payload["results"]["bindings"]
    except Exception as exc:
        if len(records) == 1:
            raise RuntimeError(
                f"Live preflight {label} failed for game {records[0]['gamePk']}: {exc}"
            ) from exc
        midpoint = len(records) // 2
        return adaptive_preflight_query(
            endpoint, timeout, records[:midpoint], label, query_factory
        ) + adaptive_preflight_query(
            endpoint, timeout, records[midpoint:], label, query_factory
        )


def live_graph_state(endpoint: str, timeout: int, inventory: dict[str, Any]) -> dict[str, Any]:
    records = [inventory["games"][game_pk] for game_pk in sorted(inventory["games"], key=int)]
    dimension_source = GAME_DIMENSION_QUERY.read_text(encoding="utf-8")
    dimensions: list[dict[str, Any]] = []
    source_state_bindings: list[dict[str, Any]] = []
    index_state_bindings: list[dict[str, Any]] = []
    batches = graph_batches(records, LIVE_PREFLIGHT_BATCH_SIZE)
    for batch in batches:
        dimensions.extend(
            adaptive_preflight_query(
                endpoint,
                timeout,
                batch,
                "dimension query",
                lambda subset: bounded_query_for_graphs(
                    dimension_source,
                    [record["authoritativeGraph"] for record in subset],
                ),
            )
        )
        source_state_bindings.extend(
            adaptive_preflight_query(
                endpoint, timeout, batch, "source-count query", live_source_graph_state_query
            )
        )
        index_state_bindings.extend(
            adaptive_preflight_query(
                endpoint, timeout, batch, "index-count query", live_index_graph_state_query
            )
        )
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

    source_counts: dict[str, int] = {}
    for binding in source_state_bindings:
        source_graph = lexical(binding, "sourceGraph") or ""
        record = by_graph.get(source_graph)
        if record is None:
            raise ValueError(f"Live source-count query returned an unpromoted graph: {source_graph}")
        if source_graph in source_counts:
            raise ValueError(f"Live source-count query returned duplicate state: {source_graph}")
        if lexical(binding, "game") != record["gameIri"]:
            raise ValueError(f"Live source graph identity differs from promotion evidence: {source_graph}")
        try:
            source_count = int(lexical(binding, "sourceCount") or "")
        except ValueError as exc:
            raise ValueError(f"Live source count is invalid for {source_graph}") from exc
        if source_count != record["authoritativeTripleCount"]:
            raise ValueError(f"Live authoritative triple count differs from promotion evidence: {source_graph}")
        source_counts[source_graph] = source_count

    index_states: dict[str, dict[str, Any]] = {}
    for binding in index_state_bindings:
        source_graph = lexical(binding, "sourceGraph") or ""
        record = by_graph.get(source_graph)
        if record is None:
            raise ValueError(f"Live index-count query returned an unpromoted graph: {source_graph}")
        if source_graph in index_states:
            raise ValueError(f"Live index-count query returned duplicate state: {source_graph}")
        if (
            lexical(binding, "indexGraph") != record["queryIndexGraph"]
            or lexical(binding, "game") != record["gameIri"]
            or lexical(binding, "indexResource") != record["queryIndexResource"]
        ):
            raise ValueError(f"Live graph-pair identity differs from promotion evidence: {source_graph}")
        try:
            index_count = int(lexical(binding, "indexCount") or "")
        except ValueError as exc:
            raise ValueError(f"Live index count is invalid for {source_graph}") from exc
        if index_count != record["queryIndexTripleCount"]:
            raise ValueError(f"Live query-index triple count differs from promotion evidence: {source_graph}")
        index_states[source_graph] = {
            "indexGraph": record["queryIndexGraph"],
            "game": record["gameIri"],
            "indexResource": record["queryIndexResource"],
            "indexCount": index_count,
        }

    missing_source_counts = sorted(set(by_graph) - set(source_counts))
    if missing_source_counts:
        raise ValueError(
            "Valid promotion evidence has no matching live authoritative graph: "
            + ", ".join(missing_source_counts[:5])
        )
    missing_index_states = sorted(set(by_graph) - set(index_states))
    if missing_index_states:
        raise ValueError(
            "Valid promotion evidence has no matching live query-index graph: "
            + ", ".join(missing_index_states[:5])
        )

    graph_states: dict[str, dict[str, Any]] = {}
    for source_graph in sorted(by_graph):
        index_state = index_states[source_graph]
        graph_states[source_graph] = {
            "sourceGraph": source_graph,
            "indexGraph": index_state["indexGraph"],
            "game": index_state["game"],
            "indexResource": index_state["indexResource"],
            "sourceCount": source_counts[source_graph],
            "indexCount": index_state["indexCount"],
        }

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


def development_inventory_subset(
    inventory: dict[str, Any], max_games: int | None
) -> dict[str, Any]:
    if not max_games:
        return inventory
    selected_ids = sorted(inventory["games"], key=int)[:max_games]
    selected = {game_pk: inventory["games"][game_pk] for game_pk in selected_ids}
    subset = {**inventory, "games": selected, "gameCount": len(selected)}
    subset["fingerprint"] = sha256_bytes(
        (
            inventory["fingerprint"]
            + "|focused-development-subset|"
            + "|".join(selected_ids)
        ).encode("utf-8")
    )
    return subset


def corpus_snapshot(
    state_root: Path, endpoint: str, timeout: int, max_games: int | None = None
) -> dict[str, Any]:
    inventory_before = promotion_inventory(state_root)
    inventory_before = development_inventory_subset(inventory_before, max_games)
    live = live_graph_state(endpoint, timeout, inventory_before)
    inventory_after = promotion_inventory(state_root)
    inventory_after = development_inventory_subset(inventory_after, max_games)
    if inventory_after["fingerprint"] != inventory_before["fingerprint"]:
        raise RuntimeError("Promotion inventory changed while the live graph-state snapshot was captured")
    fingerprint = sha256_bytes(
        f"{inventory_before['fingerprint']}|{live['fingerprint']}".encode("utf-8")
    )
    return {"fingerprint": fingerprint, "inventory": inventory_before, "live": live}


def bounded_query(source: str, graph: str) -> str:
    has_authoritative_clause = "GRAPH ?graph" in source
    has_index_clause = "GRAPH ?indexGraph" in source and "idx:sourceGraph ?graph" in source
    if not has_authoritative_clause and not has_index_clause:
        raise ValueError("Reviewed serving query has no graph-scoping clause")
    if not graph.startswith(GRAPH_PREFIX) or not graph[len(GRAPH_PREFIX):].isdigit():
        raise ValueError(f"Unsafe authoritative graph: {graph}")
    game_pk = graph[len(GRAPH_PREFIX):]
    index_graph = f"{INDEX_GRAPH_PREFIX}{game_pk}"
    query = source.replace("GRAPH ?graph", f"GRAPH <{graph}>")
    query = query.replace("idx:sourceGraph ?graph", f"idx:sourceGraph <{graph}>")
    query = query.replace(GRAPH_GUARD, "")
    if "GRAPH ?indexGraph" in query:
        query = query.replace("GRAPH ?indexGraph", f"GRAPH <{index_graph}>")
        query = query.replace(INDEX_GRAPH_GUARD, "")
    return query


def bounded_dsq_query(source: str, graph: str, execution_layer: str) -> str:
    if execution_layer == "authoritative":
        return bounded_query(source, graph)
    if execution_layer != "indexed":
        raise ValueError(f"Unsupported DSQ execution layer: {execution_layer}")
    if not graph.startswith(GRAPH_PREFIX) or not graph[len(GRAPH_PREFIX):].isdigit():
        raise ValueError(f"Unsafe authoritative graph: {graph}")
    if "GRAPH ?graph" not in source:
        raise ValueError("Reviewed indexed DSQ has no graph-scoping clause")
    game_pk = graph[len(GRAPH_PREFIX):]
    index_graph = f"{INDEX_GRAPH_PREFIX}{game_pk}"
    return source.replace("GRAPH ?graph", f"GRAPH <{index_graph}>")


def restore_scoped_graph_bindings(
    payload: dict[str, Any], graph: str, graph_binding: str | None = None
) -> dict[str, Any]:
    """Restore projected graph bindings after exact named-graph substitution."""
    variables = payload.get("head", {}).get("vars", [])
    bindings = payload.get("results", {}).get("bindings", [])
    game_pk = graph[len(GRAPH_PREFIX):]
    scoped = {
        "graph": {"type": "uri", "value": graph_binding or graph},
        "indexGraph": {"type": "uri", "value": f"{INDEX_GRAPH_PREFIX}{game_pk}"},
    }
    for variable, value in scoped.items():
        if variable in variables:
            for binding in bindings:
                existing = binding.get(variable)
                if existing is not None and existing != value:
                    raise ValueError(f"Serving query escaped its fixed {variable} scope")
                binding[variable] = value
    return payload


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
    dsq_catalog = json.loads(DSQ_MATERIALIZATIONS.read_text(encoding="utf-8"))
    advanced_entries = catalog.get("queries", [])
    reducer_ids = set(reducers.get("detailQueries", [])) | set(reducers.get("additiveQueries", {}))
    query_ids = {entry.get("id") for entry in advanced_entries}
    ordering_ids = set(reducers.get("ordering", {}))
    if len(advanced_entries) != 17 or query_ids != reducer_ids or query_ids != ordering_ids:
        raise ValueError("Advanced serving reducers do not cover the reviewed query catalog exactly")
    dsq_entries = load_dsq_entries(dsq_catalog, catalog, reducers)
    dsq_by_id = {entry["id"]: entry for entry in dsq_entries}
    canned_dsq_entries = [entry for entry in dsq_entries if entry["kind"] == "canned"]
    advanced_sources = {
        entry["id"]: (ROOT / entry["path"]).read_text(encoding="utf-8")
        for entry in advanced_entries
    }
    canned_dsq_sources = {
        entry["id"]: (ROOT / entry["executionPath"]).read_text(encoding="utf-8")
        for entry in canned_dsq_entries
    }
    explore_sources = {name: path.read_text(encoding="utf-8") for name, path in EXPLORE_GRAIN_QUERIES.items()}
    started = time.perf_counter()
    snapshot_started = time.perf_counter()
    initial_snapshot = corpus_snapshot(
        state_root, args.endpoint, args.timeout, args.max_games
    )
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
    dsq_states = {
        entry["id"]: {"variables": None, "count": 0}
        for entry in dsq_entries
    }
    sparql_durations: list[float] = []
    advanced_sparql_durations: dict[str, list[float]] = {entry["id"]: [] for entry in advanced_entries}
    canned_dsq_sparql_durations: dict[str, list[float]] = {
        entry["id"]: [] for entry in canned_dsq_entries
    }
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
        *(entry["table"] for entry in dsq_entries),
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
            if (
                provenance_set
                and rdf_game_set
                and provenance_set != rdf_game_set
                and provenance_set != "fixture"
            ):
                raise ValueError(
                    f"Persistent game-set provenance conflicts with authoritative RDF for game {game_pk}: "
                    f"{provenance_set!r} != {rdf_game_set!r}"
                )
            # Fixture membership is corpus provenance, not a baseball game
            # classification. It deliberately overrides the RDF game-set value
            # only in this disposable serving build so fixtures never enter a
            # user-selectable baseball competition pool.
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
            try:
                payload = restore_scoped_graph_bindings(
                    sparql(args.endpoint, bounded_query(query_source, graph), args.timeout), graph
                )
            except Exception as exc:
                raise RuntimeError(
                    f"Serving query plate-appearance-fingerprint failed for {graph}: {exc}"
                ) from exc
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
                    try:
                        advanced_payload = restore_scoped_graph_bindings(
                            sparql(args.endpoint, bounded_query(source, graph), args.timeout), graph
                        )
                    except Exception as exc:
                        raise RuntimeError(
                            f"Serving advanced query {query_id} failed for {graph}: {exc}"
                        ) from exc
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
                insert_dsq_payload(
                    connection,
                    dsq_by_id[query_id],
                    graph,
                    advanced_payload,
                    dsq_states[query_id],
                    record_source_row,
                )
            def execute_canned_dsq(entry: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], float]:
                query_id = entry["id"]
                dsq_started = time.perf_counter()
                try:
                    dsq_payload = restore_scoped_graph_bindings(
                        sparql(
                            args.endpoint,
                            bounded_dsq_query(
                                canned_dsq_sources[query_id], graph, entry["executionLayer"]
                            ),
                            args.timeout,
                        ),
                        graph,
                        (
                            f"{INDEX_GRAPH_PREFIX}{graph[len(GRAPH_PREFIX):]}"
                            if entry["executionLayer"] == "indexed"
                            else graph
                        ),
                    )
                except Exception as exc:
                    raise RuntimeError(
                        f"Serving DSQ {query_id} failed for {graph}: {exc}"
                    ) from exc
                return entry, dsq_payload, (time.perf_counter() - dsq_started) * 1000

            with ThreadPoolExecutor(max_workers=getattr(args, "dsq_workers", 2)) as executor:
                canned_results = executor.map(execute_canned_dsq, canned_dsq_entries)
                for entry, dsq_payload, dsq_duration in canned_results:
                    query_id = entry["id"]
                    canned_dsq_sparql_durations[query_id].append(dsq_duration)
                    insert_dsq_payload(
                        connection,
                        entry,
                        graph,
                        dsq_payload,
                        dsq_states[query_id],
                        record_source_row,
                    )
            for grain_name, source in explore_sources.items():
                grain_started = time.perf_counter()
                try:
                    grain_payload = restore_scoped_graph_bindings(
                        sparql(args.endpoint, bounded_query(source, graph), args.timeout), graph
                    )
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
        for entry in dsq_entries:
            state = dsq_states[entry["id"]]
            if state["variables"] is None:
                raise ValueError(f"DSQ was not materialized: {entry['id']}")
            connection.execute(
                "INSERT INTO dsq_query_manifest VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    entry["id"],
                    entry["family"],
                    entry["kind"],
                    entry["path"],
                    entry["table"],
                    sha256_file(ROOT / entry["path"]),
                    entry["executionLayer"],
                    entry["executionPath"],
                    sha256_file(ROOT / entry["executionPath"]),
                    json.dumps(
                        entry["reducer"], ensure_ascii=False, sort_keys=True, separators=(",", ":")
                    ),
                    json.dumps(state["variables"], ensure_ascii=False, separators=(",", ":")),
                    state["count"],
                ),
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
        dsq_hash_mismatches = sum(
            sha256_bytes(binding.encode("utf-8")) != digest
            for entry in dsq_entries
            for binding, digest in connection.execute(
                f'SELECT binding_json,binding_sha256 FROM "{entry["table"]}"'
            )
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
            **{
                entry["table"]: (
                    f'SELECT graph_iri,row_ordinal,binding_json FROM "{entry["table"]}" ORDER BY rowid'
                )
                for entry in dsq_entries
            },
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
            or dsq_hash_mismatches
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

    dsq_binding_count = sum(state["count"] for state in dsq_states.values())
    dsq_bindings_by_query = {
        query_id: state["count"] for query_id, state in sorted(dsq_states.items())
    }
    dsq_execution_layers = {
        layer: sum(entry["executionLayer"] == layer for entry in dsq_entries)
        for layer in ("authoritative", "indexed")
    }
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
        "dsqQueryCount": len(dsq_entries),
        "dsqBindingCount": dsq_binding_count,
        "dsqBindingsByQuery": dsq_bindings_by_query,
        "dsqExecutionLayers": dsq_execution_layers,
        "exploreCounts": explore_counts,
        "emptyPlayerGameCount": empty_player_games,
        "integrity": {
            "sqliteIntegrityCheck": integrity,
            "foreignKeyIssueCount": len(foreign_key_issues),
            "checkedBindingHashes": rows + advanced_rows + dsq_binding_count + explore_counts["damage"],
            "bindingHashMismatches": (
                hash_mismatches
                + advanced_hash_mismatches
                + dsq_hash_mismatches
                + damage_hash_mismatches
            ),
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
            "dsqReadOnlyWorkers": getattr(args, "dsq_workers", 2),
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
            "cannedDsqSparqlByQuery": {
                query_id: {
                    "calls": len(durations),
                    "totalMs": round(sum(durations), 1),
                    "medianPerGameMs": round(statistics.median(durations), 1),
                }
                for query_id, durations in sorted(canned_dsq_sparql_durations.items())
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
        "dsqMaterializationCatalogSha256": sha256_file(DSQ_MATERIALIZATIONS),
        "dsqQuerySetSha256": dsq_query_set_sha256(dsq_entries),
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
            "dsqMaterializationCatalogSha256": evidence["dsqMaterializationCatalogSha256"],
            "dsqQuerySetSha256": evidence["dsqQuerySetSha256"],
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
            "dsqQueryCount": len(dsq_entries),
            "dsqBindingCount": dsq_binding_count,
            "dsqExecutionLayers": dsq_execution_layers,
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
    parser.add_argument(
        "--dsq-workers",
        type=int,
        choices=range(1, 5),
        default=2,
        help="Concurrent read-only DSQ SELECT workers (1-4; default 2)",
    )
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
