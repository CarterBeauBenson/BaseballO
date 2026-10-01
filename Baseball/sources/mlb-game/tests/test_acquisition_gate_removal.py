"""Acquisition migration preserves queued work and the per-game lifecycle."""
import copy
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / 'nifi/remove-acquisition-gate.py'
spec = importlib.util.spec_from_file_location('direct_acquisition', path)
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)


class NiFi:
    def __init__(self):
        self.calls = []
        names = [('prepare', 'Prepare Schedule Batch'), ('acquire', 'Acquire MLB Schedule'),
                 ('check', 'Check Proof Release'), ('exit', 'Require Proof Release Success'),
                 ('retry', 'Retry Proof Release Readiness'), ('fail', 'Fail Proof Release'),
                 ('quarantine', 'Name Schedule Quarantine'), ('rml', 'RML'), ('shacl', 'Source SHACL')]
        self.processors = {i: dict(id=i, revision=dict(version=0),
            component=dict(id=i, name=n, state='RUNNING'),
            status=dict(aggregateSnapshot=dict(activeThreadCount=0))) for i, n in names}
        self.connections = {}
        for i, source, destination, relationship, count in [
                ('entry', 'prepare', 'check', 'success', 1),
                ('result', 'check', 'exit', 'original', 0),
                ('passed', 'exit', 'acquire', 'passed', 0),
                ('waiting', 'exit', 'retry', 'unmatched', 0),
                ('retrying', 'retry', 'check', 'retry', 1),
                ('exhausted', 'retry', 'fail', 'retries_exceeded', 0),
                ('failed', 'fail', 'quarantine', 'success', 0)]:
            self.connections[i] = dict(id=i, revision=dict(version=0), component=dict(id=i, name=i,
                source=dict(id=source), destination=dict(id=destination), selectedRelationships=[relationship]),
                status=dict(aggregateSnapshot=dict(flowFilesQueued=count)))

    def api(self, method, path, body=None):
        self.calls.append((method, path))
        if path.startswith('/flow/'):
            return copy.deepcopy(dict(processGroupFlow=dict(flow=dict(
                processors=list(self.processors.values()), connections=list(self.connections.values())))))
        parts = path.split('?')[0].strip('/').split('/')
        table = self.processors if parts[0] == 'processors' else self.connections
        entity = table[parts[1]]
        if method == 'PUT':
            if parts[-1] == 'run-status':
                entity['component']['state'] = body['state']
            else:
                entity['component'] = copy.deepcopy(body['component'])
            entity['revision']['version'] += 1
        elif method == 'DELETE':
            if table is self.connections:
                assert entity['status']['aggregateSnapshot']['flowFilesQueued'] == 0
            del table[parts[1]]
        return copy.deepcopy(entity)


class AcquisitionMigration(unittest.TestCase):
    def test_preserves_queued_requests_then_removes_only_retired_processors(self):
        n = NiFi()
        result = M.reconcile('mlb', n.api)
        self.assertEqual(result['status'], 'draining')
        self.assertEqual(result['preservedRequests'], 2)
        self.assertEqual(set(n.connections), {'entry', 'retrying'})
        self.assertTrue(all(c['component']['destination']['id'] == 'acquire' for c in n.connections.values()))
        self.assertEqual(n.connections['entry']['component']['name'], M.DIRECT)
        self.assertEqual(n.processors['retry']['component']['state'], 'STOPPED')
        self.assertEqual(n.processors['acquire']['component']['state'], 'RUNNING')
        for c in n.connections.values():
            c['status']['aggregateSnapshot']['flowFilesQueued'] = 0
        self.assertEqual(M.reconcile('mlb', n.api)['status'], 'complete')
        self.assertEqual(set(n.processors), {'prepare', 'acquire', 'quarantine', 'rml', 'shacl'})
        before = len(n.calls)
        self.assertEqual(M.reconcile('mlb', n.api)['status'], 'complete')
        self.assertTrue(all(method == 'GET' for method, _ in n.calls[before:]))
        self.assertFalse(any(method != 'GET' and ('/rml' in path or '/shacl' in path)
                             for method, path in n.calls))

    def test_conflicting_direct_route_stops_before_mutation(self):
        n = NiFi()
        n.connections['entry']['component']['name'] = M.DIRECT
        with self.assertRaisesRegex(ValueError, 'differs'):
            M.reconcile('mlb', n.api)
        self.assertTrue(all(method == 'GET' for method, _ in n.calls))


if __name__ == '__main__':
    unittest.main()
