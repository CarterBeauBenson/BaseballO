#!/usr/bin/env python3
"""Materialize promoted authority RDF events into an immutable SQLite serving build."""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import hashlib
import importlib.util
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Iterator


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "serving" / "authority-contract.json"
SCHEMA_PATH = ROOT / "serving" / "authority-schema.sql"
CATALOG_PATH = ROOT / "sparql" / "query-modules" / "authority" / "catalog.json"
COMPILER_PATH = ROOT / "scripts" / "pipeline" / "compile-dsq-query.py"
MATERIALIZER_PATH = Path(__file__).resolve()
IDENTIFIER = __import__("re").compile(r"[a-z_][a-z0-9_]*")

COMPILER_SPEC = importlib.util.spec_from_file_location("baseballo_dsq_compiler_authority", COMPILER_PATH)
COMPILER = importlib.util.module_from_spec(COMPILER_SPEC)
assert COMPILER_SPEC and COMPILER_SPEC.loader
sys.modules[COMPILER_SPEC.name] = COMPILER
COMPILER_SPEC.loader.exec_module(COMPILER)


class MaterializationError(ValueError):
    """Raised when an authority serving candidate violates its contract."""


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise MaterializationError(f"JSON artifact must be an object: {path}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def query_spec_set_sha256(contract: dict[str, Any]) -> str:
    return sha256_text(
        canonical_json(
            {
                entry["id"]: sha256_file(ROOT / entry["spec"])
                for entry in contract["queries"]
            }
        )
    )


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


@contextlib.contextmanager
def exclusive_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise MaterializationError(f"Authority materialization is already locked: {path}") from exc
    try:
        os.write(descriptor, canonical_json({"pid": os.getpid(), "createdAtUtc": utc_now()}).encode("utf-8"))
        os.close(descriptor)
        descriptor = -1
        yield
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        path.unlink(missing_ok=True)


def sparql(endpoint: str, query: str, timeout: int) -> dict[str, Any]:
    request = urllib.request.Request(
        endpoint,
        data=urllib.parse.urlencode({"query": query}).encode("utf-8"),
        headers={"Accept": "application/sparql-results+json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("results", {}).get("bindings"), list):
        raise MaterializationError("SPARQL endpoint returned an invalid results document")
    return payload


def validate_contract() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    contract = load_json(CONTRACT_PATH)
    if (
        contract.get("artifactType") != "baseballo-authority-serving-contract"
        or contract.get("contractVersion") != 1
        or contract.get("engine") != "sqlite"
        or contract.get("partitioning") != "replace-source-graph"
    ):
        raise MaterializationError("Authority serving contract envelope is invalid")
    if contract.get("catalog") != str(CATALOG_PATH.relative_to(ROOT)).replace("\\", "/"):
        raise MaterializationError("Authority serving contract names the wrong query-module catalog")
    if contract.get("schema") != str(SCHEMA_PATH.relative_to(ROOT)).replace("\\", "/"):
        raise MaterializationError("Authority serving contract names the wrong schema")
    catalog, modules = COMPILER.load_catalog(CATALOG_PATH)
    raw_queries = contract.get("queries")
    if not isinstance(raw_queries, list) or not raw_queries:
        raise MaterializationError("Authority serving contract must declare queries")
    query_ids: set[str] = set()
    for entry in raw_queries:
        if not isinstance(entry, dict):
            raise MaterializationError("Authority serving query entries must be objects")
        query_id = str(entry.get("id", ""))
        table = str(entry.get("table", ""))
        if query_id in query_ids or not COMPILER.ID_PATTERN.fullmatch(query_id):
            raise MaterializationError(f"Duplicate or invalid authority serving query id: {query_id!r}")
        if not IDENTIFIER.fullmatch(table):
            raise MaterializationError(f"Invalid authority serving table: {table!r}")
        query_ids.add(query_id)
        spec_path = (ROOT / str(entry.get("spec", ""))).resolve()
        if not spec_path.is_file() or not spec_path.is_relative_to(
            (ROOT / "sparql" / "query-modules" / "authority" / "specs").resolve()
        ):
            raise MaterializationError(f"Authority serving spec is missing or misplaced: {spec_path}")
        spec = load_json(spec_path)
        if spec.get("id") != query_id:
            raise MaterializationError(f"Authority serving query/spec id mismatch: {query_id}")
        sources = entry.get("sources")
        if not isinstance(sources, list) or sources != spec.get("sourceScope", {}).get("sources"):
            raise MaterializationError(f"Authority serving source scope drifted for {query_id}")
        COMPILER.compile_query(spec, catalog, modules)
        constants = entry.get("constants")
        columns = entry.get("columns")
        if not isinstance(constants, dict) or not isinstance(columns, list) or not columns:
            raise MaterializationError(f"Authority serving column contract is invalid for {query_id}")
        names = ["query_id", "graph_iri", "source_module", *constants.keys()]
        for column in columns:
            if not isinstance(column, dict):
                raise MaterializationError(f"Authority serving columns must be objects for {query_id}")
            name = str(column.get("name", ""))
            variable = str(column.get("variable", ""))
            if not IDENTIFIER.fullmatch(name) or variable not in spec.get("projection", []):
                raise MaterializationError(f"Authority serving column is invalid for {query_id}: {column!r}")
            if column.get("conversion") not in (None, "decimal", "integer"):
                raise MaterializationError(f"Authority serving conversion is invalid for {query_id}")
            names.append(name)
        names.extend(["binding_json", "binding_sha256"])
        if len(names) != len(set(names)):
            raise MaterializationError(f"Authority serving columns collide for {query_id}")
    return contract, catalog, modules


def validate_event(path: Path, state_root: Path, source_contracts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    event_root = (state_root / "pipeline" / "events" / "promoted-graphs").resolve()
    resolved = path.resolve()
    if not resolved.is_file() or not resolved.is_relative_to(event_root):
        raise MaterializationError(f"Promoted-graph event is outside its outbox: {path}")
    event = load_json(resolved)
    if event.get("artifactType") != "baseballo-promoted-graph-event" or event.get("contractVersion") != 1:
        raise MaterializationError(f"Unsupported promoted-graph event: {path}")
    event_id = str(event.get("eventId", ""))
    module = str(event.get("sourceModule", ""))
    graph = str(event.get("authoritativeGraph", ""))
    if len(event_id) != 64 or any(char not in "0123456789abcdef" for char in event_id):
        raise MaterializationError(f"Promoted-graph event has an invalid id: {path}")
    if path.stem != event_id or module not in source_contracts:
        raise MaterializationError(f"Promoted-graph event identity/source is invalid: {path}")
    if not any(graph.startswith(prefix) and graph != prefix for prefix in source_contracts[module]["graphPrefixes"]):
        raise MaterializationError(f"Promoted-graph event graph is outside its source namespace: {path}")
    count = event.get("authoritativeTripleCount")
    if not isinstance(count, int) or isinstance(count, bool) or count <= 0:
        raise MaterializationError(f"Promoted-graph event has an invalid triple count: {path}")
    promotion_path = Path(str(event.get("promotionEvidence", ""))).resolve()
    evidence_root = (state_root / "pipeline" / "evidence").resolve()
    if not promotion_path.is_file() or not promotion_path.is_relative_to(evidence_root):
        raise MaterializationError(f"Promoted-graph event has missing promotion evidence: {path}")
    if sha256_file(promotion_path) != event.get("promotionEvidenceSha256"):
        raise MaterializationError(f"Promoted-graph event promotion hash is stale: {path}")
    expected_id = hashlib.sha256(
        (
            canonical_json(
                {
                    "sourceModule": module,
                    "scopeKey": str(event.get("scopeKey", "")),
                    "pipelineRunId": str(event.get("pipelineRunId", "")),
                    "promotionEvidenceSha256": str(event.get("promotionEvidenceSha256", "")),
                }
            )
            + "\n"
        ).encode("utf-8")
    ).hexdigest()
    if event_id != expected_id:
        raise MaterializationError(f"Promoted-graph event id does not match its evidence identity: {path}")
    return {**event, "eventPath": str(resolved), "eventSha256": sha256_file(resolved)}


def query_routes(contract: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    routes: dict[str, list[dict[str, Any]]] = {}
    for entry in contract["queries"]:
        for source in entry["sources"]:
            routes.setdefault(source, []).append(entry)
    return routes


def pending_events(
    state_root: Path,
    contract: dict[str, Any],
    catalog: dict[str, Any],
    maximum: int,
) -> list[dict[str, Any]]:
    routes = query_routes(contract)
    source_contracts = {str(item["id"]): item for item in catalog["sourceContracts"]}
    receipt_root = state_root / "pipeline" / "evidence" / "serving-authority" / "events"
    event_root = state_root / "pipeline" / "events" / "promoted-graphs"
    values: list[dict[str, Any]] = []
    for path in sorted(event_root.glob("*/*/*.json")) if event_root.is_dir() else []:
        if (receipt_root / path.name).is_file():
            continue
        event = validate_event(path, state_root, source_contracts)
        if event["sourceModule"] in routes:
            values.append(event)
    values.sort(key=lambda item: (str(item["promotedAtUtc"]), str(item["eventId"])))
    return values[:maximum]


def discover_graphs(
    endpoint: str, timeout: int, catalog: dict[str, Any]
) -> list[dict[str, Any]]:
    prefixes = {
        str(source["id"]): prefix
        for source in catalog["sourceContracts"]
        for prefix in source["graphPrefixes"]
    }
    expression = " || ".join(
        f'STRSTARTS(STR(?authorityGraph), "{prefix}")' for prefix in prefixes.values()
    )
    query = (
        "SELECT ?authorityGraph (COUNT(*) AS ?tripleCount) WHERE { "
        "GRAPH ?authorityGraph { ?s ?p ?o } "
        f"FILTER({expression}) }} GROUP BY ?authorityGraph"
    )
    payload = sparql(endpoint, query, timeout)
    values: list[dict[str, Any]] = []
    for binding in payload["results"]["bindings"]:
        graph = str(binding.get("authorityGraph", {}).get("value", ""))
        source = next((source for source, prefix in prefixes.items() if graph.startswith(prefix)), None)
        count = int(binding.get("tripleCount", {}).get("value", "0"))
        if source is None or count <= 0:
            raise MaterializationError(f"Full rebuild discovered an invalid authority graph: {graph!r}")
        event_id = "full-rebuild-" + sha256_text(graph)
        values.append(
            {
                "eventId": event_id,
                "sourceModule": source,
                "authoritativeGraph": graph,
                "authoritativeTripleCount": count,
                "promotedAtUtc": utc_now(),
                "promotionEvidenceSha256": "",
                "eventSha256": "",
            }
        )
    return sorted(values, key=lambda item: (item["sourceModule"], item["authoritativeGraph"]))


def binding_value(binding: dict[str, Any], variable: str, conversion: str | None = None) -> object:
    term = binding.get(variable)
    if not isinstance(term, dict) or not isinstance(term.get("value"), str):
        raise MaterializationError(f"SPARQL binding lacks required variable {variable}")
    value = term["value"]
    if conversion == "decimal":
        return float(value)
    if conversion == "integer":
        return int(value)
    return value


def table_columns(connection: sqlite3.Connection, table: str) -> list[str]:
    if not IDENTIFIER.fullmatch(table):
        raise MaterializationError(f"Unsafe SQLite table identifier: {table!r}")
    return [str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})")]


def insert_binding(
    connection: sqlite3.Connection,
    entry: dict[str, Any],
    event: dict[str, Any],
    binding: dict[str, Any],
) -> None:
    graph = str(event["authoritativeGraph"])
    if binding_value(binding, "authorityGraph") != graph:
        raise MaterializationError(f"Query {entry['id']} returned a row outside its exact graph scope")
    canonical = canonical_json(binding)
    columns = ["query_id", "graph_iri", "source_module"]
    values: list[object] = [entry["id"], graph, event["sourceModule"]]
    for name, value in entry["constants"].items():
        columns.append(name)
        values.append(value)
    for column in entry["columns"]:
        columns.append(column["name"])
        values.append(binding_value(binding, column["variable"], column.get("conversion")))
    columns.extend(["binding_json", "binding_sha256"])
    values.extend([canonical, sha256_text(canonical)])
    table = entry["table"]
    if table_columns(connection, table) != columns:
        raise MaterializationError(f"SQLite schema/column contract drifted for {entry['id']}")
    placeholders = ",".join("?" for _ in columns)
    connection.execute(
        f"INSERT INTO {table} ({','.join(columns)}) VALUES ({placeholders})",
        values,
    )


def initialize_query_manifest(connection: sqlite3.Connection, contract: dict[str, Any]) -> None:
    for entry in contract["queries"]:
        spec_path = ROOT / entry["spec"]
        spec = load_json(spec_path)
        connection.execute(
            """INSERT INTO authority_query_manifest
               (query_id,spec_path,spec_sha256,table_name,variables_json,row_count)
               VALUES (?,?,?,?,?,0)
               ON CONFLICT(query_id) DO UPDATE SET
                 spec_path=excluded.spec_path,spec_sha256=excluded.spec_sha256,
                 table_name=excluded.table_name,variables_json=excluded.variables_json""",
            (
                entry["id"],
                entry["spec"],
                sha256_file(spec_path),
                entry["table"],
                canonical_json(spec["projection"]),
            ),
        )


def apply_graph(
    connection: sqlite3.Connection,
    event: dict[str, Any],
    routes: dict[str, list[dict[str, Any]]],
    catalog: dict[str, Any],
    modules: dict[str, Any],
    endpoint: str,
    timeout: int,
) -> dict[str, Any]:
    graph = str(event["authoritativeGraph"])
    existing = connection.execute(
        "SELECT promoted_at_utc,event_id FROM authority_source_graph WHERE graph_iri=?", (graph,)
    ).fetchone()
    if existing is not None and str(existing[0]) > str(event["promotedAtUtc"]):
        return {"eventId": event["eventId"], "graph": graph, "status": "superseded", "rows": 0}
    connection.execute("DELETE FROM authority_source_graph WHERE graph_iri=?", (graph,))
    connection.execute(
        "INSERT INTO authority_source_graph VALUES (?,?,?,?,?,?,?)",
        (
            graph,
            event["sourceModule"],
            event["eventId"],
            event["promotedAtUtc"],
            event["authoritativeTripleCount"],
            event.get("promotionEvidenceSha256", ""),
            event.get("eventSha256", ""),
        ),
    )
    inserted = 0
    for entry in routes.get(str(event["sourceModule"]), []):
        spec = load_json(ROOT / entry["spec"])
        query = COMPILER.compile_query(
            spec, catalog, modules, authority_graphs=[graph]
        )
        payload = sparql(endpoint, query, timeout)
        for binding in payload["results"]["bindings"]:
            insert_binding(connection, entry, event, binding)
            inserted += 1
    return {"eventId": event["eventId"], "graph": graph, "status": "applied", "rows": inserted}


def enforce_retention(build_root: Path, keep: set[Path], retain: int) -> list[str]:
    candidates = sorted(
        build_root.glob("authority-*.sqlite"), key=lambda item: item.stat().st_mtime, reverse=True
    )
    retained = set(candidates[:retain]) | {item.resolve() for item in keep}
    removed: list[str] = []
    for path in candidates:
        if path.resolve() not in retained:
            path.unlink()
            removed.append(str(path))
    return removed


def build(args: argparse.Namespace) -> dict[str, Any]:
    state_root = args.state_root.resolve()
    contract, catalog, modules = validate_contract()
    routes = query_routes(contract)
    store_root = state_root / "serving" / "authority"
    build_root = store_root / "builds"
    evidence_root = store_root / "evidence"
    pointer_path = store_root / "current.json"
    build_root.mkdir(parents=True, exist_ok=True)
    evidence_root.mkdir(parents=True, exist_ok=True)

    if args.full_rebuild:
        events = discover_graphs(args.endpoint, args.timeout, catalog)
        mode = "full-rdf-rebuild"
    else:
        events = pending_events(state_root, contract, catalog, args.max_events)
        mode = "incremental-events"
    if not events:
        return {"status": "no-op", "mode": mode, "processedEventCount": 0}

    build_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid.uuid4().hex[:8]
    database = build_root / f"authority-{build_id}.sqlite"
    prior_database: Path | None = None
    if mode == "incremental-events" and pointer_path.is_file():
        pointer = load_json(pointer_path)
        if pointer.get("artifactType") != "baseballo-authority-serving-pointer" or pointer.get("contractVersion") != 1:
            raise MaterializationError("Current authority serving pointer is invalid")
        expected_hashes = {
            "contractSha256": sha256_file(CONTRACT_PATH),
            "schemaSha256": sha256_file(SCHEMA_PATH),
            "materializerSha256": sha256_file(MATERIALIZER_PATH),
            "compilerSha256": sha256_file(COMPILER_PATH),
            "moduleCatalogSha256": sha256_file(CATALOG_PATH),
            "querySpecSetSha256": query_spec_set_sha256(contract),
        }
        if any(pointer.get(key) != value for key, value in expected_hashes.items()):
            raise MaterializationError("Authority serving contract drift requires a NiFi-owned full RDF rebuild")
        prior_database = Path(str(pointer.get("databasePath", ""))).resolve()
        if not prior_database.is_file() or sha256_file(prior_database) != pointer.get("databaseSha256"):
            raise MaterializationError("Current authority serving database is missing or has drifted")
        shutil.copy2(prior_database, database)

    connection = sqlite3.connect(database)
    validated = False
    outcomes: list[dict[str, Any]] = []
    try:
        connection.execute("PRAGMA foreign_keys=ON")
        if prior_database is None:
            connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        initialize_query_manifest(connection, contract)
        connection.execute("DELETE FROM authority_build")
        for event in events:
            outcomes.append(
                apply_graph(connection, event, routes, catalog, modules, args.endpoint, args.timeout)
            )
        for entry in contract["queries"]:
            row_count = connection.execute(
                f"SELECT COUNT(*) FROM {entry['table']} WHERE query_id=?", (entry["id"],)
            ).fetchone()[0]
            connection.execute(
                "UPDATE authority_query_manifest SET row_count=? WHERE query_id=?",
                (row_count, entry["id"]),
            )
        result_rows = sum(
            connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in sorted({entry["table"] for entry in contract["queries"]})
        )
        graph_count = connection.execute("SELECT COUNT(*) FROM authority_source_graph").fetchone()[0]
        connection.execute(
            "INSERT INTO authority_build VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                build_id,
                1,
                utc_now(),
                mode,
                sha256_file(CONTRACT_PATH),
                sha256_file(SCHEMA_PATH),
                sha256_file(MATERIALIZER_PATH),
                sha256_file(COMPILER_PATH),
                sha256_file(CATALOG_PATH),
                query_spec_set_sha256(contract),
                graph_count,
                result_rows,
                len(events),
                "candidate",
            ),
        )
        connection.commit()
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_keys = connection.execute("PRAGMA foreign_key_check").fetchall()
        hash_failures = 0
        for table in sorted({entry["table"] for entry in contract["queries"]}):
            hash_failures += sum(
                sha256_text(binding) != digest
                for binding, digest in connection.execute(
                    f"SELECT binding_json,binding_sha256 FROM {table}"
                )
            )
        if integrity != "ok" or foreign_keys or hash_failures:
            raise MaterializationError("Authority serving candidate failed SQLite integrity validation")
        connection.execute("UPDATE authority_build SET status='validated' WHERE build_id=?", (build_id,))
        connection.commit()
        connection.execute("PRAGMA optimize")
        validated = True
    finally:
        connection.close()
        if not validated:
            database.unlink(missing_ok=True)

    evidence = {
        "artifactType": "baseballo-authority-serving-build-evidence",
        "contractVersion": 1,
        "buildId": build_id,
        "status": "validated" if args.no_promote else "promoted",
        "createdAtUtc": utc_now(),
        "buildMode": mode,
        "databasePath": str(database.resolve()),
        "databaseSha256": sha256_file(database),
        "contractSha256": sha256_file(CONTRACT_PATH),
        "schemaSha256": sha256_file(SCHEMA_PATH),
        "materializerSha256": sha256_file(MATERIALIZER_PATH),
        "compilerSha256": sha256_file(COMPILER_PATH),
        "moduleCatalogSha256": sha256_file(CATALOG_PATH),
        "querySpecSetSha256": query_spec_set_sha256(contract),
        "sourceGraphCount": graph_count,
        "resultRowCount": result_rows,
        "processedEventCount": len(events),
        "outcomes": outcomes,
        "integrity": {"sqliteIntegrityCheck": integrity, "foreignKeyIssueCount": len(foreign_keys), "bindingHashMismatchCount": hash_failures},
    }
    evidence_path = evidence_root / f"{build_id}.json"
    atomic_json(evidence_path, evidence)
    if args.no_promote:
        return evidence

    pointer = {
        "artifactType": "baseballo-authority-serving-pointer",
        "contractVersion": 1,
        "promotedAtUtc": utc_now(),
        "buildId": build_id,
        "databasePath": str(database.resolve()),
        "databaseSha256": evidence["databaseSha256"],
        "contractSha256": evidence["contractSha256"],
        "schemaSha256": evidence["schemaSha256"],
        "materializerSha256": evidence["materializerSha256"],
        "compilerSha256": evidence["compilerSha256"],
        "moduleCatalogSha256": evidence["moduleCatalogSha256"],
        "querySpecSetSha256": evidence["querySpecSetSha256"],
        "sourceGraphCount": graph_count,
        "resultRowCount": result_rows,
        "evidencePath": str(evidence_path.resolve()),
    }
    atomic_json(pointer_path, pointer)
    receipt_root = state_root / "pipeline" / "evidence" / "serving-authority" / "events"
    if mode == "incremental-events":
        for event, outcome in zip(events, outcomes):
            atomic_json(
                receipt_root / f"{event['eventId']}.json",
                {
                    "artifactType": "baseballo-authority-serving-event-receipt",
                    "contractVersion": 1,
                    "eventId": event["eventId"],
                    "eventSha256": event["eventSha256"],
                    "buildId": build_id,
                    "databaseSha256": evidence["databaseSha256"],
                    "outcome": outcome,
                },
            )
    keep = {database}
    if prior_database is not None:
        keep.add(prior_database)
    evidence["removedBuilds"] = enforce_retention(build_root, keep, max(2, args.retain_builds))
    return evidence


def main() -> int:
    default_state = Path(
        os.environ.get("BASEBALLO_STATE_ROOT")
        or Path(os.environ.get("LOCALAPPDATA", ".")) / "BaseballO" / "state"
    )
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-root", type=Path, default=default_state)
    parser.add_argument("--endpoint", default="http://127.0.0.1:3031/baseball-dev/query")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--max-events", type=int, default=100)
    parser.add_argument("--full-rebuild", action="store_true")
    parser.add_argument("--no-promote", action="store_true")
    parser.add_argument("--retain-builds", type=int, default=3)
    args = parser.parse_args()
    if args.max_events < 1 or args.timeout < 1 or args.retain_builds < 2:
        print(json.dumps({"status": "failed", "error": "Invalid positive runtime limit"}))
        return 1
    try:
        with exclusive_lock(args.state_root.resolve() / "serving" / "authority" / ".materialize.lock"):
            print(json.dumps(build(args), separators=(",", ":"), ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, separators=(",", ":")))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
