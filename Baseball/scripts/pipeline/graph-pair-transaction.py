#!/usr/bin/env python3
"""Recoverable logical transaction for one authoritative/query-index graph pair."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from rdflib import Graph
from rdflib.compare import isomorphic

GAME = re.compile(r"^[1-9][0-9]*$")
RUN = re.compile(r"^[0-9a-f]{32}$")


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def atomic_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", delete=False, dir=path.parent) as output:
        output.write(value)
        temporary = Path(output.name)
    os.replace(temporary, path)


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    atomic_bytes(path, (json.dumps(value, indent=2) + "\n").encode())


def read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def nt_graph(value: bytes) -> Graph:
    graph = Graph()
    if value.strip():
        graph.parse(data=value.decode("utf-8"), format="nt")
    return graph


class GraphStore(Protocol):
    def get(self, graph: str) -> bytes | None: ...
    def put(self, graph: str, body: bytes) -> None: ...
    def delete(self, graph: str) -> None: ...


class HttpGraphStore:
    def __init__(self, endpoint: str) -> None:
        self.endpoint = endpoint

    def _url(self, graph: str) -> str:
        return self.endpoint + "?graph=" + urllib.parse.quote(graph, safe="")

    def get(self, graph: str) -> bytes | None:
        request = urllib.request.Request(self._url(graph), headers={"Accept": "application/n-triples"})
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                if int(response.status) != 200:
                    raise RuntimeError(f"graph GET returned {response.status}")
                return response.read()
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return None
            raise

    def put(self, graph: str, body: bytes) -> None:
        request = urllib.request.Request(self._url(graph), data=body, method="PUT", headers={"Content-Type": "application/n-triples"})
        with urllib.request.urlopen(request, timeout=120) as response:
            if int(response.status) not in {200, 201, 204}:
                raise RuntimeError(f"graph PUT returned {response.status}")

    def delete(self, graph: str) -> None:
        request = urllib.request.Request(self._url(graph), method="DELETE")
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                if int(response.status) not in {200, 204}:
                    raise RuntimeError(f"graph DELETE returned {response.status}")
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise


def paths(state_root: Path, game: str, run: str) -> tuple[Path, Path]:
    work = state_root.resolve() / "pipeline" / "work" / "graph-pair-transactions" / game / run
    evidence = state_root.resolve() / "pipeline" / "evidence" / "nifi" / "graph-pair-transactions" / game / run
    return work, evidence


def graph_names(game: str) -> dict[str, str]:
    return {
        "authoritative": f"https://w3id.org/baseball/graph/game/{game}",
        "index": f"https://w3id.org/baseball/graph/query-index/game/{game}",
    }


def event(evidence: Path, kind: str, value: dict[str, Any]) -> Path:
    identity = hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    target = evidence / f"{kind}-{identity}.json"
    if target.is_file():
        if read(target) != value:
            raise RuntimeError("immutable graph-pair transaction event conflicts")
    else:
        atomic_json(target, value)
    return target


def prepare(store: GraphStore, state_root: Path, game: str, run: str) -> dict[str, Any]:
    work, evidence = paths(state_root, game, run)
    manifest_path = work / "transaction.json"
    if manifest_path.is_file():
        manifest = read(manifest_path)
        if manifest.get("gamePk") != game or manifest.get("runId") != run:
            raise RuntimeError("graph-pair transaction identity conflicts")
        return manifest
    snapshots: dict[str, dict[str, Any]] = {}
    for name, graph in graph_names(game).items():
        body = store.get(graph)
        if body is None:
            snapshots[name] = {"graph": graph, "existed": False, "tripleCount": 0, "sha256": None, "backup": None}
            continue
        parsed = nt_graph(body)
        backup = work / f"{name}.nt"
        atomic_bytes(backup, body)
        snapshots[name] = {"graph": graph, "existed": True, "tripleCount": len(parsed), "sha256": sha_bytes(body), "backup": backup.name}
    manifest = {"artifactType": "baseballo-graph-pair-transaction", "contractVersion": 1, "gamePk": game, "runId": run, "state": "prepared", "preparedAtUtc": now(), "snapshots": snapshots}
    atomic_json(manifest_path, manifest)
    event(evidence, "prepared", {**manifest, "eventType": "prepared"})
    return manifest


def restore(store: GraphStore, state_root: Path, game: str, run: str, reason: str) -> dict[str, Any]:
    work, evidence = paths(state_root, game, run)
    manifest_path = work / "transaction.json"
    manifest = read(manifest_path)
    if manifest.get("state") == "restored":
        return manifest
    if manifest.get("state") == "committed":
        raise RuntimeError("refusing to restore a committed graph pair")
    for snapshot in manifest["snapshots"].values():
        graph = str(snapshot["graph"])
        if snapshot["existed"]:
            backup = work / str(snapshot["backup"])
            body = backup.read_bytes()
            if sha_bytes(body) != snapshot["sha256"]:
                raise RuntimeError("graph-pair backup hash changed")
            store.put(graph, body)
            restored = store.get(graph)
            if restored is None or not isomorphic(nt_graph(body), nt_graph(restored)):
                raise RuntimeError("restored graph is not isomorphic to its snapshot")
        else:
            store.delete(graph)
            if store.get(graph) is not None:
                raise RuntimeError("graph that was absent before the transaction still exists")
    manifest = {**manifest, "state": "restored", "restoredAtUtc": now(), "restoreReason": reason}
    atomic_json(manifest_path, manifest)
    event(evidence, "restored", {**manifest, "eventType": "restored"})
    return manifest


def commit(state_root: Path, game: str, run: str) -> dict[str, Any]:
    work, evidence = paths(state_root, game, run)
    manifest_path = work / "transaction.json"
    manifest = read(manifest_path)
    if manifest.get("state") == "restored":
        raise RuntimeError("refusing to commit a restored graph pair")
    if manifest.get("state") != "committed":
        manifest = {**manifest, "state": "committed", "committedAtUtc": now()}
        atomic_json(manifest_path, manifest)
        event(evidence, "committed", {**manifest, "eventType": "committed"})
    for name in ("authoritative.nt", "index.nt"):
        backup = work / name
        if backup.is_file():
            backup.unlink()
    return manifest


def recover(store: GraphStore, state_root: Path, game: str) -> dict[str, Any]:
    root = state_root.resolve() / "pipeline" / "work" / "graph-pair-transactions" / game
    restored: list[str] = []
    committed: list[str] = []
    for manifest_path in sorted(root.glob("*/transaction.json")):
        manifest = read(manifest_path)
        if manifest.get("state") != "prepared":
            continue
        run = manifest_path.parent.name
        promotion = state_root.resolve() / "pipeline" / "evidence" / "nifi" / "game-promotion" / game / f"{run}.json"
        if promotion.is_file():
            commit(state_root, game, run)
            committed.append(run)
        else:
            restore(store, state_root, game, run, "recovered-uncommitted-transaction")
            restored.append(run)
    return {"artifactType": "baseballo-graph-pair-recovery", "contractVersion": 1, "gamePk": game, "recoveredAtUtc": now(), "restoredRuns": restored, "committedRuns": committed}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-root", type=Path, required=True)
    parser.add_argument("--game-pk", required=True)
    parser.add_argument("--run-id")
    parser.add_argument("--graph-store", default="http://127.0.0.1:3031/baseball-dev/data")
    parser.add_argument("--action", choices=("prepare", "restore", "commit", "recover"), required=True)
    parser.add_argument("--reason", default="stage-failure")
    args = parser.parse_args()
    if not GAME.fullmatch(args.game_pk) or (args.action != "recover" and not RUN.fullmatch(str(args.run_id or ""))):
        raise SystemExit("invalid game or run identity")
    store = HttpGraphStore(args.graph_store)
    if args.action == "prepare":
        result = prepare(store, args.state_root, args.game_pk, args.run_id)
    elif args.action == "restore":
        result = restore(store, args.state_root, args.game_pk, args.run_id, args.reason)
    elif args.action == "commit":
        result = commit(args.state_root, args.game_pk, args.run_id)
    else:
        result = recover(store, args.state_root, args.game_pk)
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
