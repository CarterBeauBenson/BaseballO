"""A verified no-pitch intentional walk is inapplicable, not a missing history."""
import copy
import json
import unittest

from pyshacl import validate
from rdflib import RDF,URIRef
from test_pitch_count_admission import A
from test_batting_progress_players import fixture,BASE,BFO,CCO,GAME,PROOF
from test_metric_suite_serving import M,G1,bindings,database


def graph_fixture():
    data=fixture();g=data.graph(G1);pa=str(GAME)+'/plate-appearance/0'
    for i in (1,2,3):g.remove((URIRef(str(GAME)+'/plate-appearance/'+str(i)),RDF.type,BASE.PlateAppearance))
    result=URIRef(pa+'/result')
    g.remove((result,RDF.type,BASE.SingleProcess));g.add((result,RDF.type,BASE.WalkProcess))
    return data,pa


class ZeroPitchWalkRecovery(unittest.TestCase):
    def test_real_four_virtual_balls_require_the_whole_supported_award(self):
        document=json.loads((M.ROOT/'data/raw/samples/2026-08-25/823585.json').read_bytes())
        play=document['liveData']['plays']['allPlays'][79]
        self.assertTrue(A.virtual_intentional_walk(play,2026))
        source=A.census(json.dumps(document).encode(),'823585')
        selected=next(p for p in source['plateAppearances'] if p['pa'].endswith('/79'))
        self.assertTrue(selected['zeroPitchIntentionalWalk']);self.assertEqual(selected['events'],[])
        self.assertFalse(any(i.get('plateAppearance')==selected['pa'] for i in source['issues']))
        for fault in ('missing','pitch','count','strike','out','reach','review'):
            changed=copy.deepcopy(play)
            if fault=='missing':changed['playEvents'].pop()
            elif fault=='pitch':changed['playEvents'][0]['isPitch']=True
            elif fault=='count':changed['playEvents'][1]['count']['balls']=3
            elif fault=='strike':changed['playEvents'][1]['count']['strikes']=1
            elif fault=='out':changed['playEvents'][1]['count']['outs']+=1
            elif fault=='reach':changed['matchup'].pop('postOnFirst')
            else:changed['reviewDetails']={'inProgress':True};changed['about']['hasReview']=True
            self.assertFalse(A.virtual_intentional_walk(changed,2026),fault)

    def test_zero_shape_requires_walk_and_rejects_invented_pitch_strike_and_award(self):
        data,pa=graph_fixture();g=data.graph(G1)
        source=dict(game=str(GAME),plateAppearances=[dict(pa=pa,events=[],zeroPitchIntentionalWalk=True)])
        shape=A.shape_text(source)
        check=lambda:validate(g,shacl_graph=shape,shacl_graph_format='turtle',advanced=True)[0]
        self.assertTrue(check())
        walk=(URIRef(pa+'/result'),RDF.type,BASE.WalkProcess)
        g.remove(walk);self.assertFalse(check());g.add(walk)
        for kind in (BASE.PitchAct,BASE.StrikeProcess,BASE.BallProcess):
            event=URIRef(str(GAME)+'/invented');record=URIRef(str(GAME)+'/event-record/count-award/invented')
            triples=[(event,RDF.type,kind),(event,BFO.BFO_0000132,URIRef(pa))]
            if kind==BASE.BallProcess:triples.extend([(record,RDF.type,BASE.BaseballEventRecord),(record,CCO.ont00001808,event)])
            for t in triples:g.add(t)
            self.assertFalse(check(),kind)
            for t in triples:g.remove(t)

    def test_only_admitted_exact_zero_census_can_establish_known_ineligibility(self):
        data,pa=graph_fixture();raw=bindings(data,[G1]);rows=M.normalize_bindings(raw,[G1])
        missing=M.recovery_game_inputs(rows,graph=G1,batting_admission=PROOF,pitch_count_admission=PROOF)
        self.assertFalse(missing['complete']);self.assertEqual(missing['gaps'],['EMPTY_COUNT_HISTORY'])
        proof=dict(PROOF,zeroPitchPlateAppearances=[pa])
        result=M.recovery_game_inputs(rows,graph=G1,batting_admission=PROOF,pitch_count_admission=proof)
        self.assertTrue(result['complete']);item,=result['plateAppearances']
        self.assertFalse(item['twoStrikeEligible']);self.assertIsNone(item['value']);self.assertEqual(item['countHistory'],[])
        self.assertEqual(item['gaps'],['NOT_TWO_STRIKE_ELIGIBLE'])
        for p in (dict(proof,status='withheld'),{}):
            self.assertFalse(M.recovery_game_inputs(rows,graph=G1,batting_admission=PROOF,pitch_count_admission=p)['complete'])
        for population in ([pa,pa],[pa+'/unknown'],[{}],None):
            with self.assertRaises(M.EvidenceError):
                M.recovery_game_inputs(rows,graph=G1,batting_admission=PROOF,pitch_count_admission=dict(PROOF,zeroPitchPlateAppearances=population))
        with database() as conn:
            M.materialize_game(conn,G1,raw,batting_admission=PROOF,pitch_count_admission=proof)
            retained,=M.read_results(conn,G1,'recovery-quality')
            self.assertEqual(retained['recoveryInputs'],result)

    def test_graph_outcome_or_count_conflict_cannot_use_zero_census(self):
        data,pa=graph_fixture();g=data.graph(G1);result=URIRef(pa+'/result')
        g.add((result,RDF.type,BASE.SingleProcess))
        rows=M.normalize_bindings(bindings(data,[G1]),[G1])
        self.assertEqual(M.recovery_histories(rows,zero_pitch_pas={(G1,pa)})['unresolvedPlateAppearances'][0]['gap'],'ZERO_PITCH_COUNT_CONFLICT')
        g.remove((result,RDF.type,BASE.SingleProcess))
        pitch=URIRef(str(GAME)+'/unexpected-pitch')
        g.add((pitch,RDF.type,BASE.PitchAct));g.add((pitch,BFO.BFO_0000132,URIRef(pa)))
        rows=M.normalize_bindings(bindings(data,[G1]),[G1])
        self.assertEqual(M.recovery_histories(rows,zero_pitch_pas={(G1,pa)})['unresolvedPlateAppearances'][0]['gap'],'ZERO_PITCH_COUNT_CONFLICT')


if __name__=='__main__':unittest.main()
