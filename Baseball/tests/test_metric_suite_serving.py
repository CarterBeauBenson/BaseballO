"""Focused RDF-to-kernel-to-SQL checks; no live acquisition or corpus build."""
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from rdflib import Dataset, Namespace, RDF

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('metric_suite', ROOT/'serving/metric_suite.py')
M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
G1 = 'https://w3id.org/baseball/graph/game/101'
G2 = 'https://w3id.org/baseball/graph/game/102'
PREFIX = '''@prefix base: <https://baseballontology.org/> .
@prefix cco: <https://www.commoncoreontologies.org/> .
@prefix obo: <http://purl.obolibrary.org/obo/> .
@prefix ex: <urn:test:> .
'''


def fixture(graph=G1, decisions=('reversed', 'affirmed', None)):
    triples = '''ex:game a base:BaseballGame .
ex:inning obo:BFO_0000132 ex:game . ex:half obo:BFO_0000132 ex:inning .
ex:pa a base:PlateAppearance ; obo:BFO_0000132 ex:half .
ex:play a base:BattedBallPlayProcess ; obo:BFO_0000132 ex:pa .
ex:run a base:RunProcess ; obo:BFO_0000132 ex:pa .
ex:act obo:BFO_0000132 ex:pa ; obo:BFO_0000055 ex:role .
ex:role a base:BatterRole ; obo:BFO_0000197 ex:player .
'''
    for i, decision in enumerate(decisions):
        # Actual mapping does not assert review-act-to-PA parthood. Scope is
        # proved through the review record and its final result judgment.
        triples += f'''ex:review{i} a base:BaseballReplayReviewAct .
ex:record{i} a base:BaseballReplayReviewEventRecord ; cco:ont00001808 ex:review{i}, ex:resultJudgment{i} .
ex:resultJudgment{i} obo:BFO_0000132 ex:result{i} .
ex:result{i} a base:BaseballInstitutionalProcess ; obo:BFO_0000132 ex:pa .
'''
        if decision is None:
            continue
        classes = ('base:OverturningBaseballReplayReviewDispositionICE' if decision == 'reversed' else
                   'base:AffirmingBaseballReplayReviewDispositionICE' if decision == 'affirmed' else
                   'base:OverturningBaseballReplayReviewDispositionICE, base:AffirmingBaseballReplayReviewDispositionICE')
        triples += f'''ex:record{i} a base:BaseballReplayReviewEventRecord ; cco:ont00001808
            ex:review{i}, ex:judgment{i}, ex:original{i}, ex:operative{i}, ex:disposition{i} .
ex:judgment{i} a base:ReviewedOnFieldUmpireJudgmentAct ; cco:ont00001986 ex:original{i} ; obo:BFO_0000063 ex:review{i} .
ex:review{i} cco:ont00001921 ex:original{i} ; cco:ont00001986 ex:operative{i} .
ex:original{i} a base:ReviewedOnFieldBaseballDecisionICE .
ex:operative{i} a base:BaseballReplayDecisionICE .
ex:disposition{i} a base:BaseballReplayReviewDispositionICE, {classes} ;
  cco:ont00001816 ex:review{i} ; cco:ont00001808 ex:original{i}, ex:operative{i} .
'''
    # Distinct fixture IRIs across games, like the persistent event graph contract.
    triples = triples.replace('ex:', 'ex'+graph.rsplit('/',1)[-1]+':')
    prefix = PREFIX.replace('@prefix ex:', '@prefix ex'+graph.rsplit('/',1)[-1]+':').replace('<urn:test:>', '<urn:test:'+graph.rsplit('/',1)[-1]+':>')
    dataset = Dataset()
    dataset.graph(graph).parse(data=prefix+triples, format='turtle')
    return dataset


def bindings(dataset, graphs):
    return json.loads(dataset.query(M.evidence_query(graphs)).serialize(format='json'))['results']['bindings']


