"""Accepted M2 subject attribution survives canonical extraction and SQL."""
import copy
import json
import unittest

from rdflib import Namespace, RDF

from test_metric_suite_serving import M, G1, PREFIX, bindings, database, pitch_review_fixture

EX=Namespace('urn:test:101:')
BASE=Namespace('https://baseballontology.org/')
BFO=Namespace('http://purl.obolibrary.org/obo/')
CCO=Namespace('https://www.commoncoreontologies.org/')


def supported_fixture():
    data=pitch_review_fixture()
    g=data.graph(G1)
    g.add((EX.act,RDF.type,BASE.BatterAct))
    g.add((EX.act,BFO.BFO_0000057,EX.player))
    for i in range(2):
        g.parse(data=PREFIX.replace('<urn:test:>','<urn:test:101:>')+f'''
ex:pitch{i} a base:PitchAct ; obo:BFO_0000132 ex:pa .
ex:motion{i} a base:PitchBallMotionProcess ; obo:BFO_0000132 ex:pa ; obo:BFO_0000062 ex:pitch{i} .
ex:pitchOriginal{i} cco:ont00001808 ex:motion{i} .
ex:pitchOperative{i} cco:ont00001808 ex:motion{i} .
''',format='turtle')
    return data


def evidence(data):
    return M.review_player_evidence(M.normalize_bindings(bindings(data,[G1]),[G1]))


class ReviewPlayerEvidence(unittest.TestCase):
    def test_exact_reviewed_pitch_and_actual_batting_role_supply_subject(self):
        rows=evidence(supported_fixture())
        self.assertEqual(len(rows),3)
        supported=[r for r in rows if r['attributionStatus']=='supported']
        self.assertEqual(len(supported),2)
        self.assertEqual({r['affectedPlayer'] for r in supported},{str(EX.player)})
        self.assertEqual({r['reviewPitch'] for r in supported},{str(EX.pitch0),str(EX.pitch1)})
        self.assertTrue(all('mechanism' not in r for r in rows))

    def test_missing_subject_link_does_not_fall_back_to_pa_or_challenger(self):
        for triple in ((EX.pitchOriginal0,CCO.ont00001808,EX.motion0),
                       (EX.pitchOperative0,CCO.ont00001808,EX.motion0),
                       (EX.motion0,BFO.BFO_0000062,EX.pitch0),
                       (EX.pitchRecord0,CCO.ont00001808,EX.pitch0),
                       (EX.act,BFO.BFO_0000057,EX.player)):
            data=supported_fixture();g=data.graph(G1);g.remove(triple)
            g.add((EX.pitchReview0,CCO.ont00001833,EX.challenger))
            row=next(r for r in evidence(data) if r['review']==str(EX.pitchReview0))
            self.assertIsNone(row['affectedPlayer'])
            self.assertEqual(row['gaps'],['AFFECTED_PLAYER_EVIDENCE'])

    def test_multiple_batting_stints_never_choose_the_final_batter(self):
        data=supported_fixture();g=data.graph(G1)
        g.add((EX.otherAct,RDF.type,BASE.BatterAct));g.add((EX.otherAct,BFO.BFO_0000132,EX.pa))
        self.assertTrue(all(r['affectedPlayer'] is None for r in evidence(data)))

    def test_conflicting_role_bearers_stay_unassigned(self):
        data=supported_fixture();data.graph(G1).add((EX.role,BFO.BFO_0000197,EX.otherPlayer))
        self.assertTrue(all(r['affectedPlayer'] is None for r in evidence(data)))

    def test_distinct_subjects_for_same_review_cannot_be_collapsed(self):
        data=supported_fixture();g=data.graph(G1)
        for decision in (EX.pitchOriginal0,EX.pitchOperative0):g.add((decision,CCO.ont00001808,EX.motion1))
        g.add((EX.pitchRecord0,CCO.ont00001808,EX.pitch1))
        row=next(r for r in evidence(data) if r['review']==str(EX.pitchReview0))
        self.assertEqual(row['gaps'],['CONFLICTING_REVIEW_SUBJECT'])
        self.assertIsNone(row['affectedPlayer'])

    def test_sql_retains_subjects_without_admitting_a_player_population(self):
        raw=bindings(supported_fixture(),[G1]);rows=M.normalize_bindings(raw,[G1])
        expected=M.live_result('adjudication-volatility',rows,graph_count=1)
        self.assertEqual(expected['coverage']['reviewsWithAffectedPlayer'],2)
        self.assertFalse(expected['coverage']['populationComplete'])
        self.assertEqual(expected['value'],M.exact(M.Fraction(1,3)))
        with database() as conn:
            M.materialize_game(conn,G1,raw+raw)
            result=M.query_sql(conn,{'metricId':'adjudication-volatility'},
                {'gameSet':'regular_season','startDate':'2026-08-01','endDate':'2026-08-01'})
            self.assertEqual(result['metric'],expected)
            self.assertNotIn('playerResults',result['metric'])

    def test_subject_identities_must_be_iris(self):
        raw=bindings(supported_fixture(),[G1])
        for field in ('reviewPA','reviewPitch','reviewMotion','reviewBatterAct','affectedPlayer'):
            changed=copy.deepcopy(raw)
            row=next(r for r in changed if field in r)
            row[field]['type']='literal'
            with self.assertRaisesRegex(M.EvidenceError,'identity must be an IRI'):
                M.normalize_bindings(changed,[G1])


if __name__=='__main__':unittest.main()
