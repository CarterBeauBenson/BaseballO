#!/usr/bin/env python3
"""NiFi entry point for static contracts plus real RMLMapper compatibility."""

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


subprocess.run(
    [sys.executable, str(ROOT / "scripts" / "pipeline" / "validate-mapping-shacl-contracts.py")],
    cwd=ROOT,
    check=True,
)
subprocess.run(
    [sys.executable, str(ROOT / "tests" / "test_rmlmapper_iterator_compatibility.py")],
    cwd=ROOT,
    check=True,
)
