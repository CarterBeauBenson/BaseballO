#!/usr/bin/env python3
"""Reconcile immutable promotion evidence after verified manifest rebuilds."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import tempfile
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rdflib import Graph, RDF, URIRef
from rdflib.compare import isomorphic


MODULE_ROOT = Path(__file__).resolve().parents[1]
BASEBALL_ROOT = MODULE_ROOT.parents[1]
INVENTORY_PATH = BASEBALL_ROOT / "scripts" / "pipeline" / "game_promotion_inventory.py"
GAME_TYPE = URIRef("https://baseballontology.org/BaseballGame")


def load_inventory_module():
    spec = importlib.util.spec_from_file_location("game_promotion_inventory", INVENTORY_PATH)
    if spec is None or spec.loader is None:
        raise ValueError("cannot load game promotion inventory")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


INVENTORY = load_inventory_module()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-root", type=Path, required=True)
    parser.add_argument("--game-pk", action="append", required=True)
    parser.add_argument(
        "--graph-store", default="http://127.0.0.1:3031/baseball-dev/data"
    )
    return parser.parse_args()


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".partial",
            delete=False,
        ) as stream:
            temporary_name = stream.name
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
        temporary_name = None
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)


def graph_bytes(endpoint: str, graph: str) -> bytes:
    url = endpoint + "?graph=" + urllib.parse.quote(graph, safe="")
    request = urllib.request.Request(url, headers={"Accept": "application/n-triples"})
    with urllib.request.urlopen(request, timeout=120) as response:
        if int(response.status) != 200:
            raise ValueError(f"graph read returned status {response.status}: {graph}")
        return response.read()


def nt_graph(value: bytes) -> Graph:
    graph = Graph()
    graph.parse(data=value.decode("utf-8"), format="nt")
    return graph


def current_markers(root: Path, game_pk: str) -> list[tuple[Path, dict[str, Any]]]:
    directory = root / "pipeline" / "evidence" / "nifi" / "game-promotion" / game_pk
    markers: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(directory.glob("*.json")):
        marker = INVENTORY.json_object(path)
        if str(marker.get("gamePk", "")) == game_pk:
            markers.append((path, marker))
    if not markers:
        raise ValueError(f"game {game_pk} has no prior promotion evidence")
    return markers


def reconcile_game(state_root: Path, graph_store: str, game_pk: str) -> Path:
    if not game_pk.isdigit() or int(game_pk) <= 0:
        raise ValueError(f"invalid game identity: {game_pk}")
    pipeline = state_root / "pipeline"
    manifest_root = pipeline / "manifests"
    rml_path = (manifest_root / f"game-{game_pk}-rml.json").resolve()
    index_path = (manifest_root / f"game-{game_pk}-query-index.json").resolve()
    rml = INVENTORY.json_object(rml_path)
    index = INVENTORY.json_object(index_path)
    source_graph = f"{INVENTORY.GRAPH_PREFIX}{game_pk}"
    index_graph = f"{INVENTORY.INDEX_GRAPH_PREFIX}{game_pk}"
    game_iri = f"{INVENTORY.GAME_IRI_PREFIX}{game_pk}"
    index_resource = f"{INVENTORY.INDEX_RESOURCE_PREFIX}{game_pk}"
    if str(rml.get("gamePk", "")) != game_pk or rml.get("graphIri") != source_graph:
        raise ValueError(f"game {game_pk} RML manifest identity mismatch")
    if rml.get("shaclStatus") != "validated":
        raise ValueError(f"game {game_pk} RML manifest is not SHACL validated")
    raw_sha = INVENTORY.required_sha256(rml.get("inputSha256"), "RML inputSha256")
    source_rdf_sha = INVENTORY.required_sha256(
        rml.get("outputSha256"), "RML outputSha256"
    )
    if (
        str(index.get("gamePk", "")) != game_pk
        or index.get("sourceGraph") != source_graph
        or index.get("indexGraph") != index_graph
        or index.get("indexResource") != index_resource
    ):
        raise ValueError(f"game {game_pk} query-index manifest identity mismatch")
    if (
        INVENTORY.required_sha256(index.get("sourceRdfSha256"), "index sourceRdfSha256")
        != source_rdf_sha
    ):
        raise ValueError(f"game {game_pk} index was not built from the current RML output")
    admission = INVENTORY.query_index_contract_admission()
    INVENTORY.resolve_query_index_manifest_admission(index, admission)

    expected_index_artifact = (
        pipeline / "query-index" / f"game-{game_pk}.nt"
    ).resolve()
    if Path(str(index.get("indexPath", ""))).resolve() != expected_index_artifact:
        raise ValueError(f"game {game_pk} index artifact path mismatch")
    if not expected_index_artifact.is_file():
        raise ValueError(f"game {game_pk} index artifact is missing")
    index_sha = INVENTORY.required_sha256(index.get("indexSha256"), "index indexSha256")
    if INVENTORY.sha256_file(expected_index_artifact) != index_sha:
        raise ValueError(f"game {game_pk} local index hash mismatch")

    prior = current_markers(state_root, game_pk)
    prior_raw_hashes = {
        str(marker.get("rawSha256", "")) for _, marker in prior
    }
    payloads = sorted((pipeline / "transient" / "mlb-game").glob(f"game-{game_pk}-*.json"))
    payload_anchor = any(INVENTORY.sha256_file(path) == raw_sha for path in payloads)
    current_rml_hash = INVENTORY.sha256_file(rml_path)
    prior_rml_anchor = any(
        str(marker.get("rawSha256", "")) == raw_sha
        and str(marker.get("rmlManifestSha256", "")) == current_rml_hash
        for _, marker in prior
    )
    if raw_sha not in prior_raw_hashes or not (payload_anchor or prior_rml_anchor):
        raise ValueError(f"game {game_pk} has no retained source or immutable RML anchor")

    live_source = nt_graph(graph_bytes(graph_store, source_graph))
    live_index = nt_graph(graph_bytes(graph_store, index_graph))
    if (URIRef(game_iri), RDF.type, GAME_TYPE) not in live_source:
        raise ValueError(f"game {game_pk} live authoritative graph has no BaseballGame assertion")
    source_count = INVENTORY.required_positive_int(
        index.get("sourceTripleCount"), "index sourceTripleCount"
    )
    index_count = INVENTORY.required_positive_int(
        index.get("indexTripleCount"), "index indexTripleCount"
    )
    if len(live_source) != source_count or len(live_index) != index_count:
        raise ValueError(f"game {game_pk} live graph counts differ from the index manifest")
    local_index = Graph().parse(expected_index_artifact, format="nt")
    if not isomorphic(live_index, local_index):
        raise ValueError(f"game {game_pk} live index differs from its local artifact")

    local_rdf = pipeline / "rdf" / f"game-{game_pk}.ttl"
    if local_rdf.is_file():
        if INVENTORY.sha256_file(local_rdf) != source_rdf_sha:
            raise ValueError(f"game {game_pk} serialized RDF hash differs from its RML manifest")
        if not isomorphic(live_source, Graph().parse(local_rdf, format="turtle")):
            raise ValueError(f"game {game_pk} live authoritative graph differs from serialized RDF")
    elif not prior_rml_anchor:
        raise ValueError(f"game {game_pk} has neither serialized RDF nor an immutable RML anchor")

    previous_path, _ = max(
        prior,
        key=lambda item: (INVENTORY.promotion_timestamp(item[1].get("promotedAtUtc")), item[0].name),
    )
    identity_payload = {
        "gamePk": game_pk,
        "rawSha256": raw_sha,
        "rmlManifestSha256": current_rml_hash,
        "queryIndexManifestSha256": INVENTORY.sha256_file(index_path),
        "authoritativeTripleCount": len(live_source),
        "queryIndexTripleCount": len(live_index),
    }
    repair_id = hashlib.sha256(
        json.dumps(identity_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:32]
    target = previous_path.parent / f"{repair_id}.json"
    if target.is_file():
        INVENTORY.validated_promotion_record(state_root, target, game_pk, admission)
        return target

    marker = {
        "artifactType": "baseball-nifi-game-promotion",
        "contractVersion": 1,
        "gamePk": game_pk,
        "pipelineRunId": repair_id,
        "transactionRunId": repair_id,
        "promotedAtUtc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "rawSha256": raw_sha,
        "authoritativeGraph": source_graph,
        "authoritativeTripleCount": len(live_source),
        "queryIndexGraph": index_graph,
        "queryIndexTripleCount": len(live_index),
        "rmlManifest": str(rml_path),
        "rmlManifestSha256": current_rml_hash,
        "queryIndexManifest": str(index_path),
        "queryIndexManifestSha256": INVENTORY.sha256_file(index_path),
        "evidenceReconciliation": {
            "kind": "verified-existing-graph-pair",
            "previousPromotionEvidence": str(previous_path.resolve()),
            "retainedPayloadVerified": payload_anchor,
            "serializedRdfVerified": local_rdf.is_file(),
            "liveIndexArtifactIsomorphic": True,
            "perGameQueryEquivalenceRequiredBeforeInvocation": True,
        },
    }
    atomic_json(target, marker)
    INVENTORY.validated_promotion_record(state_root, target, game_pk, admission)
    return target


def main() -> int:
    args = parse_args()
    state_root = args.state_root.resolve()
    repaired = [
        str(reconcile_game(state_root, args.graph_store, str(game_pk)).resolve())
        for game_pk in args.game_pk
    ]
    inventory = INVENTORY.promotion_inventory(state_root)
    print(
        json.dumps(
            {
                "artifactType": "baseballo-promotion-evidence-reconciliation",
                "contractVersion": 1,
                "reconciledGames": [str(value) for value in args.game_pk],
                "evidence": repaired,
                "inventoryGameCount": inventory["gameCount"],
                "corpusFingerprint": inventory["fingerprint"],
            },
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print(f"Promotion evidence reconciliation failed: {error}")
        raise SystemExit(2)
