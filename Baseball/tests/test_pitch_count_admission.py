"""Source census, exact existing-RDF conformance, and Recovery extraction."""
import importlib.util
import json
from pathlib import Path
import unittest

from pyshacl import validate
from rdflib import Literal,RDF,URIRef,XSD

from test_batting_progress_players import fixture,BASE,BFO,CCO,GAME
from test_metric_suite_serving import M,G1,bindings

spec=importlib.util.spec_from_file_location('pitch_count_admission',M.ROOT/'sources/mlb-game/pipeline/pitch-count-admission.py')
A=importlib.util.module_from_spec(spec);spec.loader.exec_module(A)


def pitch_fixture():
    data=fixture();g=data.graph(G1);pa=str(GAME)+'/plate-appearance/0'
    for i in (1,2,3):g.remove((URIRef(str(GAME)+'/plate-appearance/'+str(i)),RDF.type,BASE.PlateAppearance))
    source=dict(game=str(GAME),plateAppearances=[dict(pa=pa,events=[])])
    count=0
    for i,strike in enumerate([True,True,False,False,False]):
        pid='pitch-'+str(i);pitch=str(GAME)+'/pitch/'+pid;record=str(GAME)+'/event-record/pitch/'+pid
        count+=strike
        e=dict(event=pitch,kind='pitch',playId=pid,strike=strike,strikesAfter=count,
               start=f'2026-08-01T12:0{i}:00Z',end=f'2026-08-01T12:0{i}:01Z')
        source['plateAppearances'][0]['events'].append(e)
        g.add((URIRef(pitch),RDF.type,BASE.PitchAct));g.add((URIRef(pitch),BFO.BFO_0000132,URIRef(pa)))
        interval=URIRef(pitch+'/temporal-interval')
        g.add((URIRef(pitch),BFO.BFO_0000199,interval));g.add((interval,RDF.type,BFO.BFO_0000038))
        for side,edge in [('start',BFO.BFO_0000222),('end',BFO.BFO_0000224)]:
            instant=URIRef(pitch+'/temporal-instant/'+side);stamp=URIRef(pitch+'/timestamp/'+side)
            g.add((interval,edge,instant));g.add((instant,RDF.type,BASE.BaseballEventTemporalInstant))
            g.add((stamp,RDF.type,BASE.BaseballTimestampICE));g.add((stamp,CCO.ont00001916,instant))
            g.add((stamp,CCO.ont00001808,URIRef(pitch)));g.add((stamp,CCO.ont00001767,Literal(e[side],datatype=XSD.dateTime)))
        g.add((URIRef(record),RDF.type,BASE.BaseballEventRecord));g.add((URIRef(record),CCO.ont00001808,URIRef(pitch)))
        if strike:
            outcome=URIRef(str(GAME)+'/process/strike/'+pid);judgment=URIRef(str(outcome)+'/judgment');decision=URIRef(str(outcome)+'/decision')
            g.add((URIRef(record),CCO.ont00001808,outcome));g.add((outcome,RDF.type,BASE.StrikeProcess))
            g.add((outcome,BFO.BFO_0000132,URIRef(pa)));g.add((outcome,BFO.BFO_0000117,judgment))
            g.add((judgment,RDF.type,BASE.StrikeJudgmentAct));g.add((judgment,CCO.ont00001986,decision))
            g.add((decision,RDF.type,BASE.StrikeDecisionICE));g.add((decision,CCO.ont00001808,outcome))
    return data,source


def extract(data):return M.recovery_histories(M.normalize_bindings(bindings(data,[G1]),[G1]))


