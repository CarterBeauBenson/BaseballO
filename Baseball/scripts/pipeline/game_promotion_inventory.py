#!/usr/bin/env python3
"""Source-neutral validation of promoted MLB-game/query-index graph pairs."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
GRAPH_PREFIX = "https://w3id.org/baseball/graph/game/"
INDEX_GRAPH_PREFIX = "https://w3id.org/baseball/graph/query-index/game/"
GAME_IRI_PREFIX = "https://baseballontology.org/data/game/"
INDEX_RESOURCE_PREFIX = "https://w3id.org/baseball/query-index-build/game/"
QUERY_INDEX_ROUTING = ROOT / "sparql" / "query-index" / "operational-query-routing.json"
QUERY_INDEX_SEMANTIC_CONTRACT = ROOT / "sparql" / "query-index" / "semantic-contract.json"
SUPPORTED_QUERY_INDEX_CONTRACT_VERSION = 1


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def required_sha256(value: object, label: str) -> str:
    digest = str(value or "")
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError(f"{label} is not a lowercase SHA-256 digest")
    return digest


def required_positive_int(value: object, label: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{label} is not a positive integer")
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} is not a positive integer") from exc
    if result <= 0:
        raise ValueError(f"{label} is not a positive integer")
    return result


def promotion_timestamp(value: object) -> datetime:
    text = re.sub(
        r"(\.\d{6})\d+(?=[+-]\d{2}:\d{2}$)",
        r"\1",
        str(value).replace("Z", "+00:00"),
    )
    timestamp = datetime.fromisoformat(text)
    if timestamp.tzinfo is None:
        raise ValueError("Promotion timestamp has no timezone")
    return timestamp.astimezone(timezone.utc)


def query_index_contract_admission() -> dict[str, Any]:
    routing = json_object(QUERY_INDEX_ROUTING)
    contract = json_object(QUERY_INDEX_SEMANTIC_CONTRACT)
    contract_sha256 = sha256_file(QUERY_INDEX_SEMANTIC_CONTRACT)
    semantic = routing.get("semanticAdmission")
    if (
        routing.get("artifactType") != "baseball-reviewed-query-routing"
        or routing.get("routingVersion") != 2
        or contract.get("artifactType") != "baseball-query-index-semantic-contract"
        or contract.get("contractVersion") != 1
        or not isinstance(semantic, dict)
        or semantic.get("contractId") != contract.get("semanticContractId")
        or semantic.get("contract") != "sparql/query-index/semantic-contract.json"
        or required_sha256(
            semantic.get("contractTextSha256"), "routing semantic contractTextSha256"
        )
        != contract_sha256
    ):
        raise ValueError("Routing policy does not admit the exact query-index semantic contract")
    bridge = routing.get("legacyManifestBridge")
    fixed_hashes = bridge.get("fixedImplementationSha256") if isinstance(bridge, dict) else None
    if (
        not isinstance(bridge, dict)
        or bridge.get("bridgeVersion") != 1
        or bridge.get("status") != "reviewed-fixed"
        or bridge.get("appliesOnlyWhenSemanticFieldsAbsent") is not True
        or bridge.get("legacyImplementationField") != "contractSha256"
        or bridge.get("semanticContractId") != contract.get("semanticContractId")
        or required_sha256(
            bridge.get("semanticContractSha256"), "legacy bridge semanticContractSha256"
        )
        != contract_sha256
        or not isinstance(fixed_hashes, list)
        or len(fixed_hashes) != 5
        or len(set(fixed_hashes)) != 5
        or not str(bridge.get("compatibilityReview", "")).strip()
        or not str(bridge.get("requiredOutputValidation", "")).strip()
    ):
        raise ValueError("Routing policy has no fixed reviewed legacy-manifest bridge")
    fixed_legacy = {
        required_sha256(value, f"legacy bridge implementation hash {index}")
        for index, value in enumerate(fixed_hashes)
    }
    if len(fixed_legacy) != 5:
        raise ValueError("Legacy bridge implementation hashes are not unique")
    return {
        "semanticContractId": str(contract["semanticContractId"]),
        "semanticContractSha256": contract_sha256,
        "fixedLegacyImplementationSha256": fixed_legacy,
        "routingSha256": sha256_file(QUERY_INDEX_ROUTING),
        "contract": contract,
    }


def resolve_query_index_manifest_admission(
    index: dict[str, Any], admission: dict[str, Any]
) -> dict[str, str]:
    semantic_fields = {"semanticContractId", "semanticContractSha256"}
    present = semantic_fields.intersection(index)
    if present and present != semantic_fields:
        raise ValueError("query-index manifest has a partial semantic-contract identity")
    if present == semantic_fields:
        if (
            index.get("semanticContractId") != admission["semanticContractId"]
            or required_sha256(
                index.get("semanticContractSha256"), "query-index semanticContractSha256"
            )
            != admission["semanticContractSha256"]
            or (
                "semanticContractPath" in index
                and index.get("semanticContractPath")
                != "sparql/query-index/semantic-contract.json"
            )
        ):
            raise ValueError("query-index manifest does not match the admitted semantic contract")
        implementation = required_sha256(
            index.get("implementationSha256"), "query-index implementationSha256"
        )
        if (
            index.get("implementationFingerprintAlgorithm")
            != "query-index-generation-file-set-v1"
            or (
                "contractSha256" in index
                and required_sha256(index.get("contractSha256"), "query-index contractSha256")
                != implementation
            )
        ):
            raise ValueError("query-index manifest has invalid implementation provenance")
        return {
            "mode": "semantic-contract",
            "semanticContractId": str(admission["semanticContractId"]),
            "semanticContractSha256": str(admission["semanticContractSha256"]),
            "implementationSha256": implementation,
        }
    if "semanticContractPath" in index or "implementationSha256" in index:
        raise ValueError("query-index manifest mixes legacy and separated contract fields")
    implementation = required_sha256(
        index.get("contractSha256"), "legacy query-index contractSha256"
    )
    if implementation not in admission["fixedLegacyImplementationSha256"]:
        raise ValueError("legacy query-index fingerprint is not in the fixed reviewed bridge")
    return {
        "mode": "reviewed-legacy-bridge",
        "semanticContractId": str(admission["semanticContractId"]),
        "semanticContractSha256": str(admission["semanticContractSha256"]),
        "implementationSha256": implementation,
    }


def validated_promotion_record(
    state_root: Path,
    marker_path: Path,
    game_pk: str,
    admission: dict[str, Any],
) -> dict[str, Any]:
    marker = json_object(marker_path)
    if marker.get("artifactType") != "baseball-nifi-game-promotion" or marker.get("contractVersion") != 1:
        raise ValueError("unsupported promotion marker contract")
    if str(marker.get("gamePk", "")) != game_pk:
        raise ValueError("promotion marker game identity mismatch")
    promoted_at = promotion_timestamp(marker.get("promotedAtUtc"))
    raw_sha256 = required_sha256(marker.get("rawSha256"), "promotion rawSha256")
    authoritative_graph = f"{GRAPH_PREFIX}{game_pk}"
    index_graph = f"{INDEX_GRAPH_PREFIX}{game_pk}"
    game_iri = f"{GAME_IRI_PREFIX}{game_pk}"
    index_resource = f"{INDEX_RESOURCE_PREFIX}{game_pk}"
    if marker.get("authoritativeGraph") != authoritative_graph:
        raise ValueError("promotion authoritative graph identity mismatch")
    if marker.get("queryIndexGraph") != index_graph:
        raise ValueError("promotion query-index graph identity mismatch")
    authoritative_count = required_positive_int(
        marker.get("authoritativeTripleCount"), "promotion authoritativeTripleCount"
    )
    index_count = required_positive_int(
        marker.get("queryIndexTripleCount"), "promotion queryIndexTripleCount"
    )
    manifests = state_root / "pipeline" / "manifests"
    expected_rml_path = (manifests / f"game-{game_pk}-rml.json").resolve()
    expected_index_path = (manifests / f"game-{game_pk}-query-index.json").resolve()
    try:
        rml_path = Path(str(marker["rmlManifest"])).resolve()
        index_path = Path(str(marker["queryIndexManifest"])).resolve()
    except (KeyError, OSError, TypeError, ValueError) as exc:
        raise ValueError("promotion marker has invalid manifest references") from exc
    if rml_path != expected_rml_path or index_path != expected_index_path:
        raise ValueError("promotion marker references a manifest outside the per-game contract")
    if not rml_path.is_file() or not index_path.is_file():
        raise ValueError("promotion marker references a missing build manifest")
    marker_rml_sha256 = required_sha256(marker.get("rmlManifestSha256"), "promotion rmlManifestSha256")
    marker_index_sha256 = required_sha256(
        marker.get("queryIndexManifestSha256"), "promotion queryIndexManifestSha256"
    )
    if sha256_file(rml_path) != marker_rml_sha256:
        raise ValueError("promotion RML manifest hash mismatch")
    if sha256_file(index_path) != marker_index_sha256:
        raise ValueError("promotion query-index manifest hash mismatch")
    rml = json_object(rml_path)
    if str(rml.get("gamePk", "")) != game_pk or rml.get("graphIri") != authoritative_graph:
        raise ValueError("RML manifest game or graph identity mismatch")
    if required_sha256(rml.get("inputSha256"), "RML inputSha256") != raw_sha256:
        raise ValueError("RML input hash does not match the promoted raw source")
    authoritative_rdf_sha256 = required_sha256(rml.get("outputSha256"), "RML outputSha256")
    if rml.get("shaclStatus") != "validated":
        raise ValueError("RML manifest is not SHACL-validated")
    index = json_object(index_path)
    if index.get("artifactType") != "baseball-query-index-build":
        raise ValueError("unsupported query-index manifest artifact type")
    version = index.get("contractVersion")
    if isinstance(version, bool) or not isinstance(version, int) or version != SUPPORTED_QUERY_INDEX_CONTRACT_VERSION:
        raise ValueError(
            f"query-index contractVersion is not supported; expected {SUPPORTED_QUERY_INDEX_CONTRACT_VERSION}"
        )
    if str(index.get("gamePk", "")) != game_pk:
        raise ValueError("query-index manifest game identity mismatch")
    if index.get("sourceGraph") != authoritative_graph or index.get("indexGraph") != index_graph:
        raise ValueError("query-index manifest graph identity mismatch")
    if index.get("indexResource") != index_resource:
        raise ValueError("query-index manifest resource identity mismatch")
    if required_sha256(index.get("sourceRdfSha256"), "query-index sourceRdfSha256") != authoritative_rdf_sha256:
        raise ValueError("query-index source hash does not match the authoritative RML output")
    if required_positive_int(index.get("sourceTripleCount"), "query-index sourceTripleCount") != authoritative_count:
        raise ValueError("authoritative triple count differs between promotion and query-index manifests")
    if required_positive_int(index.get("indexTripleCount"), "query-index indexTripleCount") != index_count:
        raise ValueError("index triple count differs between promotion and query-index manifests")
    index_rdf_sha256 = required_sha256(index.get("indexSha256"), "query-index indexSha256")
    manifest_admission = resolve_query_index_manifest_admission(index, admission)
    expected_index_artifact = (
        state_root / "pipeline" / "query-index" / f"game-{game_pk}.nt"
    ).resolve()
    try:
        manifest_index_artifact = Path(str(index["indexPath"])).resolve()
    except (KeyError, OSError, TypeError, ValueError) as exc:
        raise ValueError("query-index manifest has an invalid local artifact path") from exc
    if manifest_index_artifact != expected_index_artifact or not expected_index_artifact.is_file():
        raise ValueError("query-index manifest local artifact is missing or outside its contract")
    if sha256_file(expected_index_artifact) != index_rdf_sha256:
        raise ValueError("query-index local artifact hash mismatch")
    return {
        "gamePk": game_pk,
        "gameIri": game_iri,
        "promotedAtUtc": promoted_at.isoformat().replace("+00:00", "Z"),
        "promotionManifest": str(marker_path.resolve()),
        "promotionManifestSha256": sha256_file(marker_path),
        "rawSha256": raw_sha256,
        "authoritativeGraph": authoritative_graph,
        "authoritativeTripleCount": authoritative_count,
        "authoritativeRdfSha256": authoritative_rdf_sha256,
        "queryIndexGraph": index_graph,
        "queryIndexResource": index_resource,
        "queryIndexTripleCount": index_count,
        "queryIndexRdfSha256": index_rdf_sha256,
        "queryIndexAdmissionMode": manifest_admission["mode"],
        "queryIndexSemanticContractId": manifest_admission["semanticContractId"],
        "queryIndexSemanticContractSha256": manifest_admission["semanticContractSha256"],
        "queryIndexImplementationSha256": manifest_admission["implementationSha256"],
        "rmlManifestSha256": marker_rml_sha256,
        "queryIndexManifestSha256": marker_index_sha256,
    }


def promotion_inventory(state_root: Path) -> dict[str, Any]:
    promotion_root = state_root / "pipeline" / "evidence" / "nifi" / "game-promotion"
    admission = query_index_contract_admission()
    games: dict[str, dict[str, Any]] = {}
    superseded_count = 0
    invalid_games: list[str] = []
    for game_directory in sorted(
        (path for path in promotion_root.glob("*") if path.is_dir() and path.name.isdigit()),
        key=lambda path: int(path.name),
    ):
        candidates: list[tuple[datetime, str, Path]] = []
        errors: list[str] = []
        for marker_path in sorted(game_directory.glob("*.json")):
            try:
                marker = json_object(marker_path)
                candidates.append(
                    (promotion_timestamp(marker.get("promotedAtUtc")), marker_path.name, marker_path)
                )
            except (OSError, ValueError, TypeError) as exc:
                errors.append(f"{marker_path.name}: {exc}")
        if errors:
            invalid_games.append(f"{game_directory.name} ({errors[-1]})")
            continue
        if not candidates:
            continue
        superseded_count += len(candidates) - 1
        marker_path = max(candidates, key=lambda item: (item[0], item[1]))[2]
        try:
            games[game_directory.name] = validated_promotion_record(
                state_root, marker_path, game_directory.name, admission
            )
        except (OSError, ValueError, TypeError) as exc:
            invalid_games.append(f"{game_directory.name} ({marker_path.name}: {exc})")
    if invalid_games:
        raise ValueError(
            "Newest promotion evidence is invalid or cannot be ordered: " + "; ".join(invalid_games[:5])
        )
    if not games:
        raise ValueError("No valid per-game promotion manifests are available")
    canonical_games = [games[game_pk] for game_pk in sorted(games, key=int)]
    fingerprint_payload = {
        "queryIndexRoutingSha256": admission["routingSha256"],
        "queryIndexSemanticContractId": admission["semanticContractId"],
        "queryIndexSemanticContractSha256": admission["semanticContractSha256"],
        "legacyQueryIndexImplementationBridgeSha256Set": sorted(
            admission["fixedLegacyImplementationSha256"]
        ),
        "games": canonical_games,
    }
    fingerprint = sha256_bytes(
        json.dumps(
            fingerprint_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )
    return {
        "fingerprint": fingerprint,
        "gameCount": len(games),
        "supersededManifestCount": superseded_count,
        "queryIndexRoutingSha256": admission["routingSha256"],
        "queryIndexSemanticContractId": admission["semanticContractId"],
        "queryIndexSemanticContractSha256": admission["semanticContractSha256"],
        "legacyQueryIndexImplementationBridgeSha256Set": sorted(
            admission["fixedLegacyImplementationSha256"]
        ),
        "queryIndexImplementationSha256Set": sorted(
            {record["queryIndexImplementationSha256"] for record in games.values()}
        ),
        "games": games,
    }


def game_team_season_preflight_query(inventory: dict[str, Any]) -> str:
    rows = "\n    ".join(
        f"(<{item['indexGraph']}> <{item['authoritativeGraph']}> "
        f"<{item['gameIri']}> <{item['queryIndexResource']}>)"
        for item in (inventory["games"][key] for key in sorted(inventory["games"], key=int))
    )
    contract = query_index_contract_admission()["contract"]
    consumer = next(
        item for item in contract.get("consumerGrains", [])
        if item.get("id") == "game-team-season-v1"
    )
    home, away = consumer["assignmentTypes"]
    team_class = consumer["sourceAssigneeClassIri"]
    return f"""PREFIX idx: <https://w3id.org/baseball/query-index/>
