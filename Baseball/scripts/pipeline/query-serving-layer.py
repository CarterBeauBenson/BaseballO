#!/usr/bin/env python3
"""Read-only adapter for reviewed Explorer results in the promoted SQLite build."""

from __future__ import annotations

import argparse
import functools
import hashlib
import importlib.util
import json
import os
import re
import sqlite3
import sys
import tempfile
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
_metric_spec = importlib.util.spec_from_file_location('baseballo_metric_suite', ROOT / 'serving/metric_suite.py')
_metric_suite = importlib.util.module_from_spec(_metric_spec)
_metric_spec.loader.exec_module(_metric_suite)
GAME_SETS = frozenset(
    {"regular_season", "preseason", "postseason", "exhibition", "all_star"}
)
SCHEMA = ROOT / "serving" / "schema.sql"
CONTRACT = ROOT / "serving" / "contract.json"
QUALITY_SPEC = ROOT / "serving" / "plate-appearance-quality-v1.json"
SOURCE_QUERY = ROOT / "sparql" / "advanced" / "plate-appearance-fingerprint.rq"
ADVANCED_CATALOG = ROOT / "sparql" / "advanced" / "advanced-query-catalog.json"
ADVANCED_REDUCERS = ROOT / "serving" / "advanced-query-reducers.json"
DSQ_MATERIALIZATIONS = ROOT / "serving" / "dsq-materializations.json"
QUERY_INDEX_ROUTING = ROOT / "sparql" / "query-index" / "operational-query-routing.json"
EXPLORE_GRAIN_QUERIES = {
    "batting": ROOT / "sparql" / "serving" / "explore-batting-grain.rq",
    "pitching": ROOT / "sparql" / "serving" / "explore-pitching-grain.rq",
    "baserunning": ROOT / "sparql" / "serving" / "explore-baserunning-grain.rq",
    "assignments": ROOT / "sparql" / "serving" / "explore-assignment-grain.rq",
    "damage": ROOT / "sparql" / "serving" / "empty-damage-opportunity-grain.rq",
}
GAME_DIMENSION_QUERY = ROOT / "sparql" / "serving" / "game-dimension.rq"
SERVING_QUERY_FILES = {**EXPLORE_GRAIN_QUERIES, "dimensions": GAME_DIMENSION_QUERY}
MATERIALIZER = ROOT / "scripts" / "pipeline" / "materialize-serving-layer.py"
MAPPING = ROOT / "sources" / "mlb-game" / "mapping" / "mlb-game.rml.ttl"
VALIDATOR = Path(__file__).resolve()
DATA_PREFIX = "https://baseballontology.org/data/"
DATE_PRESETS = {"one_day", "seven_days", "thirty_days", "season_to_date", "custom"}
XSD = "http://www.w3.org/2001/XMLSchema#"
MAX_RESULTS = 1000
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
PAQ_OPTION_REQUESTS = frozenset({
    ("games", "season"),
    ("games", "game"),
    ("games", "team"),
    ("games", "venue"),
    ("batting", "player"),
    ("pitching", "pitcher"),
})


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def file_identity(path: Path) -> tuple[int, int, int, int, int]:
    metadata = path.stat()
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def hash_database_stream(path: Path, identity: tuple[int, int, int, int, int]) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        opened_identity = (
            opened.st_dev,
            opened.st_ino,
            opened.st_size,
            opened.st_mtime_ns,
            opened.st_ctime_ns,
        )
        if opened_identity != identity:
            raise ValueError("Serving database changed before integrity verification")
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
        closed = os.fstat(stream.fileno())
        closed_identity = (
            closed.st_dev,
            closed.st_ino,
            closed.st_size,
            closed.st_mtime_ns,
            closed.st_ctime_ns,
        )
        if closed_identity != identity:
            raise ValueError("Serving database changed during integrity verification")
    return digest.hexdigest()


def identity_record(identity: tuple[int, int, int, int, int]) -> dict[str, int]:
    return dict(zip(("device", "inode", "size", "mtimeNs", "ctimeNs"), identity))


def cached_database_identity(
    cache_path: Path,
    expected_sha256: str,
    database: Path,
) -> tuple[int, int, int, int, int] | None:
    try:
        cache = json.loads(cache_path.read_text(encoding="utf-8-sig"))
        if (
            not isinstance(cache, dict)
            or cache.get("artifactType") != "baseball-serving-database-verification-cache"
            or cache.get("contractVersion") != 1
            or not isinstance(cache.get("entries"), dict)
        ):
            return None
        entry = cache["entries"].get(expected_sha256)
        if not isinstance(entry, dict) or entry.get("databasePath") != str(database):
            return None
        record = entry.get("identity")
        fields = ("device", "inode", "size", "mtimeNs", "ctimeNs")
        if not isinstance(record, dict) or any(
            isinstance(record.get(field), bool) or not isinstance(record.get(field), int)
            for field in fields
        ):
            return None
        return tuple(record[field] for field in fields)  # type: ignore[return-value]
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return None


def write_database_verification_cache(
    cache_path: Path,
    expected_sha256: str,
    database: Path,
    identity: tuple[int, int, int, int, int],
) -> None:
    cache = {
        "artifactType": "baseball-serving-database-verification-cache",
        "contractVersion": 1,
        "entries": {
            expected_sha256: {
                "databasePath": str(database),
                "identity": identity_record(identity),
            }
        },
    }
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", delete=False, dir=cache_path.parent
    ) as output:
        json.dump(cache, output, indent=2, ensure_ascii=False)
        output.write("\n")
        temporary = Path(output.name)
    try:
        os.replace(temporary, cache_path)
    finally:
        temporary.unlink(missing_ok=True)