class PitchCountAdmission(unittest.TestCase):
    def test_equivalent_datetime_lexical_forms_and_foul_tip_subclasses(self):
        data,source=pitch_fixture();g=data.graph(G1)
        e=source['plateAppearances'][0]['events'][0]
        stamp=URIRef(e['event']+'/timestamp/start')
        g.remove((stamp,CCO.ont00001767,None))
        g.add((stamp,CCO.ont00001767,Literal('2026-08-01T08:00:00.000-04:00',datatype=XSD.dateTime,normalize=False)))
        old=URIRef(str(GAME)+'/process/strike/pitch-0');new=URIRef(str(GAME)+'/process/foul-tip/pitch-0')
        for s,p,o in list(g):
            if s==old or o==old:
                g.remove((s,p,o));g.add((new if s==old else s,p,new if o==old else o))
        judgment=URIRef(str(old)+'/judgment');decision=URIRef(str(old)+'/decision')
        g.remove((judgment,RDF.type,BASE.StrikeJudgmentAct));g.add((judgment,RDF.type,BASE.FoulTipJudgmentAct))
        g.remove((decision,RDF.type,BASE.StrikeDecisionICE));g.add((decision,RDF.type,BASE.FoulTipCallICE))
        for code in ('T','O'):
            e['call']=code
            self.assertTrue(validate(g,shacl_graph=A.shape_text(source),shacl_graph_format='turtle',advanced=True)[0],code)
        self.assertEqual(extract(data)['plateAppearances'][0]['value'],M.exact(2))

    def test_automatic_second_strike_is_ordered_but_is_not_a_pitch(self):
        data,source=pitch_fixture();g=data.graph(G1);pa=URIRef(source['plateAppearances'][0]['pa'])
        pitch1=URIRef(str(GAME)+'/pitch/pitch-1');strike1=URIRef(str(GAME)+'/process/strike/pitch-1')
        for triple in list(g.triples((strike1,None,None)))+list(g.triples((None,None,strike1))):g.remove(triple)
        award=URIRef(str(GAME)+'/process/count-award/automatic');judgment=URIRef(str(award)+'/judgment')
        decision=URIRef(str(award)+'/decision');record=URIRef(str(GAME)+'/event-record/count-award/automatic')
        g.add((award,RDF.type,BASE.StrikeProcess));g.add((award,BFO.BFO_0000132,pa));g.add((award,BFO.BFO_0000117,judgment))
        g.add((judgment,RDF.type,BASE.StrikeJudgmentAct));g.add((judgment,BFO.BFO_0000132,award))
        g.add((judgment,CCO.ont00001986,decision));g.add((judgment,CCO.ont00001921,URIRef('urn:test:rule')))
        g.add((decision,RDF.type,BASE.StrikeDecisionICE));g.add((decision,CCO.ont00001808,award))
        g.add((record,RDF.type,BASE.BaseballEventRecord))
        for value in (award,judgment,decision):g.add((record,CCO.ont00001808,value))
        prior=URIRef(str(GAME)+'/pitch/pitch-0')
        g.add((prior,BFO.BFO_0000063,award));g.add((award,BFO.BFO_0000063,pitch1))
        rows=M.normalize_bindings(bindings(data,[G1]),[G1]);result=M.recovery_histories(rows)
        self.assertEqual(result['unresolvedPlateAppearances'],[])
        pa,=result['plateAppearances'];self.assertEqual(pa['value'],M.exact(3))
        self.assertEqual(pa['countHistory'][1]['countAward'],str(award))
        self.assertEqual(pa['countHistory'][1]['strikesAfter'],2)
        # A precedence edge to a nonadjacent pitch must not reorder the feed.
        g.remove((award,BFO.BFO_0000063,pitch1))
        g.add((award,BFO.BFO_0000063,URIRef(str(GAME)+'/pitch/pitch-2')))
        self.assertEqual(extract(data)['unresolvedPlateAppearances'][0]['gap'],'UNSUPPORTED_AUTOMATIC_AWARD_ORDER')

    def test_real_reference_source_reconciles_without_supplying_scores(self):
        raw=(M.ROOT/'data/raw/game-566279.json').read_bytes()
        census=A.census(raw,'566279')
        self.assertEqual(census['issues'],[])
        self.assertEqual(len(census['plateAppearances']),79)
        self.assertEqual(sum(len(p['events']) for p in census['plateAppearances']),282)
        self.assertNotIn('recoveryScore',json.dumps(census))

    def test_full_shape_and_rdf_extraction_count_only_nonterminal_recovery_pitches(self):
        data,source=pitch_fixture()
        self.assertTrue(validate(data.graph(G1),shacl_graph=A.shape_text(source),shacl_graph_format='turtle',advanced=True)[0])
        result=extract(data)
        self.assertEqual(result['unresolvedPlateAppearances'],[])
        pa,=result['plateAppearances'];self.assertEqual(pa['value'],M.exact(2))
        self.assertEqual([e['strikesAfter'] for e in pa['countHistory']],[1,2,2,2,2])

    def test_source_shape_rejects_missing_strike_extra_pitch_and_wrong_timestamp(self):
        for change in ('strike','pitch','time','extra_strike','extra_award'):
            with self.subTest(change=change):
                data,source=pitch_fixture();g=data.graph(G1)
                if change=='strike':g.remove((URIRef(str(GAME)+'/process/strike/pitch-1'),RDF.type,BASE.StrikeProcess))
                elif change=='time':g.add((URIRef(str(GAME)+'/pitch/pitch-0/timestamp/end'),CCO.ont00001767,Literal('2026-08-01T13:00:00Z',datatype=XSD.dateTime)))
                else:
                    extra=URIRef(str(GAME)+'/extra');g.add((extra,BFO.BFO_0000132,URIRef(source['plateAppearances'][0]['pa'])))
                    g.add((extra,RDF.type,BASE.PitchAct if change=='pitch' else BASE.StrikeProcess))
                    if change=='extra_award':
                        record=URIRef(str(GAME)+'/event-record/count-award/extra')
                        g.add((record,RDF.type,BASE.BaseballEventRecord));g.add((record,CCO.ont00001808,extra))
                self.assertFalse(validate(g,shacl_graph=A.shape_text(source),shacl_graph_format='turtle',advanced=True)[0])

    def test_unknown_or_overlapping_pitch_times_cannot_be_sorted_by_id(self):
        data,_=pitch_fixture();g=data.graph(G1)
        stamp=URIRef(str(GAME)+'/pitch/pitch-0/timestamp/end')
        g.remove((stamp,CCO.ont00001767,None));g.add((stamp,CCO.ont00001767,Literal('2026-08-01T12:03:00Z',datatype=XSD.dateTime)))
        self.assertEqual(extract(data)['unresolvedPlateAppearances'][0]['gap'],'UNSUPPORTED_PITCH_ORDER')


if __name__=='__main__':unittest.main()