SELECT ?indexGraph ?sourceGraph ?game ?season ?assignment ?assignmentType ?team ?typedTeam WHERE {{
  VALUES (?indexGraph ?sourceGraph ?game ?indexResource) {{
    {rows}
  }}
  GRAPH ?indexGraph {{
    ?indexResource a idx:QueryIndex ; idx:sourceGraph ?sourceGraph ; idx:indexedGame ?game ; idx:contractVersion "1" .
    ?game a idx:GameFact ; idx:season ?season .
    ?assignment a idx:AssignmentFact ; idx:game ?game ; idx:assignmentType ?assignmentType ; idx:assignee ?team .
    VALUES ?assignmentType {{ <{home}> <{away}> }}
  }}
  OPTIONAL {{ GRAPH ?sourceGraph {{ ?team a <{team_class}> }} BIND(?team AS ?typedTeam) }}
}}
ORDER BY ?indexGraph ?assignmentType ?assignment ?team
"""


def validate_game_team_season_rows(
    rows: list[dict[str, str]], inventory: dict[str, Any]
) -> None:
    contract = query_index_contract_admission()["contract"]
    consumer = next(
        item for item in contract.get("consumerGrains", [])
        if item.get("id") == "game-team-season-v1"
    )
    assignment_types = set(consumer["assignmentTypes"])
    team_pattern = re.compile(str(consumer["assigneeIriPattern"]))
    by_graph: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_graph.setdefault(str(row.get("indexGraph", "")), []).append(row)
    expected_graphs = {
        item["queryIndexGraph"]: item for item in inventory["games"].values()
    }
    if set(by_graph) != set(expected_graphs):
        raise ValueError("game-team-season preflight does not cover the exact promoted graph set")
    for graph, expected in expected_graphs.items():
        graph_rows = by_graph[graph]
        if len(graph_rows) != 2:
            raise ValueError(f"game-team-season preflight requires exactly two assignments: {graph}")
        if any(
            row.get("sourceGraph") != expected["authoritativeGraph"]
            or row.get("game") != expected["gameIri"]
            or not re.fullmatch(r"[0-9]{4}", str(row.get("season", "")))
            or row.get("assignmentType") not in assignment_types
            or not team_pattern.fullmatch(str(row.get("team", "")))
            or row.get("typedTeam") != row.get("team")
            for row in graph_rows
        ):
            raise ValueError(f"game-team-season preflight has invalid identity or values: {graph}")
        if {row["assignmentType"] for row in graph_rows} != assignment_types:
            raise ValueError(f"game-team-season preflight lacks one home and one away assignment: {graph}")
        if len({row["assignment"] for row in graph_rows}) != 2:
            raise ValueError(f"game-team-season preflight repeats an assignment: {graph}")
        if len({row["team"] for row in graph_rows}) != 2:
            raise ValueError(f"game-team-season preflight does not identify distinct teams: {graph}")
        if len({row["season"] for row in graph_rows}) != 1:
            raise ValueError(f"game-team-season preflight has multiple seasons: {graph}")