def verify_database(
    path: Path,
    expected: object,
    cache_path: Path,
) -> tuple[int, int, int, int, int]:
    expected_sha256 = str(expected).lower()
    if not SHA256_PATTERN.fullmatch(expected_sha256):
        raise ValueError("Serving pointer has an invalid databaseSha256")
    identity = file_identity(path)
    cached = cached_database_identity(cache_path, expected_sha256, path)
    if cached == identity:
        verified = cached
    else:
        if hash_database_stream(path, identity) != expected_sha256:
            raise ValueError("Serving database hash does not match its promotion pointer")
        verified = identity
        write_database_verification_cache(
            cache_path, expected_sha256, path, verified
        )
    if file_identity(path) != verified:
        raise ValueError("Serving database changed after integrity verification")
    return verified


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def require_materialized_route_admission(request: dict[str, Any], contract: dict[str, Any]) -> None:
    if (
        contract.get("artifactType") != "baseball-analytical-serving-contract"
        or contract.get("contractVersion") != 5
    ):
        raise ValueError("Unsupported analytical serving admission contract")
    route = request.get("route")
    if route == 'metric-suite':
        # This new route is an evidence/status surface, not blanket admission
        # of PAQ-2 or any unresolved semantic family. query_sql independently
        # enforces the pinned suite manifest and every metric's prerequisites.
        suite = contract.get('metricSuite', {})
        if (suite.get('route') != route or suite.get('liveAvailability') != 'per-metric-evidence-gated'
                or suite.get('schema') != 'serving/metric-suite-schema.sql'
                or suite.get('implementation') != 'serving/metric_suite.py'):
            raise ValueError('Unsupported metric suite evidence contract')
        if request.get('metricId') not in {entry['id'] for entry in _metric_suite.catalog()['metrics']}:
            raise ValueError('Unknown metric')
        return
    if route == "options":
        contract_route = "options"
    elif route == "explore":
        contract_route = "explore"
    elif route in {"empty-games", "derived"}:
        contract_route = "empty-games-and-derived"
    elif route is None:
        contract_route = (
            "plate-appearance-fingerprint"
            if request.get("id") == "plate-appearance-fingerprint"
            else "advanced-reviewed-catalog"
        )
    else:
        raise ValueError(f"Unsupported materialized route: {route}")
    route_contract = contract.get("routes", {}).get(contract_route)
    status = route_contract.get("status") if isinstance(route_contract, dict) else None
    if not isinstance(status, str) or not status.startswith("admitted-"):
        raise ValueError(
            f"Serving contract route {contract_route} is not admitted to materialized SQL"
        )
    if route == "options":
        option_request = (request.get("family"), request.get("dimension"))
        if option_request not in PAQ_OPTION_REQUESTS:
            raise ValueError(
                "Serving contract admits SQL options only for the PAQ/Good At Bat visible slice"
            )


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


