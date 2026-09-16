"""Focused M1/M2 source-selection and adversarial conformance regressions."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

from pyshacl import validate
from rdflib import Graph, Namespace, RDF, URIRef

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location('metric_context', ROOT/'scripts/pipeline/prepare-rml-context.py')
CONTEXT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTEXT)
BASE = Namespace('https://baseballontology.org/')
BFO = Namespace('http://purl.obolibrary.org/obo/')
CCO = Namespace('https://www.commoncoreontologies.org/')
SH = Namespace('http://www.w3.org/ns/shacl#')
SHAPE = Namespace('https://w3id.org/baseball/shacl/')


def source_play(index=1):
    d = json.loads((ROOT/'data/raw/samples/2026-08-23/824315.json').read_bytes())
    return d['liveData']['plays']['allPlays'][index]


def selected(plays, consistent=True):
    """Unit fixture: isolate source gates; full E1 proof runs through main."""
    d = {'gamePk':824315, '_baseballO':{'runnerHistoryReconciliation':{
        'inputSha256':'fixture', 'sourceRevision':'fixture',
        'sourceConsistency':'consistent' if consistent else 'inconsistent'}},
        'liveData':{'plays':{'allPlays':copy.deepcopy(plays)}}}
    for p in d['liveData']['plays']['allPlays']:
        p['_baseballO'] = p.get('_baseballO', {})
        for e in p['playEvents']:
            if e.get('isPitch') is True:
                e['_baseballO'] = {'isBuntAttempt':False}
    return d, CONTEXT.metric_pitch_context(d)


class SourceSelectionTests(unittest.TestCase):
    def test_real_second_strike_and_held_count(self):
        _, e = selected([source_play(1)])
        self.assertEqual([r['eventIndex'] for r in e['countedFouls']], [4])
        _, e = selected([source_play(35)])
        self.assertFalse(e['countedFouls'])

    def test_second_strike_faults_withhold_without_erasing_source(self):
        for fault in ('missing-count', 'boolean-count', 'duplicate-index', 'missing-prefix', 'overlap', 'review', 'substitution', 'counter-correction', 'source-inconsistent'):
            p = source_play(1)
            if fault == 'missing-count': p['playEvents'][3].pop('count')
            elif fault == 'boolean-count': p['playEvents'][3]['count']['strikes'] = True
            elif fault == 'duplicate-index': p['playEvents'][3]['index'] = 2
            elif fault == 'missing-prefix': p['playEvents'].pop(0)
            elif fault == 'overlap': p['playEvents'][3]['endTime'] = p['playEvents'][4]['endTime']
            elif fault == 'review': p['playEvents'][0]['details']['hasReview'] = True
            elif fault == 'substitution': p['playEvents'][0]['isSubstitution'] = True
            elif fault == 'counter-correction': p['playEvents'][2]['count']['strikes'] = 0
            before = copy.deepcopy(p)
            _, e = selected([p], fault != 'source-inconsistent')
            self.assertFalse(e['countedFouls'], fault)
            self.assertEqual(p, before)

    def test_neutral_nonpitch_prefix_is_retained(self):
        p = source_play(1)
        previous = p['playEvents'][3]
        action = {'index':4,'isPitch':False,'type':'action','details':{'eventType':'batter_timeout'},
                  'count':previous['count'].copy(), 'startTime':previous['endTime'], 'endTime':previous['endTime']}
        p['playEvents'].insert(4, action)
        for i,e in enumerate(p['playEvents']): e['index']=i
        _, e = selected([p])
        self.assertEqual(len(e['countedFouls']), 1)
        p['playEvents'][4]['count']['strikes'] = 2
        _, e = selected([p])
        self.assertFalse(e['countedFouls'])

    def test_two_nonterminal_reviews_keep_pitch_identity(self):
        d, e = selected([source_play(36), source_play(43)])
        self.assertEqual(len(e['pitchReviews']), 2)
        for row in e['pitchReviews']:
            self.assertIn('/judgment/ball/', row['reviewIri'])
            self.assertNotEqual(row['reviewIri'], row['originalJudgmentIri'])
            self.assertNotIn('664954', json.dumps(row))
            self.assertTrue(row['affectedBatterSupported'])

    def test_two_reviews_in_one_pa_do_not_collapse(self):
        p = source_play(36)
        first = p['playEvents'][0]
        first['details'].update(call={'code':'C'}, isBall=False, isStrike=True, hasReview=True)
        first['reviewDetails'] = {'inProgress':False, 'isOverturned':False}
        _, e = selected([p])
        self.assertEqual(len({r['reviewIri'] for r in e['pitchReviews']}), 2)

    def test_completed_affirmation_is_required(self):
        for fault in ('overturned','in-progress','missing-progress','contradictory-flags','swing','duplicate-pitch'):
            p=source_play(36); event=p['playEvents'][5]
            if fault == 'overturned': event['reviewDetails']['isOverturned']=True
            elif fault == 'in-progress': event['reviewDetails']['inProgress']=True
            elif fault == 'missing-progress': event['reviewDetails'].pop('inProgress')
            elif fault == 'contradictory-flags': event['details']['isStrike']=True
            elif fault == 'swing': event['details']['call']['code']='S'
            elif fault == 'duplicate-pitch': p['playEvents'][0]['playId']=event['playId']
            _,e=selected([p]); self.assertFalse(e['pitchReviews'],fault)

    def test_duplicate_pa_narrative_reuses_canonical_review(self):
        p=source_play(36); p['playEvents']=p['playEvents'][:6]
        p['_baseballO']={'hasReview':True,'reviewType':'pitch_result','reviewOutcome':'affirming',
                        'reviewFinalDecision':'ball','reviewOriginalDecision':'ball'}
        d,e=selected([p]); row,=e['pitchReviews']
        self.assertEqual(row['reviewIri'],'https://baseballontology.org/data/game/824315/review/36/act')
        self.assertEqual(d['liveData']['plays']['allPlays'][0]['playEvents'][5]['_baseballO']['ballJudgmentIri'],row['reviewIri'])
        self.assertTrue(row['reusesPlayReview'])
        p['_baseballO']['reviewOutcome']='overturning'
        d,e=selected([p]); self.assertFalse(e['pitchReviews'])
        self.assertFalse(d['liveData']['plays']['allPlays'][0]['_baseballO']['hasReview'])

    def test_earlier_review_does_not_change_terminal_review_disposition(self):
        p={'result':{'description':'Player challenged (pitch result), call on the field was confirmed: Player walks.'}}
        events=[{'details':{'call':{'code':'C'}},'reviewDetails':{'isOverturned':True}},
                {'details':{'call':{'code':'B'}},'reviewDetails':{'isOverturned':False}}]
        result=CONTEXT.reviewed_play_context(p,events,{},'1')
        self.assertEqual(result['reviewOutcome'],'affirming')
        self.assertEqual(result['reviewFinalDecision'],'ball')

    def test_terminated_count_cannot_reset_into_an_added_foul(self):
        p=source_play(1)
        p['playEvents'][0]['count'].update(balls=0,strikes=3)
        _,e=selected([p]); self.assertFalse(e['countedFouls'])

    def test_substitution_does_not_assign_final_batter_to_review(self):
        p=source_play(36)
        p['playEvents'][0]['details']['eventType']='offensive_substitution'
        _,e=selected([p]); row,=e['pitchReviews']
        self.assertFalse(row['affectedBatterSupported'])


def review_graph():
    """Hand-written world-side fixture; not generated from RML or context."""
    g=Graph(); n=Namespace('urn:test:')
    triples=[
        (n.oldJudgment,RDF.type,BASE.ReviewedOnFieldUmpireJudgmentAct),(n.oldJudgment,RDF.type,BASE.BallJudgmentAct),
        (n.oldJudgment,CCO.ont00001986,n.oldDecision),(n.oldJudgment,BFO.BFO_0000063,n.review),(n.oldJudgment,BFO.BFO_0000132,n.oldProcess),
        (n.oldProcess,RDF.type,BASE.BaseballInstitutionalProcess),(n.oldProcess,BFO.BFO_0000117,n.oldJudgment),
        (n.oldDecision,RDF.type,BASE.ReviewedOnFieldBaseballDecisionICE),(n.oldDecision,RDF.type,BASE.BallDecisionICE),
        (n.oldDecision,CCO.ont00001808,n.oldProcess),(n.oldDecision,CCO.ont00001808,n.motion),(n.oldDecision,CCO.ont00001841,n.review),
        (n.review,RDF.type,BASE.BaseballReplayReviewAct),(n.review,RDF.type,BASE.BallAffirmingBaseballReplayReviewAct),(n.review,RDF.type,BASE.BallJudgmentAct),
        (n.review,CCO.ont00001921,n.oldDecision),(n.review,CCO.ont00001921,n.ballRule),(n.review,CCO.ont00001986,n.newDecision),(n.review,CCO.ont00001986,n.disposition),(n.review,BFO.BFO_0000132,n.process),
        (n.newDecision,RDF.type,BASE.BaseballReplayDecisionICE),(n.newDecision,RDF.type,BASE.BallDecisionICE),
        (n.newDecision,CCO.ont00001808,n.motion),(n.newDecision,CCO.ont00001808,n.process),
        (n.motion,RDF.type,BASE.PitchBallMotionProcess),(n.process,RDF.type,BASE.BallProcess),(n.process,BFO.BFO_0000117,n.review),
        (n.disposition,RDF.type,BASE.AffirmingBaseballReplayReviewDispositionICE),(n.disposition,CCO.ont00001816,n.review),
        (n.disposition,CCO.ont00001808,n.oldDecision),(n.disposition,CCO.ont00001808,n.newDecision)]
    for triple in triples: g.add(triple)
    return g,n


class ConformanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shapes=Graph().parse(ROOT/'sources/mlb-game/shacl/authoritative.ttl')

    def conforms(self,g):
        return validate(g,shacl_graph=self.shapes,use_shapes=[str(SHAPE.M2OriginalJudgmentTargetShape),str(SHAPE.M2OriginalJudgmentShape),str(SHAPE.M2OperativeReviewShape)])[0]

    def test_counted_foul_requires_complete_graph(self):
        n=Namespace('urn:foul:');g=Graph()
        for triple in [
            (n.strike,RDF.type,BASE.StrikeProcess),(n.foul,RDF.type,BASE.FoulBallProcess),
            (n.strike,BFO.BFO_0000062,n.foul),(n.strike,BFO.BFO_0000132,n.pa),(n.foul,BFO.BFO_0000132,n.pa),
            (n.pa,RDF.type,BASE.PlateAppearance),(n.strike,BFO.BFO_0000117,n.judgment),
            (n.strike,CCO.ont00001918,n.field),(n.judgment,CCO.ont00001921,BASE["data/rule/strike"]),
            (BASE["data/rule/strike"],RDF.type,BASE.StrikeRule),
            (n.judgment,RDF.type,BASE.StrikeJudgmentAct),(n.judgment,BFO.BFO_0000132,n.strike),
            (n.judgment,CCO.ont00001986,n.decision),(n.decision,RDF.type,BASE.StrikeDecisionICE),
            (n.decision,CCO.ont00001808,n.strike),(n.record,RDF.type,BASE.BaseballEventRecord),
            *[(n.record,CCO.ont00001808,x) for x in (n.strike,n.foul,n.judgment,n.decision)]]:
            g.add(triple)
        check=lambda graph: validate(graph,shacl_graph=self.shapes,use_shapes=[str(SHAPE.CountedFoulStrikeShape)])[0]
        self.assertTrue(check(g))
        for triple in [(n.judgment,CCO.ont00001986,n.decision),(n.record,CCO.ont00001808,n.decision),
                       (n.foul,BFO.BFO_0000132,n.pa),(n.judgment,CCO.ont00001921,BASE["data/rule/strike"])]:
            g.remove(triple);self.assertFalse(check(g));g.add(triple)

    def test_optional_umpire_removal_preserves_mapping_syntax(self):
        text=(ROOT/'sources/mlb-game/mapping/mlb-game.rml.ttl').read_text(encoding='utf-8')
        Graph().parse(data='\n'.join(l for l in text.splitlines() if '{$.homePlateUmpire.id}' not in l),format='turtle')

    def test_valid_review_and_adversarial_mutations(self):
        g,n=review_graph(); self.assertTrue(self.conforms(g))
        for fault in ('same-decision','missing-motion','different-motion','wrong-content','duplicate-input','duplicate-output','unrelated-decision-output','copied-umpire-role','copied-umpire-participant','merged-judgment'):
            g,n=review_graph()
            if fault=='same-decision': g.remove((n.review,CCO.ont00001986,n.newDecision)); g.add((n.review,CCO.ont00001986,n.oldDecision))
            elif fault=='missing-motion': g.remove((n.newDecision,CCO.ont00001808,n.motion))
            elif fault=='different-motion': g.add((n.otherMotion,RDF.type,BASE.PitchBallMotionProcess)); g.add((n.newDecision,CCO.ont00001808,n.otherMotion))
            elif fault=='wrong-content': g.remove((n.newDecision,RDF.type,BASE.BallDecisionICE)); g.add((n.newDecision,RDF.type,BASE.StrikeDecisionICE))
            elif fault=='duplicate-output': g.add((n.extra,RDF.type,BASE.BallDecisionICE)); g.add((n.review,CCO.ont00001986,n.extra))
            elif fault=='duplicate-input': g.add((n.extra,RDF.type,BASE.OutDecisionICE)); g.add((n.review,CCO.ont00001921,n.extra))
            elif fault=='unrelated-decision-output': g.add((n.extra,RDF.type,BASE.OutDecisionICE)); g.add((n.review,CCO.ont00001986,n.extra))
            elif fault=='copied-umpire-role': g.add((n.review,BFO.BFO_0000055,n.umpireRole))
            elif fault=='copied-umpire-participant': g.add((n.review,BFO.BFO_0000057,n.umpire))
            elif fault=='merged-judgment': g.add((n.oldJudgment,RDF.type,BASE.BaseballReplayReviewAct))
            self.assertFalse(self.conforms(g),fault)


if __name__=='__main__':
    unittest.main()
