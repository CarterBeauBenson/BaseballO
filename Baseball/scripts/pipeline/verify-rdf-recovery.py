#!/usr/bin/env python3
"""Focused isolated Fuseki -> gzip backup -> export -> TDB2 restore proof."""
import argparse
import importlib.util
import json
import os
import socket
import subprocess
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

SPEC = importlib.util.spec_from_file_location('rdf_recovery', Path(__file__).with_name('rdf-recovery.py'))
RECOVERY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RECOVERY)


def run(args):
    root = args.proof_root.resolve()
    root.mkdir(parents=True, exist_ok=False)
    base = root / 'fuseki'
    base.mkdir()
    backups = base / 'backups'
    backups.mkdir()
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        port = listener.getsockname()[1]
    server = f'http://127.0.0.1:{port}'
    environment = dict(os.environ, FUSEKI_BASE=str(base), FUSEKI_HOME=str(args.jena.resolve().parent))
    query = '''PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?graph ?label WHERE {
 { ?s rdfs:label ?label BIND("default" AS ?graph) }
 UNION { GRAPH ?g { ?s rdfs:label ?label } BIND(STR(?g) AS ?graph) }
} ORDER BY ?graph ?label'''
    update = '''PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
INSERT DATA {
 <urn:fixture:default> rdfs:label "Default graph" .
 GRAPH <urn:fixture:game:1> {
  <urn:fixture:runner> rdfs:label "José — runner" .
  _:fixture rdfs:label "Blank node label" .
 }
 GRAPH <urn:fixture:game:2> {
  <urn:fixture:count> rdfs:label "9007199254740993"^^<http://www.w3.org/2001/XMLSchema#integer> .
 }
}'''
    with (root / 'server.stdout.log').open('wb') as out, (root / 'server.stderr.log').open('wb') as err:
        process = subprocess.Popen([str(args.java), '-Xmx256m', '-jar', str(args.jena), '--localhost',
                                    f'--port={port}', '--mem', '/recovery-proof'],
                                   env=environment, cwd=base, stdout=out, stderr=err,
                                   creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        try:
            deadline = time.monotonic() + 30
            while True:
                try:
                    with urlopen(server + '/$/ping', timeout=1):
                        break
                except OSError:
                    if process.poll() is not None or time.monotonic() >= deadline:
                        raise RuntimeError('Isolated Fuseki did not start; inspect its logs')
                    time.sleep(0.1)
            with urlopen(Request(server + '/recovery-proof/update', data=update.encode('utf-8'),
                                 headers={'Content-Type': 'application/sparql-update'}), timeout=10):
                pass
            with urlopen(Request(server + '/recovery-proof/query', data=urlencode({'query': query}).encode(),
                                 headers={'Accept': 'application/sparql-results+json'}), timeout=10) as response:
                before = json.load(response)
            if len(before['results']['bindings']) != 4:
                raise AssertionError('Fixture source dataset is incomplete')
            job = RECOVERY.submit(root / 'recovery', server, 'recovery-proof', backups)
            deadline = time.monotonic() + 30
            def task_request(*request_args):
                observed = RECOVERY.http_json(*request_args)
                RECOVERY.atomic_json(root / 'task-response.json', {'response': observed})
                return observed
            while True:
                completed = RECOVERY.complete(root / 'recovery', job['jobId'], request=task_request)
                if completed['status'] == 'verified':
                    break
                if time.monotonic() >= deadline:
                    raise TimeoutError('Fixture backup did not finish')
                time.sleep(0.1)
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
    destination = root / 'export'
    destination.mkdir()
    manifest = RECOVERY.export(root / 'recovery', job['jobId'], destination)
    stage = RECOVERY.stage_restore(destination / ('baseballo-rdf-' + job['jobId']), root / 'recovery', args.java, args.jena, timeout=30)
    query_path = root / 'restored-query.rq'
    query_path.write_text(query, encoding='utf-8')
    executed = subprocess.run([str(args.java), '-cp', str(args.jena), 'tdb2.tdbquery', '--loc=' + stage['databasePath'],
                               '--query=' + str(query_path), '--results=JSON'], capture_output=True, check=True, timeout=30,
                              creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    after = json.loads(executed.stdout)
    if before['head'] != after['head'] or before['results'] != after['results']:
        raise AssertionError('Restored graph names, literal values or datatypes differ')
    proof = {'artifactType': 'baseballo-rdf-recovery-fixture-proof', 'status': 'passed', 'checkedAtUtc': RECOVERY.now(),
             'scope': 'synthetic-isolated-fixture', 'liveDatasetTouched': False, 'offMachineCopy': False,
             'bindings': 4, 'namedGraphs': 2, 'defaultGraphPreserved': True, 'unicodePreserved': True,
             'blankNodeLabelPreserved': True, 'largeIntegerPreserved': True,
             'archiveSha256': manifest['archive']['sha256'], 'restore': stage}
    RECOVERY.atomic_json(root / 'verification.json', proof)
    return proof


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--java', type=Path, required=True)
    parser.add_argument('--jena', type=Path, required=True)
    parser.add_argument('--proof-root', type=Path, required=True)
    print(json.dumps(run(parser.parse_args()), ensure_ascii=True))
