#!/usr/bin/env python3
"""Validate a portable BaseballO dehydration package and all recorded hashes."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath

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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("package_directory", type=Path)
    args = parser.parse_args()

    root = args.package_directory.resolve()
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError(f"Package manifest is missing: {manifest_path}")
    manifest = read_json(manifest_path)
    if manifest.get("artifactType") != "baseball-dehydration-package" or manifest.get("packageVersion") != 1:
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
    if index_manifest.get("contractSha256") != index_contract.get("contractSha256"):
        raise ValueError("Index generation-contract hash does not match the package contract")

    print(f"Dehydration package validated: game {game_pk}")
    print(f"Package files: {len(records)}")
    print(f"Authoritative triples: {len(authoritative)}")
    print(f"Query-index triples: {len(index)}")


if __name__ == "__main__":
    main()
