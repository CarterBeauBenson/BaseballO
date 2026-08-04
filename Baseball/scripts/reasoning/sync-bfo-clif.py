#!/usr/bin/env python3
"""Fetch the pinned BFO CLIF modules and fail closed on any byte change."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "reasoning" / "bfo-clif-manifest.json"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if manifest.get("artifactType") != "baseball-bfo-clif-source-manifest":
        raise ValueError("Unknown BFO CLIF source manifest")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    base_url = str(manifest["baseUrl"]).rstrip("/")

    for entry in manifest["modules"]:
        name = str(entry["name"])
        destination = output / name
        if destination.parent != output or not name.endswith(".cl"):
            raise ValueError(f"Unsafe CLIF module name: {name}")
        if destination.exists():
            data = destination.read_bytes()
        else:
            request = urllib.request.Request(
                f"{base_url}/{name}",
                headers={"User-Agent": "BaseballO-selective-reasoning"},
            )
            with urllib.request.urlopen(request, timeout=30) as response:
                data = response.read()
        actual_hash = sha256(data)
        if len(data) != int(entry["bytes"]) or actual_hash != entry["sha256"]:
            raise ValueError(
                f"Pinned BFO CLIF verification failed for {name}: "
                f"bytes={len(data)}, sha256={actual_hash}"
            )
        if not destination.exists():
            handle, temporary_name = tempfile.mkstemp(
                prefix=f".{name}.", suffix=".tmp", dir=output
            )
            try:
                with os.fdopen(handle, "wb") as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary_name, destination)
            finally:
                if os.path.exists(temporary_name):
                    os.unlink(temporary_name)
        print(f"Verified {name}: {actual_hash}")

    cache_manifest = output / "source-manifest.json"
    cache_manifest.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"Pinned BFO CLIF cache ready: {output}")


if __name__ == "__main__":
    main()