def dsq_query_set_sha256(
    dsq_catalog: dict[str, Any],
    advanced_catalog: dict[str, Any],
    advanced_reducers: dict[str, Any],
    routing: dict[str, Any],
) -> str:
    entries: list[tuple[str, str, str, str, dict[str, Any]]] = []
    routes = {
        str(route["authoritative"]): route
        for route in routing.get("routes", [])
        if isinstance(route, dict) and route.get("authoritative")
    }
    details = set(advanced_reducers.get("detailQueries", []))
    additive = advanced_reducers.get("additiveQueries", {})
    for entry in advanced_catalog.get("queries", []):
        query_id = str(entry["id"])
        if query_id in details:
            filter_dimensions = [
                str(value["variable"])
                for value in entry.get("resultFilters", [])
                if isinstance(value, dict) and value.get("variable")
            ]
            reducer = {
                "mode": "detail",
                "dimensions": list(dict.fromkeys(filter_dimensions)),
                "sums": [],
            }
        else:
            reducer = {"mode": "additive", **additive[query_id]}
        query_path = str(entry["path"])
        entries.append((query_id, query_path, "authoritative", query_path, reducer))
    for entry in dsq_catalog.get("cannedQueries", []):
        query_path = str(entry["path"])
        route = routes.get(query_path)
        execution_layer = "indexed" if route and route.get("autoLayer") == "indexed" else "authoritative"
        execution_path = str(route["indexed"]) if execution_layer == "indexed" else query_path
        entries.append(
            (str(entry["id"]), query_path, execution_layer, execution_path, entry["reducer"])
        )
    digest = hashlib.sha256()
    for query_id, query_path, execution_layer, execution_path, reducer in sorted(entries):
        digest.update(query_id.encode("utf-8"))
        digest.update(b"\0")
        digest.update((ROOT / query_path).read_bytes())
        digest.update(b"\0")
        digest.update(execution_layer.encode("utf-8"))
        digest.update(b"\0")
        digest.update((ROOT / execution_path).read_bytes())
        digest.update(b"\0")
        digest.update(
            json.dumps(reducer, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        )
        digest.update(b"\0")
    return digest.hexdigest()


def integer_binding(value: int) -> dict[str, str]:
    return {"type": "literal", "datatype": f"{XSD}integer", "value": str(value)}


def uri_binding(value: str) -> dict[str, str]:
    return {"type": "uri", "value": value}


def literal_binding(value: Any, datatype: str | None = None) -> dict[str, str]:
    result = {"type": "literal", "value": str(value)}
    if datatype:
        result["datatype"] = f"{XSD}{datatype}"
    return result


def decimal_binding(value: float) -> dict[str, str]:
    return {"type": "literal", "datatype": f"{XSD}decimal", "value": f"{value:.2f}"}


def sort_bindings(query_id: str, rows: list[dict[str, Any]], reducers: dict[str, Any]) -> None:
    order = reducers.get("ordering", {}).get(query_id)
    if not order:
        raise ValueError(f"No reviewed SQL ordering contract for: {query_id}")

    def compare(left: dict[str, Any], right: dict[str, Any]) -> int:
        for term in order:
            descending = term.startswith("-")
            token = term[1:] if descending else term
            numeric = token.startswith("#")
            variable = token[1:] if numeric else token
            left_value = left.get(variable, {}).get("value")
            right_value = right.get(variable, {}).get("value")
            if left_value == right_value:
                continue
            if left_value is None:
                result = -1
            elif right_value is None:
                result = 1
            else:
                if numeric:
                    left_value, right_value = float(left_value), float(right_value)
                else:
                    left_value, right_value = str(left_value).casefold(), str(right_value).casefold()
                result = -1 if left_value < right_value else 1
            return -result if descending else result
        return 0

    rows.sort(key=functools.cmp_to_key(compare))


def reduce_advanced(query_id: str, bindings: list[dict[str, Any]], reducers: dict[str, Any]) -> list[dict[str, Any]]:
    if query_id in reducers["detailQueries"]:
        sort_bindings(query_id, bindings, reducers)
        return bindings[:MAX_RESULTS]
    contract = reducers["additiveQueries"].get(query_id)
    if not contract:
        raise ValueError(f"No SQL reducer for reviewed query: {query_id}")
    groups: dict[str, dict[str, Any]] = {}
    for binding in bindings:
        key = json.dumps(
            [binding.get(variable) for variable in contract["dimensions"]],
            ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        )
        row = groups.setdefault(key, {
            **{variable: binding[variable] for variable in contract["dimensions"] if variable in binding},
            **{variable: integer_binding(0) for variable in contract["sums"]},
        })
        for variable in contract["sums"]:
            current = int(row[variable]["value"])
            current += int(float(binding.get(variable, {}).get("value", "0")))
            row[variable] = integer_binding(current)
    rows = list(groups.values())
    if contract.get("derived") == "steal-efficiency":
        for row in rows:
            attempts = int(row["attempts"]["value"])
            successes = int(row["successfulSteals"]["value"])
            caught = int(row["caughtStealing"]["value"])
            row["unresolvedAttempts"] = integer_binding(attempts - successes - caught)
            if attempts:
                row["successPercent"] = decimal_binding(round(10000.0 * successes / attempts) / 100)
    sort_bindings(query_id, rows, reducers)
    return rows[:MAX_RESULTS]


def query_advanced(
    connection: sqlite3.Connection,
    request: dict[str, Any],
    build: tuple[Any, ...],
    scope: dict[str, Any],
    started: float,
    catalog: dict[str, Any],
    reducers: dict[str, Any],
) -> dict[str, Any]:
    query_id = str(request.get("id", ""))
    entry = next((value for value in catalog["queries"] if value["id"] == query_id), None)
    if entry is None:
        raise ValueError(f"Unknown reviewed query: {query_id}")
    filters = request.get("filters") or {}
    if not isinstance(filters, dict):
        raise ValueError("filters must be an object")
    declarations = {value["id"]: value["variable"] for value in entry.get("resultFilters", [])}
    allowed = {"season", "game", "venue", "team", *declarations}
    unknown = set(filters) - allowed
    if unknown:
        raise ValueError(f"Unsupported filter: {sorted(unknown)[0]}")
    clauses = ["r.query_id=?", "g.game_set=?", "g.official_date BETWEEN ? AND ?"]
    parameters: list[Any] = [query_id, scope["gameSet"], scope["startDate"], scope["endDate"]]
    for field, column in (("game", "g.game_iri"), ("venue", "g.venue_iri")):
        if field in filters:
            clauses.append(f"{column}=?")
            parameters.append(canonical_iri(filters[field], field))
    if "team" in filters:
        team = canonical_iri(filters["team"], "team")
        clauses.append("(g.home_team_iri=? OR g.away_team_iri=?)")
        parameters.extend([team, team])
    if "season" in filters:
        season = filters["season"]
        if not isinstance(season, int) or not 1800 <= season <= 3000:
            raise ValueError("season must be an integer between 1800 and 3000")
        clauses.append("g.season=?")
        parameters.append(season)
    sql = (
        "SELECT r.binding_json FROM advanced_result_fact r "
        "JOIN game_dimension g USING(graph_iri) WHERE " + " AND ".join(clauses)
        + " ORDER BY r.graph_iri,r.row_ordinal"
    )
    bindings = [json.loads(row[0]) for row in connection.execute(sql, parameters)]
    for filter_id, variable in declarations.items():
        if filter_id in filters:
            expected = canonical_iri(filters[filter_id], filter_id)
            bindings = [row for row in bindings if row.get(variable, {}).get("value") == expected]
    variables_row = connection.execute(
        "SELECT variables_json FROM advanced_query_manifest WHERE query_id=?", (query_id,)
    ).fetchone()
    if not variables_row:
        raise ValueError(f"Reviewed query is absent from serving build: {query_id}")
    variables = json.loads(variables_row[0])
    reduced = reduce_advanced(query_id, bindings, reducers)
    game_clauses = [clause for clause in clauses if clause != "r.query_id=?"]
    game_count = connection.execute(
        "SELECT COUNT(*) FROM game_dimension g WHERE " + " AND ".join(game_clauses),
        parameters[1:],
    ).fetchone()[0]
    scope["gameCount"] = game_count
    return {
        "head": {"vars": variables},
        "results": {"bindings": reduced},
        "query": f"-- Materialized reviewed SPARQL: {entry['path']}\n{sql}",
        "serving": {
            "durationMs": round((time.perf_counter() - started) * 1000, 3),
            "buildId": build[0], "corpusFingerprint": build[1], "filters": filters,
            "dateScope": scope, "view": "reviewed_query", "queryId": query_id,
            "coverage": serving_coverage(build),
        },
    }


def canonical_iri(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.startswith(DATA_PREFIX) or any(character.isspace() or character in "<>" for character in value):
        raise ValueError(f"{field} must be a canonical BaseballO data IRI")
    return value


def iso_date(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must use YYYY-MM-DD")
    try:
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError
    except ValueError as exc:
        raise ValueError(f"{field} must use YYYY-MM-DD") from exc
    return value


def resolve_scope(connection: sqlite3.Connection, request: dict[str, Any]) -> dict[str, Any]:
    game_set = request.get("gameSet", "regular_season")
    if game_set not in GAME_SETS:
        raise ValueError(f"Unsupported game set: {game_set}")
    available = connection.execute(
        "SELECT MIN(official_date),MAX(official_date) FROM game_dimension WHERE game_set=?", (game_set,)
    ).fetchone()
    available_start, available_end = available
    scope = request.get("dateScope") or {"preset": "seven_days"}
    if not isinstance(scope, dict):
        raise ValueError("dateScope must be an object")
    preset = scope.get("preset", "seven_days")
    if preset not in DATE_PRESETS:
        raise ValueError(f"Unsupported date preset: {preset}")
    start = available_end
    end = available_end
    if preset == "custom":
        start = iso_date(scope.get("startDate"), "startDate")
        end = iso_date(scope.get("endDate"), "endDate")
        if start > end:
            raise ValueError("startDate must not be after endDate")
    elif available_end:
        end_date = date.fromisoformat(available_end)
        if preset == "seven_days":
            start = (end_date - timedelta(days=6)).isoformat()
        elif preset == "thirty_days":
            start = (end_date - timedelta(days=29)).isoformat()
        elif preset == "season_to_date":
            start = f"{available_end[:4]}-01-01"
    return {
        "preset": preset, "startDate": start, "endDate": end,
        "availableStartDate": available_start, "availableEndDate": available_end,
        "dateBasis": "official-source", "gameSet": game_set,
    }


COMMON_DIMENSIONS = {
    "season": [("season", "g.season", "integer")],
    "venue": [("venue", "g.venue_iri", "uri"), ("venueLabel", "g.venue_label", "literal")],
    "game": [("game", "g.game_iri", "uri"), ("gameStart", "g.game_start", "dateTime")],
}
EXPLORE_FAMILIES = {
    "batting": {
        "from": "batting_result_fact f JOIN game_dimension g USING(graph_iri)",
        "dimensions": {**COMMON_DIMENSIONS,
            "player": [("player", "f.player_iri", "uri"), ("playerLabel", "f.player_label", "literal")],
            "team": [("team", "f.team_iri", "uri"), ("teamLabel", "f.team_label", "literal")],
            "event_type": [("eventType", "f.event_type", "literal")],
        },
        "metrics": {
            "plate_appearances": ("plateAppearances", "COUNT(DISTINCT f.result_iri)"),
            "hits": ("hits", "SUM(CASE WHEN f.event_type IN ('single','double','triple','home_run') THEN 1 ELSE 0 END)"),
            "singles": ("singles", "SUM(CASE WHEN f.event_type='single' THEN 1 ELSE 0 END)"),
            "doubles": ("doubles", "SUM(CASE WHEN f.event_type='double' THEN 1 ELSE 0 END)"),
            "triples": ("triples", "SUM(CASE WHEN f.event_type='triple' THEN 1 ELSE 0 END)"),
            "home_runs": ("homeRuns", "SUM(CASE WHEN f.event_type='home_run' THEN 1 ELSE 0 END)"),
            "walks": ("walks", "SUM(CASE WHEN f.event_type='walk' THEN 1 ELSE 0 END)"),
            "strikeouts": ("strikeouts", "SUM(CASE WHEN f.event_type='strikeout' THEN 1 ELSE 0 END)"),
            "total_bases": ("totalBases", "SUM(CASE f.event_type WHEN 'single' THEN 1 WHEN 'double' THEN 2 WHEN 'triple' THEN 3 WHEN 'home_run' THEN 4 ELSE 0 END)"),
            "games": ("games", "COUNT(DISTINCT g.game_iri)"),
        },
    },
    "pitching": {
        "from": "pitch_fact f JOIN game_dimension g USING(graph_iri)",
        "dimensions": {**COMMON_DIMENSIONS,
            "pitcher": [("pitcher", "f.pitcher_iri", "uri"), ("pitcherLabel", "f.pitcher_label", "literal")],
            "team": [("team", "f.team_iri", "uri"), ("teamLabel", "f.team_label", "literal")],
        },
        "metrics": {
            "pitches": ("pitches", "COUNT(DISTINCT f.pitch_iri)"),
            "balls": ("balls", "SUM(CASE WHEN f.pitch_call_code IN ('B','*B') THEN 1 ELSE 0 END)"),
            "called_strikes": ("calledStrikes", "SUM(CASE WHEN f.pitch_call_code='C' THEN 1 ELSE 0 END)"),
            "swinging_strikes": ("swingingStrikes", "SUM(CASE WHEN f.pitch_call_code IN ('S','W','M') THEN 1 ELSE 0 END)"),
            "fouls": ("fouls", "SUM(CASE WHEN f.pitch_call_code IN ('F','T','L') THEN 1 ELSE 0 END)"),
            "in_play": ("inPlay", "SUM(CASE WHEN f.pitch_call_code IN ('X','D','E') THEN 1 ELSE 0 END)"),
            "hit_batters": ("hitBatters", "SUM(CASE WHEN f.pitch_call_code='H' THEN 1 ELSE 0 END)"),
            "plate_appearances": ("plateAppearances", "COUNT(DISTINCT f.plate_appearance_iri)"),
            "games": ("games", "COUNT(DISTINCT g.game_iri)"),
        },
    },
    "baserunning": {
        "from": "runner_event_fact f JOIN game_dimension g USING(graph_iri)",
        "dimensions": {**COMMON_DIMENSIONS,
            "player": [("player", "f.player_iri", "uri"), ("playerLabel", "f.player_label", "literal")],
            "team": [("team", "f.team_iri", "uri"), ("teamLabel", "f.team_label", "literal")],
            "event_type": [("eventType", "f.event_type", "literal")],
        },
        "metrics": {
            "runner_events": ("runnerEvents", "COUNT(DISTINCT f.resolution_iri)"),
            "runs": ("runs", "COUNT(DISTINCT CASE WHEN f.resolution_class LIKE '%/RunProcess' THEN f.resolution_iri END)"),
            "outs": ("outs", "COUNT(DISTINCT CASE WHEN f.resolution_class LIKE '%/OutProcess' THEN f.resolution_iri END)"),
            "safe_resolutions": ("safeResolutions", "COUNT(DISTINCT CASE WHEN f.resolution_class LIKE '%/SafeProcess' THEN f.resolution_iri END)"),
            "stolen_bases": ("stolenBases", "COUNT(DISTINCT f.stolen_base_iri)"),
            "games": ("games", "COUNT(DISTINCT g.game_iri)"),
        },
    },
}


def scope_clauses(scope: dict[str, Any], alias: str = "g") -> tuple[list[str], list[Any]]:
    return [f"{alias}.game_set=?", f"{alias}.official_date BETWEEN ? AND ?"], [
        scope["gameSet"], scope["startDate"], scope["endDate"],
    ]


def filter_value(value: Any, field: str, kind: str) -> Any:
    if kind == "uri":
        return canonical_iri(value, field)
    if kind == "integer":
        if not isinstance(value, int) or not 1800 <= value <= 3000:
            raise ValueError(f"{field} must be an integer between 1800 and 3000")
        return value
    values = value if isinstance(value, list) else [value]
    if not values or not all(isinstance(item, str) and item.replace("_", "").isalnum() for item in values):
        raise ValueError(f"Unsupported {field} value")
    return values


def row_binding(names: list[tuple[str, str]], row: tuple[Any, ...]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for (name, kind), value in zip(names, row):
        if value is None:
            continue
        if kind == "uri":
            result[name] = uri_binding(str(value))
        elif kind == "integer":
            result[name] = integer_binding(int(value))
        else:
            result[name] = literal_binding(value, kind if kind in {"dateTime", "decimal", "boolean"} else None)
    return result


def query_explore(connection: sqlite3.Connection, request: dict[str, Any], build: tuple[Any, ...], scope: dict[str, Any], started: float) -> dict[str, Any]:
    family_id = request.get("family")
    dimensions = list(dict.fromkeys(request.get("dimensions") or ["season"]))
    metrics = list(dict.fromkeys(request.get("metrics") or []))
    filters = request.get("filters") or {}
    if family_id == "games":
        return query_games(connection, request, build, scope, started)
    family = EXPLORE_FAMILIES.get(family_id)
    if not family or not metrics or not isinstance(filters, dict):
        raise ValueError("Unsupported Explorer request")
    if any(item not in family["dimensions"] for item in dimensions) or any(item not in family["metrics"] for item in metrics):
        raise ValueError("Unsupported Explorer dimension or metric")
    if any(item not in family["dimensions"] for item in filters):
        raise ValueError("Unsupported Explorer filter")
    selected: list[str] = []
    names: list[tuple[str, str]] = []
    groups: list[str] = []
    for dimension in dimensions:
        for variable, expression, kind in family["dimensions"][dimension]:
            selected.append(f"{expression} AS {variable}")
            names.append((variable, kind))
            groups.append(expression)
    for metric in metrics:
        variable, expression = family["metrics"][metric]
        selected.append(f"{expression} AS {variable}")
        names.append((variable, "integer"))
    clauses, parameters = scope_clauses(scope)
    for dimension, value in filters.items():
        variable, expression, kind = family["dimensions"][dimension][0]
        normalized = filter_value(value, dimension, kind)
        if isinstance(normalized, list):
            clauses.append(f"{expression} IN ({','.join('?' for _ in normalized)})")
            parameters.extend(normalized)
        else:
            clauses.append(f"{expression}=?")
            parameters.append(normalized)
    sort = request.get("sort")
    aliases = {name for name, _ in names}
    if sort is None:
        order = [f"{family['metrics'][metric][0]} DESC" for metric in metrics]
    else:
        if not isinstance(sort, list):
            raise ValueError("sort must be an array")
        component_alias = {key: values[0][0] for key, values in family["dimensions"].items()}
        component_alias.update({key: value[0] for key, value in family["metrics"].items()})
        order = []
        for item in sort:
            alias = component_alias.get(item.get("id")) if isinstance(item, dict) else None
            direction = item.get("direction", "asc") if isinstance(item, dict) else ""
            if alias not in aliases or direction not in {"asc", "desc"}:
                raise ValueError("Unsupported Explorer sort")
            order.append(f"{alias} {direction.upper()}")
    limit = request.get("limit", 250)
    offset = request.get("offset", 0)
    if not isinstance(limit, int) or not 1 <= limit <= MAX_RESULTS or not isinstance(offset, int) or not 0 <= offset <= 100000:
        raise ValueError("Unsupported Explorer page bounds")
    sql = f"SELECT {','.join(selected)} FROM {family['from']} WHERE {' AND '.join(clauses)}"
    if groups:
        sql += " GROUP BY " + ",".join(groups)
    if order:
        sql += " ORDER BY " + ",".join(order)
    sql += " LIMIT ? OFFSET ?"
    rows = connection.execute(sql, [*parameters, limit, offset]).fetchall()
    scope["gameCount"] = connection.execute(
        "SELECT COUNT(*) FROM game_dimension g WHERE g.game_set=? AND g.official_date BETWEEN ? AND ?", parameters[:3]
    ).fetchone()[0]
    return serving_payload(names, rows, sql, build, scope, started, "explore", {"family": family_id})


def query_games(connection: sqlite3.Connection, request: dict[str, Any], build: tuple[Any, ...], scope: dict[str, Any], started: float) -> dict[str, Any]:
    dimensions = list(dict.fromkeys(request.get("dimensions") or ["season"]))
    metrics = list(dict.fromkeys(request.get("metrics") or ["games"]))
    filters = request.get("filters") or {}
    allowed = {"season", "venue", "game", "team", "side", "umpire", "official_scorer"}
    if any(value not in allowed for value in [*dimensions, *filters]) or metrics != ["games"]:
        raise ValueError("Unsupported games request")
    joins = []
    if {"team", "side"} & set([*dimensions, *filters]):
        joins.append("JOIN assignment_fact t ON t.graph_iri=g.graph_iri AND t.assignment_type IN ('home','away')")
    if "umpire" in [*dimensions, *filters]:
        joins.append("JOIN assignment_fact u ON u.graph_iri=g.graph_iri AND u.assignment_type='umpire'")
    if "official_scorer" in [*dimensions, *filters]:
        joins.append("JOIN assignment_fact s ON s.graph_iri=g.graph_iri AND s.assignment_type='official_scorer'")
    definitions = {**COMMON_DIMENSIONS,
        "team": [("team", "t.assignee_iri", "uri"), ("teamLabel", "t.assignee_label", "literal")],
        "side": [("side", "t.assignment_type", "literal")],
        "umpire": [("umpire", "u.assignee_iri", "uri"), ("umpireLabel", "u.assignee_label", "literal")],
        "official_scorer": [("officialScorer", "s.assignee_iri", "uri"), ("officialScorerLabel", "s.assignee_label", "literal")],
    }
    selected, groups, names = [], [], []
    for dimension in dimensions:
        for variable, expression, kind in definitions[dimension]:
            selected.append(f"{expression} AS {variable}"); groups.append(expression); names.append((variable, kind))
    selected.append("COUNT(DISTINCT g.game_iri) AS games"); names.append(("games", "integer"))
    clauses, parameters = scope_clauses(scope)
    for dimension, value in filters.items():
        _, expression, kind = definitions[dimension][0]
        normalized = filter_value(value, dimension, kind)
        if isinstance(normalized, list):
            clauses.append(f"{expression} IN ({','.join('?' for _ in normalized)})")
            parameters.extend(normalized)
        else:
            clauses.append(f"{expression}=?")
            parameters.append(normalized)
    sql = f"SELECT {','.join(selected)} FROM game_dimension g {' '.join(joins)} WHERE {' AND '.join(clauses)}"
    if groups: sql += " GROUP BY " + ",".join(groups)
    component_alias = {key: value[0][0] for key, value in definitions.items()}
    component_alias["games"] = "games"
    sort = request.get("sort")
    order = ["games DESC"] if sort is None else []
    if sort is not None:
        if not isinstance(sort, list):
            raise ValueError("sort must be an array")
        selected_aliases = {name for name, _ in names}
        for item in sort:
            alias = component_alias.get(item.get("id")) if isinstance(item, dict) else None
            direction = item.get("direction", "asc") if isinstance(item, dict) else ""
            if alias not in selected_aliases or direction not in {"asc", "desc"}:
                raise ValueError("Unsupported games sort")
            order.append(f"{alias} {direction.upper()}")
    if order: sql += " ORDER BY " + ",".join(order)
    sql += " LIMIT ? OFFSET ?"
    limit, offset = request.get("limit", 250), request.get("offset", 0)
    rows = connection.execute(sql, [*parameters, limit, offset]).fetchall()
    return serving_payload(names, rows, sql, build, scope, started, "explore", {"family": "games"})


def serving_payload(names: list[tuple[str, str]], rows: list[tuple[Any, ...]], sql: str, build: tuple[Any, ...], scope: dict[str, Any], started: float, view: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "head": {"vars": [name for name, _ in names]},
        "results": {"bindings": [row_binding(names, row) for row in rows]},
        "query": "-- Materialized SQL\n" + sql,
        "serving": {"durationMs": round((time.perf_counter() - started) * 1000, 3),
                    "buildId": build[0], "corpusFingerprint": build[1], "dateScope": scope,
                    "view": view, "coverage": serving_coverage(build), **(extra or {})},
    }


def serving_coverage(build: tuple[Any, ...]) -> dict[str, Any]:
    return {"advancedQueries": build[3], "advancedBindings": build[4], "battingResults": build[5],
            "pitches": build[6], "runnerEvents": build[7], "assignments": build[8],
            "emptyPlayerGames": build[9], "damageOpportunities": build[10]}


def scoped_special_filters(request: dict[str, Any], scope: dict[str, Any], fact_alias: str = "f") -> tuple[list[str], list[Any]]:
    filters = request.get("filters") or {}
    if not isinstance(filters, dict):
        raise ValueError("filters must be an object")
    columns = {"season": ("g.season", "integer"), "game": ("g.game_iri", "uri"),
               "venue": ("g.venue_iri", "uri"), "team": (f"{fact_alias}.team_iri", "uri"),
               "player": (f"{fact_alias}.player_iri", "uri"), "pitcher": (f"{fact_alias}.pitcher_iri", "uri")}
    if set(filters) - set(columns):
        raise ValueError("Unsupported materialized filter")
    clauses, parameters = scope_clauses(scope)
    for field, value in filters.items():
        column, kind = columns[field]
        clauses.append(f"{column}=?")
        parameters.append(filter_value(value, field, kind))
    return clauses, parameters


def query_empty(connection: sqlite3.Connection, request: dict[str, Any], build: tuple[Any, ...], scope: dict[str, Any], started: float) -> dict[str, Any]:
    analysis = request.get("analysis", "players")
    if analysis not in {"players", "teams", "stretches", "pitcher_matchups", "games", "damage"}:
        raise ValueError("Unsupported Empty Games analysis")
    if analysis == "damage":
        clauses, parameters = scoped_special_filters(request, scope, "e")
        clauses.append("e.empty_flag=1")
        sql = ("SELECT d.binding_json FROM empty_damage_fact d "
               "JOIN empty_player_game_fact e ON e.graph_iri=d.graph_iri AND e.player_iri=d.player_iri "
               "AND e.pitcher_iri=d.pitcher_iri JOIN game_dimension g ON g.graph_iri=d.graph_iri WHERE "
               + " AND ".join(clauses) + " ORDER BY g.game_start,e.player_label,d.plate_appearance_iri")
        bindings = [json.loads(row[0]) | {"emptyFlag": integer_binding(1)} for row in connection.execute(sql, parameters)]
        names = ["graph", "game", "gameStart", "player", "playerLabel", "team", "teamLabel",
                 "damagePlateAppearance", "outsBefore", "failureTypes", "doublePlay", "onFirst",
                 "onSecond", "onThird", "pitches", "swings", "contacts", "fouls",
                 "damagePitcher", "damagePitcherLabel", "emptyFlag"]
    else:
        clauses, parameters = scoped_special_filters(request, scope)
        sql = ("SELECT f.graph_iri,g.game_iri,g.game_start,f.player_iri,f.player_label,f.team_iri,f.team_label,"
               "f.pitcher_iri,f.pitcher_label,f.empty_flag FROM empty_player_game_fact f "
               "JOIN game_dimension g USING(graph_iri) WHERE " + " AND ".join(clauses)
               + " ORDER BY g.game_start,g.game_iri,f.player_label,f.pitcher_label")
        bindings = []
        for graph, game, game_start, player, player_label, team, team_label, pitcher, pitcher_label, empty in connection.execute(sql, parameters):
            row = {"graph": uri_binding(graph), "game": uri_binding(game), "gameStart": literal_binding(game_start, "dateTime"),
                   "player": uri_binding(player), "playerLabel": literal_binding(player_label),
                   "team": uri_binding(team), "teamLabel": literal_binding(team_label), "emptyFlag": integer_binding(empty)}
            if pitcher:
                row.update({"pitcher": uri_binding(pitcher), "pitcherLabel": literal_binding(pitcher_label)})
            bindings.append(row)
        names = ["graph", "game", "gameStart", "player", "playerLabel", "team", "teamLabel", "pitcher", "pitcherLabel", "emptyFlag"]
    return {"head": {"vars": names}, "results": {"bindings": bindings}, "query": "-- Materialized Empty Games SQL\n" + sql,
            "serving": {"durationMs": round((time.perf_counter() - started) * 1000, 3), "buildId": build[0],
                        "corpusFingerprint": build[1], "dateScope": scope, "view": "empty_games",
                        "coverage": serving_coverage(build), "analysis": analysis}}


def query_derived(connection: sqlite3.Connection, request: dict[str, Any], build: tuple[Any, ...], scope: dict[str, Any], started: float) -> dict[str, Any]:
    numerator, denominator = request.get("numerator"), request.get("denominator")
    if {numerator, denominator} != {"empty_games", "offensive_games_played"}:
        raise ValueError("Unsupported derived metric")
    clauses, parameters = scoped_special_filters(request, scope)
    base = ("SELECT DISTINCT f.graph_iri,f.player_iri,f.player_label,f.empty_flag "
            "FROM empty_player_game_fact f JOIN game_dimension g USING(graph_iri) WHERE " + " AND ".join(clauses))
    empty_expression = "SUM(empty_flag)"
    offensive_expression = "COUNT(*)"
    numerator_expression = empty_expression if numerator == "empty_games" else offensive_expression
    denominator_expression = empty_expression if denominator == "empty_games" else offensive_expression
    scale = 100 if numerator == "empty_games" else 1
    sql = ("SELECT player_iri,player_label,SUM(empty_flag),COUNT(*),"
           f"CASE WHEN {denominator_expression}=0 THEN NULL ELSE {scale}.0*{numerator_expression}/{denominator_expression} END "
           f"FROM ({base}) GROUP BY player_iri,player_label ORDER BY 5 DESC,player_label LIMIT {MAX_RESULTS}")
    names = [("player", "uri"), ("playerLabel", "literal"), ("emptyGames", "integer"),
             ("offensiveGamesPlayed", "integer"), ("derivedValue", "decimal")]
    rows = connection.execute(sql, parameters).fetchall()
    return serving_payload(names, rows, sql, build, scope, started, "derived")


def query_options(connection: sqlite3.Connection, request: dict[str, Any], build: tuple[Any, ...], started: float) -> dict[str, Any]:
    family, dimension = request.get("family"), request.get("dimension")
    game_set = request.get("gameSet", "regular_season")
    if game_set not in GAME_SETS:
        raise ValueError("Unsupported game set")
    common = {
        "season": ("SELECT DISTINCT g.season FROM game_dimension g WHERE g.game_set=? ORDER BY g.season", [("season", "integer")]),
        "game": ("SELECT g.game_iri,g.game_start,g.venue_iri,g.venue_label FROM game_dimension g WHERE g.game_set=? ORDER BY g.game_start DESC,g.venue_label", [("game", "uri"), ("gameStart", "dateTime"), ("venue", "uri"), ("venueLabel", "literal")]),
        "venue": ("SELECT DISTINCT g.venue_iri,g.venue_label FROM game_dimension g WHERE g.game_set=? ORDER BY g.venue_label", [("venue", "uri"), ("venueLabel", "literal")]),
    }
    if dimension in common:
        sql, names = common[dimension]
    elif dimension == "team":
        sql = "SELECT DISTINCT a.assignee_iri,a.assignee_label FROM assignment_fact a JOIN game_dimension g USING(graph_iri) WHERE g.game_set=? AND a.assignment_type IN ('home','away') ORDER BY a.assignee_label"
        names = [("team", "uri"), ("teamLabel", "literal")]
    elif dimension in {"umpire", "official_scorer"}:
        kind = dimension
        variable = "officialScorer" if dimension == "official_scorer" else "umpire"
        sql = "SELECT DISTINCT a.assignee_iri,a.assignee_label FROM assignment_fact a JOIN game_dimension g USING(graph_iri) WHERE g.game_set=? AND a.assignment_type=? ORDER BY a.assignee_label"
        names = [(variable, "uri"), (f"{variable}Label", "literal")]
        rows = connection.execute(sql, (game_set, kind)).fetchall()
        return serving_payload(names, rows, sql, build, {"gameSet": game_set}, started, "options")
    elif dimension in {"player", "pitcher", "event_type"}:
        if dimension == "pitcher":
            table, variable, label, column = "pitch_fact", "pitcher", "pitcherLabel", "pitcher"
        elif family == "baserunning":
            table, variable, label, column = "runner_event_fact", "player", "playerLabel", "player"
        else:
            table, variable, label, column = "batting_result_fact", "player", "playerLabel", "player"
        if dimension == "event_type":
            sql = f"SELECT DISTINCT f.event_type,REPLACE(f.event_type,'_',' ') FROM {table} f JOIN game_dimension g USING(graph_iri) WHERE g.game_set=? ORDER BY 2"
            names = [("eventType", "literal"), ("eventTypeLabel", "literal")]
        else:
            sql = f"SELECT DISTINCT f.{column}_iri,f.{column}_label FROM {table} f JOIN game_dimension g USING(graph_iri) WHERE g.game_set=? ORDER BY f.{column}_label"
            names = [(variable, "uri"), (label, "literal")]
    else:
        raise ValueError("Unsupported materialized option")
    rows = connection.execute(sql, (game_set,)).fetchall()
    return serving_payload(names, rows, sql, build, {"gameSet": game_set}, started, "options")


def query(args: argparse.Namespace, request: dict[str, Any]) -> dict[str, Any]:
    serving_contract = load_object(CONTRACT)
    require_materialized_route_admission(request, serving_contract)
    catalog = load_object(ADVANCED_CATALOG)
    reducers = load_object(ADVANCED_REDUCERS)
    dsq_catalog = load_object(DSQ_MATERIALIZATIONS)
    query_index_routing = load_object(QUERY_INDEX_ROUTING)
    query_ids = {entry["id"] for entry in catalog["queries"]}
    reducer_ids = set(reducers.get("detailQueries", [])) | set(reducers.get("additiveQueries", {}))
    if query_ids != reducer_ids or query_ids != set(reducers.get("ordering", {})):
        raise ValueError("Reviewed SQL reducer coverage is incomplete")
    pointer_path = args.state_root.resolve() / "serving" / "current.json"
    pointer = load_object(pointer_path)
    if pointer.get("artifactType") != "baseball-analytical-serving-pointer" or pointer.get("contractVersion") != 5:
        raise ValueError("Unsupported serving pointer contract")
    for key, path in (
        ("schemaSha256", SCHEMA), ("contractSha256", CONTRACT),
        ("sourceQuerySha256", SOURCE_QUERY), ("materializerSha256", MATERIALIZER),
        ("mappingSha256", MAPPING), ("validationSha256", VALIDATOR),
        ("ratingSpecSha256", QUALITY_SPEC),
    ):
        if pointer.get(key) != sha(path):
            raise ValueError(f"Serving build is stale for {path.name}")
    if pointer.get("advancedQuerySetSha256") != advanced_query_set_sha256(catalog):
        raise ValueError("Serving build is stale for the reviewed advanced query set")
    if pointer.get("advancedReducerSha256") != sha(ADVANCED_REDUCERS):
        raise ValueError("Serving build is stale for advanced SQL reducers")
    if pointer.get("dsqMaterializationCatalogSha256") != sha(DSQ_MATERIALIZATIONS):
        raise ValueError("Serving build is stale for the DSQ SQL materialization catalog")
    if pointer.get("dsqQuerySetSha256") != dsq_query_set_sha256(
        dsq_catalog, catalog, reducers, query_index_routing
    ):
        raise ValueError("Serving build is stale for the complete DSQ query set")
    if pointer.get("exploreQuerySetSha256") != file_set_sha256(SERVING_QUERY_FILES):
        raise ValueError("Serving build is stale for Explorer grain queries")
    database = Path(str(pointer.get("databasePath", ""))).resolve()
    builds = (args.state_root.resolve() / "serving" / "builds").resolve()
    if database.parent != builds or database.suffix != ".sqlite" or not database.is_file():
        raise ValueError("Serving pointer database is outside the immutable build directory")
    verification_cache = builds.parent / "database-verification-cache.json"
    verified_identity = verify_database(
        database, pointer.get("databaseSha256"), verification_cache
    )
    connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)
    started = time.perf_counter()
    try:
        if file_identity(database) != verified_identity:
            raise ValueError("Serving database changed while it was opened")
        build = connection.execute(
            "SELECT build_id,corpus_fingerprint,status,advanced_query_count,advanced_binding_count,"
            "batting_result_count,pitch_count,runner_event_count,assignment_count,"
            "empty_player_game_count,damage_opportunity_count FROM serving_build"
        ).fetchone()
        if not build or build[0] != pointer.get("buildId") or build[1] != pointer.get("corpusFingerprint") or build[2] != "validated":
            raise ValueError("Serving build metadata does not match its promotion pointer")
        dsq_coverage = connection.execute(
            "SELECT COUNT(*),COALESCE(SUM(binding_count),0) FROM dsq_query_manifest"
        ).fetchone()
        if (
            not dsq_coverage
            or dsq_coverage[0] != pointer.get("dsqQueryCount")
            or dsq_coverage[1] != pointer.get("dsqBindingCount")
        ):
            raise ValueError("Serving build DSQ coverage differs from its promotion pointer")
        route = request.get("route")
        if route == "options":
            return query_options(connection, request, build, started)
        scope = resolve_scope(connection, request)
        if route == "metric-suite":
            if pointer.get('metricSuiteSha256') != _metric_suite.fingerprint():
                raise ValueError('Serving pointer is stale for the metric suite')
            result = _metric_suite.query_sql(connection, request, scope)
            result['serving'] = {'buildId': build[0], 'corpusFingerprint': build[1],
                                 'durationMs': round((time.perf_counter() - started) * 1000, 3)}
            return result
        if route == "explore":
            return query_explore(connection, request, build, scope, started)
        if route == "empty-games":
            return query_empty(connection, request, build, scope, started)
        if route == "derived":
            return query_derived(connection, request, build, scope, started)
        if request.get("id") != "plate-appearance-fingerprint":
            return query_advanced(connection, request, build, scope, started, catalog, reducers)
        clauses = ["g.game_set=?", "g.official_date BETWEEN ? AND ?"]
        parameters: list[Any] = [scope["gameSet"], scope["startDate"], scope["endDate"]]
        filters = request.get("filters") or {}
        if not isinstance(filters, dict):
            raise ValueError("filters must be an object")
        mappings = {
            "game": "p.game_iri", "venue": "g.venue_iri", "player": "p.batter_iri",
            "pitcher": "p.pitcher_iri",
        }
        for field, column in mappings.items():
            if field in filters:
                clauses.append(f"{column}=?")
                parameters.append(canonical_iri(filters[field], field))
        if "team" in filters:
            clauses.append("(g.home_team_iri=? OR g.away_team_iri=?)")
            team = canonical_iri(filters["team"], "team")
            parameters.extend([team, team])
        if "season" in filters:
            season = filters["season"]
            if not isinstance(season, int) or not 1800 <= season <= 3000:
                raise ValueError("season must be an integer between 1800 and 3000")
            clauses.append("g.season=?")
            parameters.append(season)
        unknown = set(filters) - {*mappings, "team", "season"}
        if unknown:
            raise ValueError(f"Unsupported filter: {sorted(unknown)[0]}")
        view = request.get("view", "plate_appearances")
        if view not in {"plate_appearances", "player_averages"}:
            raise ValueError(f"Unsupported Plate Appearance Quality view: {view}")
        if view == "player_averages":
            sql = (
                "SELECT p.batter_iri,p.batter_label,COUNT(*),AVG(p.plate_appearance_quality),"
                "SUM(CASE WHEN p.plate_appearance_quality_band='Excellent' THEN 1 ELSE 0 END),"
                "SUM(CASE WHEN p.plate_appearance_quality_band='Good' THEN 1 ELSE 0 END),"
                "SUM(CASE WHEN p.plate_appearance_quality_band='Mixed' THEN 1 ELSE 0 END),"
                "SUM(CASE WHEN p.plate_appearance_quality_band='Poor' THEN 1 ELSE 0 END),"
                "SUM(CASE WHEN p.plate_appearance_quality_band='Bad' THEN 1 ELSE 0 END) "
                "FROM plate_appearance_fact p JOIN game_dimension g USING(graph_iri) WHERE "
                + " AND ".join(clauses)
                + " GROUP BY p.batter_iri,p.batter_label "
                "ORDER BY AVG(p.plate_appearance_quality) DESC,p.batter_label LIMIT 1000"
            )
            bindings = []
            for row in connection.execute(sql, parameters):
                player, label, appearances, average, excellent, good, mixed, poor, bad = row
                bindings.append({
                    "player": {"type": "uri", "value": player},
                    "playerLabel": {"type": "literal", "value": label},
                    "plateAppearances": {"type": "literal", "datatype": f"{XSD}integer", "value": str(appearances)},
                    "averagePlateAppearanceQuality": {
                        "type": "literal", "datatype": f"{XSD}decimal", "value": f"{average:.3f}",
                    },
                    "excellentPlateAppearances": {"type": "literal", "datatype": f"{XSD}integer", "value": str(excellent)},
                    "goodPlateAppearances": {"type": "literal", "datatype": f"{XSD}integer", "value": str(good)},
                    "mixedPlateAppearances": {"type": "literal", "datatype": f"{XSD}integer", "value": str(mixed)},
                    "poorPlateAppearances": {"type": "literal", "datatype": f"{XSD}integer", "value": str(poor)},
                    "badPlateAppearances": {"type": "literal", "datatype": f"{XSD}integer", "value": str(bad)},
                })
            variables = [
                "player", "playerLabel", "plateAppearances", "averagePlateAppearanceQuality",
                "excellentPlateAppearances", "goodPlateAppearances", "mixedPlateAppearances",
                "poorPlateAppearances", "badPlateAppearances",
            ]
        else:
            sql = (
                "SELECT p.binding_json FROM plate_appearance_fact p "
                "JOIN game_dimension g USING(graph_iri) WHERE " + " AND ".join(clauses)
                + " ORDER BY p.game_iri,p.start_time LIMIT 1000"
            )
            bindings = [json.loads(row[0]) for row in connection.execute(sql, parameters)]
            # Preserve the reviewed query's projected variable order, including
            # fields which may be unbound in every selected row.
            variables = [
                "game", "plateAppearance", "batter", "batterLabel", "pitcher", "pitcherLabel",
                "outcome", "wasHit", "hitType", "startTime", "endTime", "duration", "durationMinutes",
                "pitches", "swings", "bunts", "contacts", "balls", "strikes", "fouls", "foulTips",
                "runnerRuns", "runnerOuts", "safeResolutions", "positiveOutcome", "productiveOtherRunner",
                "grindScore", "outcomeRating", "grindRating", "situationalRating",
                "plateAppearanceQuality", "plateAppearanceQualityBand",
                "plateAppearanceQualityVersion", "goodAtBatEvidenceCount", "goodAtBat",
            ]
        game_count = connection.execute(
            "SELECT COUNT(*) FROM game_dimension WHERE game_set=? AND official_date BETWEEN ? AND ?",
            (scope["gameSet"], scope["startDate"], scope["endDate"]),
        ).fetchone()[0]
        scope["gameCount"] = game_count
        duration = round((time.perf_counter() - started) * 1000, 3)
        return {
            "head": {"vars": variables},
            "results": {"bindings": bindings},
            "query": "-- Materialized from sparql/advanced/plate-appearance-fingerprint.rq\n" + sql,
            "serving": {
                "durationMs": duration, "buildId": build[0], "corpusFingerprint": build[1],
                "filters": filters, "dateScope": scope, "view": view,
                "coverage": serving_coverage(build),
            },
        }
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    default_state = Path(os.environ.get("BASEBALLO_STATE_ROOT") or Path(os.environ.get("LOCALAPPDATA", ".")) / "BaseballO" / "state")
    parser.add_argument("--state-root", type=Path, default=default_state)
    args = parser.parse_args()
    try:
        request = json.load(sys.stdin)
        if not isinstance(request, dict):
            raise ValueError("Serving request must be an object")
        catalog = load_object(ADVANCED_CATALOG)
        routes = {"explore", "options", "empty-games", "derived", "metric-suite"}
        if request.get("route") not in routes and request.get("id") not in {entry["id"] for entry in catalog["queries"]}:
            raise ValueError("Only reviewed Explorer queries are materialized")
        # ASCII-safe JSON prevents the Windows console code page from corrupting
        # UTF-8 names when Node reads this process through a pipe.
        print(json.dumps(query(args, request), separators=(",", ":"), ensure_ascii=True))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "unavailable", "error": str(exc)}, separators=(",", ":")))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
