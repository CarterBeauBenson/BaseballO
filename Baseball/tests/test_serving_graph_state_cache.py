import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('graph_state_cache_test',ROOT/'scripts/pipeline/serving_graph_state_cache.py')
C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)


class GraphStateCache(unittest.TestCase):
    def server(self):
        services=[{'srv.type':op,'srv.endpoints':[name]} for name,op in
                  [('query','query'),('data','gsp-rw'),('update','update')]]
        server={'startDateTime':'2026-09-23T00:00:00Z','datasets':[
            {'ds.name':'/baseball-dev','ds.state':True,'ds.services':services}]}
        stats={'datasets':{'/baseball-dev':{'endpoints':{name:{'operation':op,'Requests':2,
            'RequestsGood':2,'RequestsBad':0} for name,op in [('query','query'),('data','gsp-rw'),('update','update')]}}}}
        return server,stats

    def test_write_counters_and_restart_identity_exclude_read_requests(self):
        server,stats=self.server();endpoint='http://127.0.0.1:3031/baseball-dev/query'
        with patch.object(C,'read_json',side_effect=lambda url:stats if url.endswith('/stats') else server):
            first=C.state_token(endpoint)
            self.assertIsNotNone(first)
            stats['datasets']['/baseball-dev']['endpoints']['query']['Requests']+=5
            self.assertEqual(C.state_token(endpoint),first)
            counter=stats['datasets']['/baseball-dev']['endpoints']['data'];counter['Requests']+=1
            self.assertIsNone(C.state_token(endpoint))  # Write may be in flight.
            counter['RequestsGood']+=1
            self.assertNotEqual(C.state_token(endpoint),first)
            server['startDateTime']='2026-09-23T01:00:00Z'
            self.assertNotEqual(C.state_token(endpoint)['started'],first['started'])
            stats['datasets']['/baseball-dev']['endpoints']['data']['operation']='unrecognized'
            self.assertIsNone(C.state_token(endpoint))

    def test_only_unchanged_fenced_snapshots_reuse_and_corruption_falls_back(self):
        with tempfile.TemporaryDirectory() as temporary:
            state=Path(temporary);token={'started':'one','writes':1};fetch=Mock(return_value={'fingerprint':'live','dimensions':[]})
            def atomic(path,value):
                path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value))
            def call(inventory='one',definition='same'):
                return C.snapshot(state,'local',{'fingerprint':inventory},definition,fetch,atomic)
            with patch.object(C,'state_token',side_effect=lambda endpoint:copy.deepcopy(token)):
                self.assertEqual(call(),call());self.assertEqual(fetch.call_count,1)
                token['writes']=2;call();self.assertEqual(fetch.call_count,2)
                token['started']='two';call();self.assertEqual(fetch.call_count,3)
                call(inventory='two');self.assertEqual(fetch.call_count,4)
                call(inventory='two',definition='changed');self.assertEqual(fetch.call_count,5)
                path=state/'serving/live-graph-state.json';record=json.loads(path.read_text());record['live']['fingerprint']='corrupt';atomic(path,record)
                call(inventory='two',definition='changed');self.assertEqual(fetch.call_count,6)
            with patch.object(C,'state_token',return_value=None):call();call()
            self.assertEqual(fetch.call_count,8)
            with patch.object(C,'state_token',side_effect=[{'writes':8},{'writes':9}]):call()
            record=json.loads(path.read_text())
            self.assertNotEqual(record['key']['server'],{'writes':9})


if __name__=='__main__':unittest.main()
