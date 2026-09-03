#!/usr/bin/env python3
"""Read pending SQL routes solely for pre-admission equivalence evidence."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
ADAPTER_PATH = ROOT / "scripts" / "pipeline" / "query-serving-layer.py"
SPEC = importlib.util.spec_from_file_location("baseballo_serving_adapter_candidate", ADAPTER_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Could not load {ADAPTER_PATH}")
ADAPTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ADAPTER)
ORIGINAL_ADMISSION = ADAPTER.require_materialized_route_admission


def allow_candidate_route(request: dict[str, Any], contract: dict[str, Any]) -> None:
    """Preserve all admission validation except the final pending-status gate."""
    try:
        ORIGINAL_ADMISSION(request, contract)
    except ValueError as exc:
        if " is not admitted to materialized SQL" not in str(exc):
            raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    default_state = Path(
        os.environ.get("BASEBALLO_STATE_ROOT")
        or Path(os.environ.get("LOCALAPPDATA", ".")) / "BaseballO" / "state"
    )
    parser.add_argument("--state-root", type=Path, default=default_state)
    args = parser.parse_args()
    try:
        request = json.load(sys.stdin)
        if not isinstance(request, dict):
            raise ValueError("Serving request must be an object")
        ADAPTER.require_materialized_route_admission = allow_candidate_route
        result = ADAPTER.query(args, request)
        print(json.dumps(result, separators=(",", ":"), ensure_ascii=True))
        return 0
    except Exception as exc:
        print(
            json.dumps(
                {"status": "unavailable", "error": str(exc)},
                separators=(",", ":"),
                ensure_ascii=True,
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
