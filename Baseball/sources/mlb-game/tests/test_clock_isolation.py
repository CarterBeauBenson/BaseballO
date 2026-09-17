"""T1 negative controls: no invented clocks and no hidden population loss."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

from pyshacl import validate
from rdflib import Dataset, Graph, Literal, Namespace, RDF, URIRef, XSD

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('clock_admission_test', ROOT / 'sources/mlb-game/pipeline/clock-admission.py')
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)
BASE = Namespace(C.B.BASE)
OBO = Namespace('http://purl.obolibrary.org/obo/')
CCO = Namespace('https://www.commoncoreontologies.org/')
CASES = json.loads((Path(__file__).parent / 'fixtures/clock-conflicts.json').read_text())['cases']


class ClockSelectionTests(unittest.TestCase):
    def test_all_five_exact_source_pairs_are_omitted_without_mutating_records(self):
        self.assertEqual({c['gamePk'] for c in CASES}, {'822753', '823302', '823532', '823631', '823740'})
        for case in CASES:
            with self.subTest(game=case['gamePk']):
                before = copy.deepcopy(case['record'])
                self.assertEqual(C.CONTEXT.clock_pair(case['record']), (None, None))
                self.assertTrue(C.CONTEXT.clock_pair_conflicted(case['record']))
                self.assertEqual(case['record'], before)

    def test_same_instant_and_timezone_offsets_are_compared_as_instants(self):
        record = {'startTime': '2026-09-17T12:00:00-04:00', 'endTime': '2026-09-17T16:00:00Z'}
        self.assertEqual(C.CONTEXT.clock_pair(record), tuple(record.values()))
        record['endTime'] = '2026-09-17T15:59:59Z'
        self.assertEqual(C.CONTEXT.clock_pair(record), (None, None))
        self.assertEqual(C.CONTEXT.clock_pair({'startTime': 'invalid'}), ('invalid', None))

    def test_automatic_awards_survive_but_unproven_precedence_does_not(self):
        for case in CASES:
            if case['play'] is None:
                continue
            play = copy.deepcopy(case['play'])
            doc = {'gamePk': case['gamePk'], 'liveData': {'plays': {'allPlays': [play]}},
                   '_baseballO': {'runnerHistoryReconciliation': {'sourceConsistency': 'consistent'}}}
            result = C.CONTEXT.automatic_count_awards(doc)
            award, = result['automaticAwards']
            self.assertFalse(award['clockOrderSupported'])
            self.assertNotIn('previousPitchIri', award)
            self.assertNotIn('nextPitchIri', award)
            self.assertEqual(play, case['play'])
            # T1 does not excuse a wrong count or an unrelated clock failure.
            for fault in ('count', 'missing-other-clock', 'overlapping-other-clock'):
                changed = copy.deepcopy(doc)
                events = changed['liveData']['plays']['allPlays'][0]['playEvents']
                if fault == 'count':
                    events[0]['count']['strikes'] = 3
                    events[0]['count']['balls'] = 4
                elif fault == 'missing-other-clock':
                    events[1].pop('endTime', None)
                else:
                    if len(events) < 3:
                        continue  # A single undisputed event cannot overlap another.
                    events[1]['endTime'] = events[-1]['endTime']
                self.assertFalse(C.CONTEXT.automatic_count_awards(changed)['automaticAwards'], fault)

    def test_membership_errors_still_block_while_clock_conflicts_are_retained(self):
        raw = (ROOT / 'data/raw/samples/2026-07-18/824088.json').read_bytes()
        doc = json.loads(raw)
        event = next(e for p in doc['liveData']['plays']['allPlays'] for e in p['playEvents']
                     if e.get('isPitch') is True and e['startTime'] < e['endTime'])
        event['startTime'], event['endTime'] = event['endTime'], event['startTime']
        source = C.B.SOURCE.reconcile(json.dumps(doc).encode(), '824088')
        self.assertEqual(source['status'], 'consistent')
        self.assertEqual(source['clockStatus'], 'conflicted')
        self.assertEqual(len(source['clockConflicts']), 1)
        self.assertFalse(source['blockingIssues'])
        doc['liveData']['plays']['allPlays'].pop()
        source = C.B.SOURCE.reconcile(json.dumps(doc).encode(), '824088')
        self.assertEqual(source['status'], 'inconsistent')
        self.assertTrue(source['blockingIssues'])
        self.assertEqual(len(source['clockConflicts']), 1)

    def test_history_withholding_is_scoped_and_correction_guard_is_preserved(self):
        doc = json.loads((ROOT / 'data/raw/samples/2026-07-18/824088.json').read_bytes())
        before = C.CONTEXT.personal_runner_histories(json.dumps(doc).encode())
        affected = next(h for h in before['halves'] if h['status'] == 'reconciled' and h['personalHistories'])
        play = next(p for p in doc['liveData']['plays']['allPlays']
                    if p['about']['inning'] == affected['inning'] and p['about']['halfInning'] == affected['half'])
        play['about']['startTime'], play['about']['endTime'] = play['about']['endTime'], play['about']['startTime']
        after = C.CONTEXT.personal_runner_histories(json.dumps(doc).encode())
        self.assertEqual(after['sourceConsistency'], 'consistent')
        for old, new in zip(before['halves'], after['halves']):
            if old is affected:
                self.assertEqual(new['status'], 'withheld')
                self.assertIn('UNSUPPORTED_PA_CLOCK_PAIR', {i['code'] for i in new['issues']})
            else:
                self.assertEqual(new, old)
        self.assertTrue(after['withheldHistories'])
        with self.assertRaisesRegex(ValueError, 'identity no longer aligns'):
            C.CONTEXT.verify_runner_history_correction(after, before)

    def test_disputed_final_header_cannot_supply_game_end_measurement(self):
        doc = json.loads((ROOT / 'data/raw/samples/2026-07-18/824088.json').read_bytes())
        about = doc['liveData']['plays']['allPlays'][-1]['about']
        about['startTime'], about['endTime'] = about['endTime'], about['startTime']
        source = C.census(json.dumps(doc).encode(), '824088')
        game_end = source['game'] + '/timestamp/end'
        self.assertIn(game_end, {r['timestamp'] for r in source['withheld']})
        self.assertNotIn(game_end, {r['timestamp'] for r in source['expected']})
        self.assertIn(source['game'] + '/timestamp/start', {r['timestamp'] for r in source['expected']})


class ClockGraphTests(unittest.TestCase):
    def setUp(self):
        self.process = C.B.BASE + 'data/game/1/pitch/one'
        self.rows = [dict(timestamp=self.process + '/timestamp/' + side,
                         instant=self.process + '/temporal-instant/' + side,
                         process=self.process, side=side, value='2026-09-17T16:00:00Z') for side in ('start', 'end')]
        self.source = dict(expected=[], withheld=self.rows, processes=[dict(process=self.process, kind='PitchAct')], awards=[])
        self.graph = Graph()
        process, interval = URIRef(self.process), URIRef(self.process + '/temporal-interval')
        self.graph.add((process, RDF.type, BASE.PitchAct))
        self.graph.add((process, OBO.BFO_0000199, interval))
        self.graph.add((interval, RDF.type, OBO.BFO_0000038))
        for row in self.rows:
            instant = URIRef(row['instant'])
            self.graph.add((instant, RDF.type, BASE.BaseballEventTemporalInstant))
            self.graph.add((interval, OBO.BFO_0000222 if row['side'] == 'start' else OBO.BFO_0000224, instant))

    def conforms(self, graph=None):
        return validate(graph if graph is not None else self.graph,
                        shacl_graph=Graph().parse(data=C.shape_text(self.source), format='turtle'),
                        inference='none', advanced=True)[0]

    def add_measurement(self, row, resource=None, value=None):
        timestamp = URIRef(resource or row['timestamp'])
        self.graph.add((timestamp, RDF.type, BASE.BaseballTimestampICE))
        self.graph.add((timestamp, CCO.ont00001916, URIRef(row['instant'])))
        self.graph.add((timestamp, CCO.ont00001808, URIRef(row['process'])))
        self.graph.add((timestamp, CCO.ont00001767, Literal(value or row['value'], datatype=XSD.dateTime)))

    def test_neither_measurement_is_required_but_event_structure_is(self):
        self.assertTrue(self.conforms())
        for triple in list(self.graph):
            changed = Graph()
            for other in self.graph:
                if other != triple:
                    changed.add(other)
            self.assertFalse(self.conforms(changed), triple)

    def test_either_original_or_renamed_measurement_is_rejected(self):
        for row in self.rows:
            for resource in (row['timestamp'], C.B.BASE + 'data/fake-repaired-clock'):
                self.setUp()
                self.add_measurement(row, resource)
                self.assertFalse(self.conforms())

    def test_consistent_pair_requires_both_exact_measurements(self):
        self.source.update(expected=self.rows, withheld=[])
        self.assertFalse(self.conforms())
        self.add_measurement(self.rows[0])
        self.assertFalse(self.conforms())
        self.add_measurement(self.rows[1])
        self.assertTrue(self.conforms())
        self.graph.set((URIRef(self.rows[0]['timestamp']), CCO.ont00001767, Literal('2026-09-17T16:00:01Z', datatype=XSD.dateTime)))
        self.assertFalse(self.conforms())


class ClockIndexTests(unittest.TestCase):
    def test_missing_terminal_clock_does_not_reclassify_an_earlier_pitch(self):
        data = Dataset()
        graph = data.graph(URIRef('urn:baseball:query-index:source-graph'))
        graph.parse(data='''
            @prefix b: <https://baseballontology.org/> .
            @prefix d: <https://baseballontology.org/data/> .
            @prefix o: <http://purl.obolibrary.org/obo/> .
            @prefix c: <https://www.commoncoreontologies.org/> .
            @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
            d:pa a b:PlateAppearance ; o:BFO_0000132 d:half .
            d:half o:BFO_0000132 d:inning . d:inning o:BFO_0000132 <urn:baseball:query-index:game> .
            d:person a c:ont00001262 .
            d:result a b:HitByPitchProcess ; o:BFO_0000132 d:pa .
            d:one a b:PitchAct ; o:BFO_0000132 d:pa ; o:BFO_0000057 d:person ; o:BFO_0000063 d:motion1 ; o:BFO_0000199 d:i1 .
            d:two a b:PitchAct ; o:BFO_0000132 d:pa ; o:BFO_0000057 d:person ; o:BFO_0000063 d:motion2 ; o:BFO_0000199 d:i2 .
            d:motion1 a b:PitchBallMotionProcess . d:motion2 a b:PitchBallMotionProcess .
            d:r1 a b:BaseballEventRecord ; c:ont00001808 d:one, d:ball .
            d:r2 a b:BaseballEventRecord ; c:ont00001808 d:two .
            d:ball a b:BallProcess .
            d:i1 o:BFO_0000224 d:end1 . d:i2 o:BFO_0000224 d:end2 .
            d:t1 a b:BaseballTimestampICE ; c:ont00001916 d:end1 ; c:ont00001767 "2026-09-17T16:00:00Z"^^xsd:dateTime .
        ''', format='turtle')
        query = (ROOT / 'sparql/query-index/components/50-pitch-calls.rq').read_text()
        idx = Namespace('https://w3id.org/baseball/query-index/')
        result = data.query(query).graph
        self.assertFalse(list(result.subjects(idx.callType, idx.HitByPitch)))
        self.assertEqual(list(result.subjects(idx.callType, idx.Ball)), [BASE['data/one/call-fact']])
        graph.add((BASE['data/t2'], RDF.type, BASE.BaseballTimestampICE))
        graph.add((BASE['data/t2'], CCO.ont00001916, BASE['data/end2']))
        graph.add((BASE['data/t2'], CCO.ont00001767, Literal('2026-09-17T16:01:00Z', datatype=XSD.dateTime)))
        result = data.query(query).graph
        self.assertEqual(list(result.subjects(idx.callType, idx.HitByPitch)), [BASE['data/two/call-fact']])


if __name__ == '__main__':
    unittest.main()
