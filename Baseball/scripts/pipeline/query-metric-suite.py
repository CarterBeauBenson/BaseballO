#!/usr/bin/env python3
"""Read-only RDF binding reducer for bounded developer comparisons.

The metrics HTTP routes use prepared SQL and do not invoke this tool. A local
caller supplies existing SPARQL bindings through stdin; this tool neither
queries Fuseki nor acquires source data. Recurring extraction and SQL
materialization remain owned by NiFi.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('baseballo_metric_suite', ROOT / 'serving/metric_suite.py')
metrics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metrics)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--state-root')  # Shared process invocation; no state read or write.
    parser.parse_args()
    try:
        request = json.load(sys.stdin)
        graphs = request['graphs']
        metrics.evidence_query(graphs)  # Validate the exact authoritative scope.
        rows = metrics.normalize_bindings(request['bindings'], graphs)
        result = {**metrics.selected_results(request, rows, graph_count=len(set(graphs))),
                  'implementationSha256': metrics.fingerprint(), 'execution': 'authoritative-rdf',
                  'graphCount': len(set(graphs))}
        print(json.dumps(result, ensure_ascii=True))
        return 0
    except Exception as exc:
        print(json.dumps({'status': 'unavailable', 'error': str(exc)}, ensure_ascii=True))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
