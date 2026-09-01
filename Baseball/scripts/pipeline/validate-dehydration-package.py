#!/usr/bin/env python3
"""Validate a portable BaseballO dehydration package and all recorded hashes."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath

from pyshacl import validate as validate_shacl
from rdflib import Graph, Namespace, RDF, URIRef


BASE = Namespace("https://baseballontology.org/")
IDX = Namespace("https://w3id.org/baseball/query-index/")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_package_path(root: Path, relative: str) -> Path:
    posix = PurePosixPath(relative)
    if posix.is_absolute() or not posix.parts or any(part in {"", ".", ".."} for part in posix.parts):
        raise ValueError(f"Unsafe package-relative path: {relative!r}")
    resolved = (root / Path(*posix.parts)).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise ValueError(f"Package path escapes its root: {relative!r}") from error
    return resolved


def one_by_role(records: list[dict], role: str) -> dict:
    matches = [record for record in records if record.get("role") == role]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one {role!r} file, found {len(matches)}")
    return matches[0]


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return value


def required_sha256(value: object, label: str) -> str:
    text = str(value or "")
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        raise ValueError(f"{label} is not a lowercase SHA-256 digest")
    return text


def packaged_query_index_admission(root: Path) -> dict[str, object]:
    contract_path = safe_package_path(
        root, "contracts/repository/sparql/query-index/semantic-contract.json"
    )
    routing_path = safe_package_path(
        root, "contracts/repository/sparql/query-index/operational-query-routing.json"
    )
    contract = read_json(contract_path)
    routing = read_json(routing_path)
    contract_sha256 = sha256(contract_path)
    semantic = routing.get("semanticAdmission")
    if (
        contract.get("artifactType") != "baseball-query-index-semantic-contract"
        or contract.get("contractVersion") != 1
        or routing.get("artifactType") != "baseball-reviewed-query-routing"
        or routing.get("routingVersion") != 2
        or not isinstance(semantic, dict)
        or semantic.get("contractId") != contract.get("semanticContractId")
        or semantic.get("contract") != "sparql/query-index/semantic-contract.json"
        or required_sha256(
            semantic.get("contractTextSha256"), "routing semantic contract hash"
        )
        != contract_sha256
    ):
        raise ValueError("Packaged routing does not admit its exact semantic contract")
    bridge = routing.get("legacyManifestBridge")
    fixed = bridge.get("fixedImplementationSha256") if isinstance(bridge, dict) else None
    if (
        not isinstance(bridge, dict)
        or bridge.get("bridgeVersion") != 1
        or bridge.get("status") != "reviewed-fixed"
        or bridge.get("appliesOnlyWhenSemanticFieldsAbsent") is not True
        or bridge.get("legacyImplementationField") != "contractSha256"
        or bridge.get("semanticContractId") != contract.get("semanticContractId")
        or required_sha256(
            bridge.get("semanticContractSha256"), "legacy bridge semantic contract hash"
        )
        != contract_sha256
        or not isinstance(fixed, list)
        or len(fixed) != 5
        or len(set(fixed)) != 5
        or not str(bridge.get("compatibilityReview", "")).strip()
        or not str(bridge.get("requiredOutputValidation", "")).strip()
    ):
        raise ValueError("Packaged routing has no fixed reviewed legacy-manifest bridge")
    fixed_hashes = {
        required_sha256(value, f"legacy bridge implementation hash {position}")
        for position, value in enumerate(fixed)
    }
    if len(fixed_hashes) != 5:
        raise ValueError("Packaged legacy bridge implementation hashes are not unique")
    return {
        "semanticContractId": str(contract["semanticContractId"]),
        "semanticContractSha256": contract_sha256,
        "fixedLegacyImplementationSha256": fixed_hashes,
    }


def resolve_packaged_index_manifest(index: dict, admission: dict[str, object]) -> dict[str, str]:
    semantic_fields = {"semanticContractId", "semanticContractSha256"}
    present = semantic_fields.intersection(index)
    if present and present != semantic_fields:
        raise ValueError("Embedded query-index manifest has a partial semantic identity")
    if present == semantic_fields:
        if (
            index.get("semanticContractId") != admission["semanticContractId"]
            or required_sha256(
                index.get("semanticContractSha256"), "embedded semantic contract hash"
            )
            != admission["semanticContractSha256"]
            or (
                "semanticContractPath" in index
                and index.get("semanticContractPath")
                != "sparql/query-index/semantic-contract.json"
            )
        ):
            raise ValueError("Embedded query-index manifest has the wrong semantic contract")
        implementation = required_sha256(
            index.get("implementationSha256"), "embedded implementation hash"
        )
        if (
            index.get("implementationFingerprintAlgorithm")
            != "query-index-generation-file-set-v1"
            or (
                "contractSha256" in index
                and required_sha256(index.get("contractSha256"), "deprecated implementation alias")
                != implementation
            )
        ):
            raise ValueError("Embedded query-index implementation provenance is invalid")
        mode = "semantic-contract"
    else:
        if "semanticContractPath" in index or "implementationSha256" in index:
            raise ValueError("Embedded query-index manifest mixes legacy and separated fields")
        implementation = required_sha256(
            index.get("contractSha256"), "embedded legacy implementation hash"
        )
        if implementation not in admission["fixedLegacyImplementationSha256"]:
            raise ValueError("Embedded legacy query-index manifest is not in the fixed bridge")
        mode = "reviewed-legacy-bridge"
    return {
        "mode": mode,
        "semanticContractId": str(admission["semanticContractId"]),
        "semanticContractSha256": str(admission["semanticContractSha256"]),
        "implementationSha256": implementation,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("package_directory", type=Path)
    args = parser.parse_args()

    root = args.package_directory.resolve()
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError(f"Package manifest is missing: {manifest_path}")
    manifest = read_json(manifest_path)
    package_version = manifest.get("packageVersion")
    if (
        manifest.get("artifactType") != "baseball-dehydration-package"
        or isinstance(package_version, bool)
        or package_version != 2
    ):
        raise ValueError("Unsupported dehydration package type or version")

    game_pk = str(manifest.get("gamePk", ""))
    if not game_pk.isdigit():
        raise ValueError("Package gamePk must contain only digits")
    records = manifest.get("files")
    if not isinstance(records, list) or not records:
        raise ValueError("Package file inventory is empty")

    inventoried: set[Path] = set()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Package file inventory entries must be objects")
        relative = str(record.get("path", ""))
        path = safe_package_path(root, relative)
        if path in inventoried:
            raise ValueError(f"Duplicate package file inventory path: {relative}")
        inventoried.add(path)
        if not path.is_file():
            raise ValueError(f"Inventoried package file is missing: {relative}")
        if path.stat().st_size != int(record.get("bytes", -1)):
            raise ValueError(f"Byte count mismatch for {relative}")
        if sha256(path) != str(record.get("sha256", "")).lower():
            raise ValueError(f"SHA-256 mismatch for {relative}")

    actual_files = {path.resolve() for path in root.rglob("*") if path.is_file()}
    expected_files = inventoried | {manifest_path.resolve()}
    unexpected = sorted(actual_files - expected_files)
    missing = sorted(expected_files - actual_files)
    if unexpected or missing:
        raise ValueError(
            f"Package inventory closure failed: unexpected={len(unexpected)}; missing={len(missing)}"
        )

    raw_record = one_by_role(records, "raw-source")
    authoritative_record = one_by_role(records, "authoritative-rdf")
    index_record = one_by_role(records, "query-index-rdf")
    rml_manifest_record = one_by_role(records, "rml-build-manifest")
    index_manifest_record = one_by_role(records, "query-index-build-manifest")

    raw_path = safe_package_path(root, raw_record["path"])
    raw = read_json(raw_path)
    if str(raw.get("gamePk", "")) != game_pk:
        raise ValueError("Raw source gamePk does not match the package")
    state = raw.get("gameData", {}).get("status", {}).get("abstractGameState")
    if state != "Final":
        raise ValueError(f"Raw source is not a completed game: {state!r}")

    authoritative_path = safe_package_path(root, authoritative_record["path"])
    authoritative = Graph().parse(authoritative_path, format="turtle")
    index_path = safe_package_path(root, index_record["path"])
    index = Graph().parse(index_path, format="nt")

    shape_profiles = (
        ("authoritative", authoritative, "contracts/repository/shacl/authoritative.ttl"),
        ("query-index", index, "contracts/repository/shacl/query-index.ttl"),
    )
    for profile, data_graph, relative_shape_path in shape_profiles:
        shape_path = safe_package_path(root, relative_shape_path)
        if not shape_path.is_file():
            raise ValueError(f"Packaged SHACL profile is missing: {relative_shape_path}")
        conforms, _, report_text = validate_shacl(
            data_graph=data_graph,
            shacl_graph=Graph().parse(shape_path, format="turtle"),
            inference="none",
            advanced=True,
            allow_infos=True,
            allow_warnings=True,
        )
        if not conforms:
            raise ValueError(f"Packaged {profile} graph fails SHACL validation:\n{report_text}")

    authoritative_contract = manifest.get("authoritativeGraph", {})
    index_contract = manifest.get("queryIndexGraph", {})
    if len(authoritative) != int(authoritative_contract.get("tripleCount", -1)):
        raise ValueError("Authoritative graph triple count differs from the package manifest")
    if len(index) != int(index_contract.get("tripleCount", -1)):
        raise ValueError("Query-index graph triple count differs from the package manifest")

    game = URIRef(f"https://baseballontology.org/data/game/{game_pk}")
    if (game, RDF.type, BASE.BaseballGame) not in authoritative:
        raise ValueError("Authoritative package RDF has no expected BaseballGame assertion")
    index_resource = URIRef(f"https://w3id.org/baseball/query-index-build/game/{game_pk}")
    source_graph = URIRef(str(authoritative_contract.get("graphIri", "")))
    if (index_resource, RDF.type, IDX.QueryIndex) not in index:
        raise ValueError("Query-index package RDF has no QueryIndex metadata resource")
    if (index_resource, IDX.sourceGraph, source_graph) not in index:
        raise ValueError("Query-index package RDF points to the wrong authoritative graph")
    if (index_resource, IDX.indexedGame, game) not in index:
        raise ValueError("Query-index package RDF points to the wrong game")

    rml_manifest = read_json(safe_package_path(root, rml_manifest_record["path"]))
    index_manifest = read_json(safe_package_path(root, index_manifest_record["path"]))
    if str(rml_manifest.get("gamePk")) != game_pk or str(index_manifest.get("gamePk")) != game_pk:
        raise ValueError("Embedded build manifest gamePk does not match the package")
    if rml_manifest.get("inputSha256") != raw_record["sha256"]:
        raise ValueError("RML input hash does not match the packaged raw source")
    if rml_manifest.get("outputSha256") != authoritative_record["sha256"]:
        raise ValueError("RML output hash does not match the packaged authoritative RDF")
    if index_manifest.get("sourceRdfSha256") != authoritative_record["sha256"]:
        raise ValueError("Index source hash does not match the packaged authoritative RDF")
    if index_manifest.get("indexSha256") != index_record["sha256"]:
        raise ValueError("Index output hash does not match the packaged index RDF")
    if rml_manifest.get("graphIri") != authoritative_contract.get("graphIri"):
        raise ValueError("RML graph IRI does not match the package contract")
    if index_manifest.get("indexGraph") != index_contract.get("graphIri"):
        raise ValueError("Index graph IRI does not match the package contract")
    admission = packaged_query_index_admission(root)
    resolved = resolve_packaged_index_manifest(index_manifest, admission)
    if (
        index_contract.get("contractVersion") != index_manifest.get("contractVersion")
        or index_contract.get("semanticContractId") != resolved["semanticContractId"]
        or required_sha256(
            index_contract.get("semanticContractSha256"),
            "package query-index semantic contract hash",
        )
        != resolved["semanticContractSha256"]
        or required_sha256(
            index_contract.get("implementationSha256"),
            "package query-index implementation hash",
        )
        != resolved["implementationSha256"]
        or index_contract.get("implementationFingerprintRole") != "provenance-only"
        or index_contract.get("admissionMode") != resolved["mode"]
    ):
        raise ValueError("Query-index semantic admission differs from the package record")

    print(f"Dehydration package validated: game {game_pk}")
    print(f"Package files: {len(records)}")
    print(f"Authoritative triples: {len(authoritative)}")
    print(f"Query-index triples: {len(index)}")


if __name__ == "__main__":
    main()
