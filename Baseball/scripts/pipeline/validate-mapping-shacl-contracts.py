#!/usr/bin/env python3
"""Run the offline direct-mapping and SHACL contract gate for NiFi."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_repository import validate_shacl_profiles  # noqa: E402


def main() -> None:
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "mappings" / "direct" / "validate_direct_mapping.py"),
            str(ROOT / "data" / "raw" / "game-566279.json"),
        ],
        cwd=ROOT,
        check=True,
    )
    shape_count = validate_shacl_profiles()
    print(f"Mapping fixture passed; SHACL node shapes meta-validated: {shape_count}")


if __name__ == "__main__":
    main()