def pitch_review_fixture():
    """Asserted M2 shape: no inferred parent types or final-result record link.

    Two distinct pitches in one PA accompany an older play-level review.
    No challenger identity is used as an affected-player assertion.
    """
    dataset = fixture(decisions=('reversed',))
    for i, kind in enumerate(('Ball', 'Strike')):
        dataset.graph(G1).parse(data=PREFIX.replace('<urn:test:>', '<urn:test:101:>')+f'''
ex:pitchReview{i} a base:BaseballReplayReviewAct, base:{kind}AffirmingBaseballReplayReviewAct ;
  obo:BFO_0000132 ex:pitchResult{i} ; cco:ont00001921 ex:pitchOriginal{i} ;
  cco:ont00001986 ex:pitchOperative{i}, ex:pitchDisposition{i} .
ex:pitchResult{i} a base:{kind}Process ; obo:BFO_0000132 ex:pa .
ex:pitchRecord{i} a base:BaseballReplayReviewEventRecord ; cco:ont00001808
  ex:pitchReview{i}, ex:pitchJudgment{i}, ex:pitchOriginal{i}, ex:pitchOperative{i}, ex:pitchDisposition{i}, ex:pitch{i} .
ex:pitchJudgment{i} a base:ReviewedOnFieldUmpireJudgmentAct ;
  cco:ont00001986 ex:pitchOriginal{i} ; obo:BFO_0000063 ex:pitchReview{i} .
ex:pitchOriginal{i} a base:ReviewedOnFieldBaseballDecisionICE .
ex:pitchOperative{i} a base:BaseballReplayDecisionICE .
ex:pitchDisposition{i} a base:AffirmingBaseballReplayReviewDispositionICE ;
  cco:ont00001816 ex:pitchReview{i} ; cco:ont00001808 ex:pitchOriginal{i}, ex:pitchOperative{i} .
''', format='turtle')
    return dataset


def database():
    connection = sqlite3.connect(':memory:')
    connection.execute('PRAGMA foreign_keys=ON')
    connection.executescript((ROOT/'serving/schema.sql').read_text())
    M.initialize_sql(connection)
    for graph, date in [(G1,'2026-08-01'), (G2,'2026-08-02')]:
        connection.execute('INSERT INTO game_dimension VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
                           (graph,'urn:test:game:'+date,graph.rsplit('/',1)[-1],date,date+'T12:00:00Z',
                            2026,'regular_season',None,None,None,None,None,None))
    return connection


