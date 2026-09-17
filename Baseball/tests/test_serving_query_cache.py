"""Focused cache isolation and materializer checkpoint regressions."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from copy import deepcopy
import gzip
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import Mock

from test_serving_materializer import MODULE as M

C=M._query_cache
G=M._build_guard
GRAPH='https://w3id.org/baseball/graph/game/1'
INDEX='https://w3id.org/baseball/graph/query-index/game/1'
QUERY=f'SELECT ?s ?p ?o WHERE {{ GRAPH <{GRAPH}> {{ ?s ?p ?o }} }}'
PROMOTION=dict(authoritativeGraph=GRAPH,queryIndexGraph=INDEX,
    promotionManifestSha256='1'*64,authoritativeRdfSha256='2'*64,queryIndexRdfSha256='3'*64)
PAYLOAD={'head':{'vars':['s','o','optional']},'results':{'bindings':[
    {'s':{'type':'uri','value':'urn:player:1'},'o':{'type':'literal','value':'José','xml:lang':'es'}},
    {'o':{'type':'literal','value':'01','datatype':'http://www.w3.org/2001/XMLSchema#integer'}},
    {'o':{'type':'literal','value':'01','datatype':'http://www.w3.org/2001/XMLSchema#integer'}}]}}


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.cache=C.ServingQueryCache(Path(self.temporary.name)/'cache.sqlite')
        self.fetch=Mock(side_effect=lambda:deepcopy(PAYLOAD))

    def query(self,**changes):
        args=dict(endpoint='offline',query=QUERY,slot='test',promotion=PROMOTION,fetch=self.fetch)
        args.update(changes)
        return self.cache.query(**args)

    def test_warm_result_preserves_terms_duplicates_unbound_and_order_without_aliases(self):
        cold=self.query()
        cold['results']['bindings'].clear()
        self.assertEqual(self.query(),PAYLOAD)
        self.assertEqual(self.query(),PAYLOAD)
        self.assertEqual(self.fetch.call_count,1)
        self.assertEqual(self.cache.stats,dict(hits=2,misses=1,bypassed=0,discarded=0))

    def test_query_endpoint_and_read_graph_changes_invalidate(self):
        self.query()
        for changes in [dict(endpoint='different'),dict(query=QUERY+'\n'),
                        *[dict(promotion={**PROMOTION,key:'a'*64}) for key in
                          ('authoritativeRdfSha256',)]]:
            with self.subTest(changes=changes):
                count=self.fetch.call_count
                self.query(**changes);self.query(**changes)
                self.assertEqual(self.fetch.call_count,count+1)
        with closing(sqlite3.connect(self.cache.path)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM scoped_answer').fetchone()[0],1)

    def test_new_promotion_and_unread_index_do_not_rerun_authoritative_query(self):
        self.query()
        self.assertEqual(self.query(promotion={**PROMOTION,
            'promotionManifestSha256':'a'*64,'queryIndexRdfSha256':'b'*64}),PAYLOAD)
        self.assertEqual(self.fetch.call_count,1)

    def test_index_only_query_ignores_authoritative_change_but_not_index_change(self):
        query=QUERY.replace(GRAPH,INDEX)
        self.query(query=query)
        self.query(query=query,promotion={**PROMOTION,'authoritativeRdfSha256':'a'*64})
        self.assertEqual(self.fetch.call_count,1)
        self.query(query=query,promotion={**PROMOTION,'queryIndexRdfSha256':'b'*64})
        self.assertEqual(self.fetch.call_count,2)

    def test_queries_reading_both_graphs_depend_on_both_versions(self):
        queries=[f'SELECT * FROM NAMED <{GRAPH}> FROM NAMED <{INDEX}> WHERE {{ GRAPH ?g {{ ?s ?p ?o }} }}',
                 f'SELECT * WHERE {{ GRAPH <{GRAPH}> {{ ?s ?p ?o }} OPTIONAL {{ GRAPH <{INDEX}> {{ ?s ?x ?y }} }} }}']
        for slot,query in enumerate(queries):
            with self.subTest(query=query):
                before=self.fetch.call_count
                self.query(query=query,slot=str(slot))
                self.query(query=query,slot=str(slot),promotion={**PROMOTION,'queryIndexRdfSha256':'a'*64})
                self.query(query=query,slot=str(slot),promotion={**PROMOTION,'authoritativeRdfSha256':'b'*64})
                self.assertEqual(self.fetch.call_count,before+3)

    def test_changing_one_game_does_not_invalidate_another(self):
        other={**PROMOTION,'authoritativeGraph':GRAPH+'0','queryIndexGraph':INDEX+'0'}
        self.query();self.query(promotion=other,query=QUERY.replace(GRAPH,GRAPH+'0'))
        self.query(promotion={**PROMOTION,'authoritativeRdfSha256':'a'*64})
        self.query(promotion=other,query=QUERY.replace(GRAPH,GRAPH+'0'))
        self.assertEqual(self.fetch.call_count,3)

    def test_unbounded_external_and_volatile_queries_bypass(self):
        bodies=['?s ?p ?o',f'GRAPH <{GRAPH}> {{ ?s ?p ?o }} ?x ?y ?z',
                'GRAPH ?g { ?s ?p ?o }','GRAPH <urn:other> { ?s ?p ?o }',
                'SERVICE <http://example.com/sparql> { ?s ?p ?o }',
                *[f'GRAPH <{GRAPH}> {{ ?s ?p ?o }} BIND({fn} AS ?x)' for fn in
                  ('NOW()','RAND()','UUID()','STRUUID()','BNODE()','<urn:custom>(?s)')]]
        queries=['SELECT * WHERE { '+body+' }' for body in bodies]
        queries += [f'SELECT * FROM <{GRAPH}> WHERE {{ ?s ?p ?o }}',
                    f'SELECT * FROM NAMED <urn:other> WHERE {{ GRAPH ?g {{ ?s ?p ?o }} }}',
                    'ASK {}','not sparql']
        for query in queries:
            with self.subTest(query=query):
                count=self.fetch.call_count
                self.query(query=query);self.query(query=query)
                self.assertEqual(self.fetch.call_count,count+2)
        self.assertEqual(self.cache.stats['hits'],0)

    def test_explicit_named_dataset_and_nested_graphs_are_scoped(self):
        query=f'SELECT * FROM NAMED <{GRAPH}> FROM NAMED <{INDEX}> WHERE {{ GRAPH ?g {{ ?s ?p ?o }} }}'
        self.query(query=query);self.query(query=query)
        self.assertEqual(self.fetch.call_count,1)

    def test_absent_promotion_hash_bypasses(self):
        promotion={k:v for k,v in PROMOTION.items() if k!='authoritativeRdfSha256'}
        self.query(promotion=promotion);self.query(promotion=promotion)
        self.assertEqual(self.cache.stats['bypassed'],2)

    def test_corrupt_payload_checksum_and_invalid_result_refetch(self):
        self.query()
        for payload,digest in [(b'corrupt','a'*64),(gzip.compress(b'{}'),'a'*64),
                              (gzip.compress(b'{}'),C.sha(b'{}'))]:
            with self.subTest(payload=payload):
                with closing(sqlite3.connect(self.cache.path)) as db, db:
                    db.execute('UPDATE scoped_answer SET payload=?,payload_sha256=?',(payload,digest))
                self.assertEqual(self.query(),PAYLOAD)
        self.assertEqual(self.cache.stats['discarded'],3)
        self.assertEqual(self.fetch.call_count,4)

    def test_failed_fetch_never_enters_cache(self):
        for fetch in [Mock(side_effect=RuntimeError('offline')),Mock(return_value={'error':'failed'})]:
            with self.assertRaises((RuntimeError,ValueError)):self.query(fetch=fetch)
        self.query();self.query()
        self.assertEqual(self.fetch.call_count,1)

    def test_parallel_distinct_slots_preserve_answers(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            values=list(pool.map(lambda slot:self.query(slot=str(slot)),range(8)))
            warm=list(pool.map(lambda slot:self.query(slot=str(slot)),range(8)))
        self.assertEqual(values,[PAYLOAD]*8)
        self.assertEqual(warm,values)
        self.assertEqual(self.cache.stats['hits'],8)

    def test_real_materializer_queries_remain_scoped(self):
        catalog=json.loads(M.ADVANCED_CATALOG.read_text(encoding='utf-8'))
        reducers=json.loads(M.ADVANCED_REDUCERS.read_text(encoding='utf-8'))
        dsq=json.loads(M.DSQ_MATERIALIZATIONS.read_text(encoding='utf-8'))
        entries=M.load_dsq_entries(dsq,catalog,reducers)
        queries={e['id']:M.bounded_dsq_query((M.ROOT/e['executionPath']).read_text(encoding='utf-8'),GRAPH,e['executionLayer'])
                 for e in entries if e['kind']=='canned'}
        queries.update({e['id']:M.bounded_query((M.ROOT/e['path']).read_text(encoding='utf-8'),GRAPH) for e in catalog['queries']})
        queries.update({name:M.bounded_query(path.read_text(encoding='utf-8'),GRAPH) for name,path in M.EXPLORE_GRAIN_QUERIES.items()})
        queries['metric-suite']=M._metric_suite.evidence_query([GRAPH])
        for slot,query in queries.items():
            normalized=query.replace('<'+GRAPH+'>','<urn:baseballo:cache:authoritative>').replace('<'+INDEX+'>','<urn:baseballo:cache:index>')
            with self.subTest(slot=slot):self.assertTrue(C.scoped_query(normalized))


class GuardTests(unittest.TestCase):
    def test_progress_and_input_drift_are_positive_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);source=root/'query.rq';source.write_text('first')
            metric=Mock(return_value='1'*64)
            guard=G.BuildInputGuard(paths={'query':source},metric_fingerprint=metric,
                progress_path=root/'progress.json',build_id='fixture')
            guard.check(completed=10,total=100,phase='source-queries')
            self.assertEqual(json.loads(guard.path.read_text())['completedGames'],10)
            source.write_text('second')
            with self.assertRaises(G.InputsChanged):guard.check(completed=20,total=100,phase='source-queries')
            guard.fail(RuntimeError('wrapper'))
            record=json.loads(guard.path.read_text())
            self.assertEqual(record['status'],'invalidated')
            self.assertEqual(record['changedInputs'],['query'])

    def test_deleted_input_and_metric_changes_invalidate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);source=root/'query.rq';source.write_text('first')
            metric=Mock(return_value='1'*64)
            guard=G.BuildInputGuard(paths={'query':source},metric_fingerprint=metric,
                progress_path=root/'progress.json',build_id='fixture')
            source.unlink();metric.return_value='2'*64
            with self.assertRaises(G.InputsChanged):guard.check(completed=0,total=1,phase='source-queries')
            self.assertEqual(guard.record['changedInputs'],['query','metric-suite'])


if __name__=='__main__':unittest.main()