class MetricServing(unittest.TestCase):
    def test_cached_rdf_products_match_direct_sql_and_do_not_recalculate(self):
        cache_spec = importlib.util.spec_from_file_location('metric_cache', ROOT/'scripts/pipeline/serving_metric_cache.py')
        cache_module = importlib.util.module_from_spec(cache_spec); cache_spec.loader.exec_module(cache_module)
        evidence = bindings(pitch_review_fixture(), [G1])
        scope = dict(startDate='2026-08-01',endDate='2026-08-01',gameSet='regular_season')
        with tempfile.TemporaryDirectory() as temporary, database() as conn:
            M.materialize_game(conn, G1, evidence)
            expected = M.query_sql(conn, {'view':'dashboard'}, scope)
            cache = cache_module.MetricProductCache(Path(temporary)/'metric.sqlite', M.calculation_fingerprint())
            M.materialize_game(conn, G1, evidence, product_cache=cache)
            with patch.object(M, 'game_products', side_effect=AssertionError('must reuse')):
                # Normalization removes exact duplicates and input order changes.
                M.materialize_game(conn, G1, list(reversed(evidence))+evidence, product_cache=cache)
            self.assertEqual(M.query_sql(conn, {'view':'dashboard'}, scope), expected)
            self.assertEqual(cache.stats['hits'], 1)
            self.assertEqual(cache.stats['misses'], 1)

    def test_asserted_pitch_reviews_reach_sql_without_inference_or_duplicate_counts(self):
        data = pitch_review_fixture()
        original_bindings = bindings(data, [G1])
        rows = M.normalize_bindings(original_bindings, [G1])
        result = M.live_result('adjudication-volatility', rows, graph_count=1)
        self.assertEqual(result['coverage']['resolvedReviews'], 3)
        self.assertEqual(result['coverage']['unresolvedReviews'], 0)
        self.assertEqual(result['value'], M.exact(M.Fraction(1, 3)))
        self.assertFalse(result['coverage']['populationComplete'])
        self.assertTrue(all('player' not in r for r in rows if r['kind'] == 'review'))
        with database() as conn:
            M.materialize_game(conn, G1, original_bindings + original_bindings)
            actual = M.query_sql(conn, {'metricId': 'adjudication-volatility'},
                {'gameSet': 'regular_season', 'startDate': '2026-08-01', 'endDate': '2026-08-01'})
            self.assertEqual(actual['metric'], result)
        # Optional inferred types and a legacy duplicate scope path must not
        # turn one canonical review into two observations.
        base = Namespace('https://baseballontology.org/')
        ex = Namespace('urn:test:101:')
        cco = Namespace('https://www.commoncoreontologies.org/')
        g = data.graph(G1)
        for i in range(2):
            g.add((ex[f'pitchResult{i}'], RDF.type, base.BaseballInstitutionalProcess))
            g.add((ex[f'pitchDisposition{i}'], RDF.type, base.BaseballReplayReviewDispositionICE))
        g.add((ex.pitchRecord0, cco.ont00001808, ex.resultJudgment0))
        enriched = M.normalize_bindings(bindings(data, [G1]), [G1])
        self.assertEqual(M.live_result('adjudication-volatility', enriched, graph_count=1), result)

    def test_pitch_review_needs_game_containment_and_supported_disposition(self):
        data = pitch_review_fixture()
        ex = Namespace('urn:test:101:')
        bfo = Namespace('http://purl.obolibrary.org/obo/')
        base = Namespace('https://baseballontology.org/')
        g = data.graph(G1)
        g.remove((ex.pitchResult0, bfo.BFO_0000132, ex.pa))
        g.remove((ex.pitchDisposition1, RDF.type, base.AffirmingBaseballReplayReviewDispositionICE))
        rows = M.normalize_bindings(bindings(data, [G1]), [G1])
        self.assertNotIn(str(ex.pitchReview0), {r['entity'] for r in rows})
        result = M.live_result('adjudication-volatility', rows, graph_count=1)
        self.assertEqual(result['coverage']['resolvedReviews'], 1)
        self.assertEqual(result['coverage']['unresolvedReviews'], 1)
        self.assertEqual(result['value'], M.exact(M.Fraction(1)))

    def test_existing_term_query_preserves_entities_and_resolved_review_population(self):
        rows=M.normalize_bindings(bindings(fixture(),[G1]),[G1])
        self.assertEqual({r['kind'] for r in rows}, {'plate_appearance','batted_play','run','player_game','review'})
        result=M.live_result('adjudication-volatility',rows,graph_count=1)
        self.assertEqual(result['value'],M.exact(M.Fraction(1,2)))
        self.assertEqual(result['coverage']['unresolvedReviews'],1)
        self.assertFalse(result['coverage']['populationComplete'])
        self.assertIn('urn:test:101:operative0', result['evidence'])
        for entry in M.catalog()['metrics']:
            if entry['requires']:
                result=M.live_result(entry['id'],rows,graph_count=1)
                self.assertEqual(result['status'],'unavailable')
                self.assertEqual(set(result['gaps']),set(entry['requires']))

    def test_query_does_not_leak_other_graphs_or_allow_injection(self):
        data=fixture()
        data.graph(G2).parse(data=PREFIX+'ex:other a base:BaseballGame . ex:pa a base:PlateAppearance ; obo:BFO_0000132 ex:x . ex:x obo:BFO_0000132 ex:y . ex:y obo:BFO_0000132 ex:other .',format='turtle')
        self.assertTrue(all(b['graph']['value']==G1 for b in bindings(data,[G1])))
        self.assertEqual(bindings(data,[]),[])
        for graph in ['https://attacker.test/1',G1+'> } UNION { ?s ?p ?o } #']:
            with self.assertRaises(M.EvidenceError): M.evidence_query([graph])
        with self.assertRaises(M.EvidenceError): M.normalize_bindings(bindings(data,[G1]),[G2])

    def test_review_conflicts_do_not_become_zero_or_one(self):
        rows=M.normalize_bindings(bindings(fixture(decisions=('conflict',)),[G1]),[G1])
        result=M.live_result('adjudication-volatility',rows,graph_count=1)
        self.assertEqual(result['gaps'],['CONFLICTING_REVIEW_DISPOSITION'])
        rows=M.normalize_bindings(bindings(fixture(decisions=(None,)),[G1]),[G1])
        self.assertEqual(M.live_result('adjudication-volatility',rows,graph_count=1)['gaps'],['EMPTY_DENOMINATOR'])

    def test_sql_materialization_is_idempotent_and_pools_counts(self):
        with database() as conn:
            b1=bindings(fixture(decisions=('reversed',)),[G1])
            b2=bindings(fixture(G2,decisions=('affirmed','affirmed','affirmed')),[G2])
            M.materialize_game(conn,G1,b1+b1)
            M.materialize_game(conn,G1,b1)
            M.materialize_game(conn,G2,b2)
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM metric_suite_result').fetchone()[0],40)
            scope={'gameSet':'regular_season','startDate':'2026-08-01','endDate':'2026-08-02'}
            actual=M.query_sql(conn,{'metricId':'adjudication-volatility'},scope)
            direct=M.live_result('adjudication-volatility',M.normalize_bindings(b1+b2,[G1,G2]),graph_count=2)
            self.assertEqual(actual['metric'],direct)
            self.assertEqual(actual['metric']['value'],M.exact(M.Fraction(1,4)))
            self.assertEqual(conn.execute('PRAGMA foreign_key_check').fetchall(),[])
            self.assertEqual(conn.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertEqual(M.query_sql(conn,{'metricId':'tfs'},scope)['metric']['status'],'unavailable')

    def test_stale_corrupt_and_incomplete_sql_fail_closed(self):
        scope={'gameSet':'regular_season','startDate':'2026-08-01','endDate':'2026-08-01'}
        with database() as conn:
            with self.assertRaises(M.EvidenceError): M.query_sql(conn,{'metricId':'tfs'},scope)
            M.materialize_game(conn,G1,bindings(fixture(),[G1]))
            with patch.object(M,'fingerprint',return_value='different'):
                with self.assertRaises(M.EvidenceError): M.query_sql(conn,{'metricId':'tfs'},scope)
            conn.execute("UPDATE metric_suite_result SET numerator='5' WHERE metric_id='adjudication-volatility'")
            with self.assertRaises(M.EvidenceError): M.read_results(conn,G1,'adjudication-volatility')
            conn.execute("UPDATE metric_suite_evidence SET binding_sha256='bad' WHERE rowid=(SELECT MIN(rowid) FROM metric_suite_evidence)")
            with self.assertRaises(M.EvidenceError): M.query_sql(conn,{'metricId':'tfs'},scope)

    def test_empty_game_count_survives_fraction_reduction_and_sql(self):
        rows=[dict(key='player',game=str(i),plateAppearances=1,positiveEpisodes=0 if i<4 else 1)
              for i in range(8)]
        rows.append(dict(key='player',game='runner-only',plateAppearances=0,positiveEpisodes=0))
        result=M.calculate('empty-game-rate',rows)
        self.assertEqual(result['value'],M.exact(M.Fraction(1,2)))
        self.assertEqual(result['components'],dict(emptyGames=4,eligibleGames=8))
        with database() as conn:
            M.store_result(conn,G1,'empty-game-rate','fixture',result)
            self.assertEqual(M.read_results(conn,G1,'empty-game-rate'),[result])

    def test_all_metric_values_round_trip_without_float_loss(self):
        with database() as conn:
            # Exercise the generic SQL contract on the actual calculated output
            # type of every kernel, including irrational entropy and percentiles.
            defaults=dict(key='scope',participant='runner',start=1,end=2,terminal='safe',creditProgress=True,
                creditOut=False,outsBefore=0,attributedOuts=0,cohort='season',scoreN=1,scoreD=3,
                recoveryN=1,recoveryD=2,depth=1,progress36=12,pa='pa',batterProgress36=0,otherProgress36=12,
                runnerOnBase=True,existingRunnerOuts=1,existingDestruction36=12,erosion36=4,game='game',
                eligible=True,plateAppearances=1,positiveEpisodes=0,episode='episode',play='play',empty=True,score36=-9,channel='batter_self',
                act='act',next=None,agent='player',changesState=True,supporter='player',review='review',
                resolved=True,reversed=True,outcome='outcome',reviewed=True,roleType='https://baseballontology.org/BatterRole')
            for entry in M.catalog()['metrics']:
                with self.subTest(metric=entry['id']):
                    if entry['id'] in {'paq-2','paq-a','paq-2.1','recovery-quality'}:
                        result=M.percentiles([dict(key='a',cohort='season-state',score=M.Fraction(1,3),recovery=50,depth=1),
                                              dict(key='b',cohort='season-state',score=M.Fraction(2,3),recovery=50,depth=1)],
                                             metric_id=entry['id'],complete_population=True)['a']
                    else:
                        result=M.calculate(entry['id'],[{c:defaults[c] for c in entry['inputColumns']}])
                    self.assertEqual(result['status'],'available')
                    M.store_result(conn,G1,entry['id'],'fixture',result)
                    self.assertEqual(M.read_results(conn,G1,entry['id']),[result])
            big=M.available(M.Fraction(10**70+1,10**71+3))
            M.store_result(conn,G2,'tfs','exact',big)
            self.assertEqual(M.read_results(conn,G2,'tfs'),[big])

    def test_gap_register_is_complete_without_duplicate_ids(self):
        ids=[g['id'] for g in M.gaps()['gaps']]
        self.assertEqual(len(ids),len(set(ids)))
        for metric in M.catalog()['metrics']:
            self.assertTrue(set(metric['requires'])<=set(ids))
        self.assertTrue(all(g['status']=='open' for g in M.gaps()['gaps']))

    def test_serving_route_requires_the_new_evidence_contract(self):
        spec=importlib.util.spec_from_file_location('adapter', ROOT/'scripts/pipeline/query-serving-layer.py')
        adapter=importlib.util.module_from_spec(spec); spec.loader.exec_module(adapter)
        contract=json.loads((ROOT/'serving/contract.json').read_text())
        for entry in M.catalog()['metrics']:
            adapter.require_materialized_route_admission({'route':'metric-suite','metricId':entry['id']},contract)
        with self.assertRaises(ValueError):
            adapter.require_materialized_route_admission({'route':'metric-suite','metricId':'made-up'},contract)
        del contract['metricSuite']
        with self.assertRaises(ValueError):
            adapter.require_materialized_route_admission({'route':'metric-suite','metricId':'tfs'},contract)


if __name__=='__main__': unittest.main()
