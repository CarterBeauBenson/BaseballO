"""D1 real source witnesses, conservative exclusions and graph mutations."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from pyshacl import validate
from rdflib import Graph, RDF, URIRef
from test_metric_mapping_completion import CONTEXT, ROOT, BASE, BFO, CCO

spec=importlib.util.spec_from_file_location('defense_admission',ROOT/'sources/mlb-game/pipeline/defensive-admission.py')
A=importlib.util.module_from_spec(spec);spec.loader.exec_module(A)
RAW=(ROOT/'data/raw/samples/2026-08-25/822693.json').read_bytes()


def document(pa=None):
    d=json.loads(RAW)
    if pa is not None:d['liveData']['plays']['allPlays']=[d['liveData']['plays']['allPlays'][pa]]
    d['_baseballO']={'runnerHistoryReconciliation':dict(sourceConsistency='consistent',inputSha256=A.B.sha(RAW),sourceRevision='fixture')}
    return d


def hand_graph(source):
    g=Graph()
    for p in source['plays']:
        play=URIRef(p['resolution']);pa=URIRef(source['game']+'/plate-appearance/'+p['atBatIndex'])
        g.add((play,RDF.type,BASE.BattedBallPlayProcess));g.add((play,BFO.BFO_0000132,pa))
    for r in source['acts']:
        act,agent,role,play,record=[URIRef(r[k]) for k in ('actIri','agentIri','roleIri','playIri','recordIri')]
        for t in [(act,RDF.type,URIRef(r['classIri'])),(act,CCO.ont00001833,agent),
            (act,BFO.BFO_0000055,role),(act,BFO.BFO_0000132,play),(role,RDF.type,BASE.FielderRole),
            (role,BFO.BFO_0000197,agent),(agent,RDF.type,CCO.ont00001262),
            (record,RDF.type,BASE.BaseballEventRecord),(record,CCO.ont00001808,act)]:g.add(t)
        if r['catch']:g.add((act,RDF.type,BASE.FieldingAttemptAct))
    return g


class DefensiveMappingTests(unittest.TestCase):
    def test_named_catch_has_one_identity_and_persistent_role(self):
        e=CONTEXT.defensive_act_context(document(1));row,=e['acts']
        self.assertEqual(row['agentIri'],BASE+'data/player/686611')
        self.assertEqual(row['roleIri'],BASE+'data/player/686611/role/fielder')
        self.assertTrue(row['catch']);self.assertTrue(e['populationComplete'])
        self.assertTrue(row['creditPointers']);self.assertFalse(e['precedence'])

    def test_generic_groundout_and_sole_putout_do_not_invent_acts(self):
        for pa in (2,8):
            e=CONTEXT.defensive_act_context(document(pa))
            self.assertFalse(e['acts']);self.assertFalse(e['populationComplete'])

    def test_real_relay_preserves_performances_without_tag_or_order(self):
        d=document(26);e=CONTEXT.defensive_act_context(d)
        self.assertEqual([r['classIri'].split('/')[-1] for r in e['acts']],
            ['FieldingAttemptAct','ThrowAct','CatchAttemptAct','ThrowAct','CatchAttemptAct','ThrowAct','CatchAttemptAct'])
        self.assertEqual(len(set(r['actIri'] for r in e['acts'])),7)
        self.assertEqual(len(set(r['agentIri'] for r in e['acts'])),4)
        self.assertFalse(e['populationComplete']);self.assertFalse(e['precedence'])
        p=d['liveData']['plays']['allPlays'][0]
        for runner in p['runners']:
            runner['credits']=[c for c in runner['credits'] if c['credit']!='f_assist_of']
        self.assertEqual([r['actIri'] for r in CONTEXT.defensive_act_context(d)['acts']],[r['actIri'] for r in e['acts']])

    def test_source_faults_withhold_catch(self):
        for fault in ('credit','agent','review','id','duplicate'):
            d=document(1);p=d['liveData']['plays']['allPlays'][0]
            if fault=='credit':p['runners'][-1]['credits'][0]['credit']='f_assist'
            if fault=='agent':p['runners'][-1]['credits'][0]['player']['id']=1
            if fault=='review':p['about']['hasReview']=True
            if fault=='id':p['playEvents'][-1].pop('playId')
            if fault=='duplicate':p['playEvents'][0]['playId']=p['playEvents'][-1]['playId']
            self.assertFalse(CONTEXT.defensive_act_context(d)['acts'],fault)

    def test_explicit_ground_sentence_and_tag_have_separate_positive_evidence(self):
        d=document(2);p=d['liveData']['plays']['allPlays'][0]
        p['result']['description']='Shortstop Nasim Nunez fields the ground ball and throws to first baseman Abimelec Ortiz, who catches the throw.'
        e=CONTEXT.defensive_act_context(d)
        self.assertEqual([r['classIri'].split('/')[-1] for r in e['acts']],['FieldingAttemptAct','ThrowAct','CatchAttemptAct'])
        self.assertFalse(e['populationComplete'])
        p['result']['description']='First baseman Abimelec Ortiz tags Hunter Goodman out at first base.'
        e=CONTEXT.defensive_act_context(d);self.assertEqual(len(e['acts']),1)
        self.assertEqual(e['acts'][0]['classIri'],BASE+'TagAttemptAct')
        p['runners'][-1]['movement']['outBase']='2B'
        self.assertFalse(CONTEXT.defensive_act_context(d)['acts'])

    def test_corrections_keep_aligned_identity_and_quarantine_reassignment(self):
        d=document(1);e=CONTEXT.defensive_act_context(d)
        same=CONTEXT.defensive_act_context(copy.deepcopy(d),e)
        self.assertEqual(same['acts'],e['acts']);self.assertTrue(same['identityAlignmentChecked'])
        d['liveData']['plays']['allPlays'][0]['result']['description']='Unresolved corrected description.'
        with self.assertRaisesRegex(ValueError,'alignment'):CONTEXT.defensive_act_context(d,e)

    def test_whole_game_census_does_not_drop_unselected_contacts(self):
        e=A.census(RAW,'822693')
        self.assertEqual(len(e['plays']),107);self.assertEqual(len(e['acts']),20)
        self.assertEqual(sum(p['complete'] for p in e['plays']),13)
        self.assertFalse(e['populationComplete']);self.assertFalse(e['orderComplete'])

    def test_source_bound_shacl_rejects_missing_wrong_and_extra_evidence(self):
        e=CONTEXT.defensive_act_context(document(1));e['game']=BASE+'data/game/822693'
        shapes=Graph().parse(data=A.shape_text(e),format='turtle')
        check=lambda g:validate(g,shacl_graph=shapes)[0]
        g=hand_graph(e);self.assertTrue(check(g))
        r=e['acts'][0];act=URIRef(r['actIri']);role=URIRef(r['roleIri']);agent=URIRef(r['agentIri'])
        for triple in [(act,CCO.ont00001833,agent),(act,BFO.BFO_0000055,role),
            (role,BFO.BFO_0000197,agent),(act,RDF.type,BASE.FieldingAttemptAct),
            (URIRef(r['recordIri']),CCO.ont00001808,act)]:
            g.remove(triple);self.assertFalse(check(g),triple);g.add(triple)
        for triple in [(act,CCO.ont00001833,URIRef('urn:wrong:agent')),
                       (act,BFO.BFO_0000063,URIRef('urn:invented:next')),
                       (URIRef('urn:extra:act'),RDF.type,BASE.ThrowAct)]:
            g.add(triple);self.assertFalse(check(g),triple);g.remove(triple)

    def test_promotion_binds_source_rdf_implementation_and_retained_proof(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);directory=root/'pipeline/evidence/mlb-game/822693/test';directory.mkdir(parents=True)
            source=A.census(RAW,'822693');rdf=directory/'game.ttl';hand_graph(source).serialize(destination=rdf,format='turtle')
            output=directory/'defensive-admission.json'
            proof=A.prove(raw=RAW,game_pk='822693',rdf_path=rdf,output=output)
            self.assertTrue(proof['graphConforms']);self.assertEqual(proof['status'],'withheld')
            self.assertFalse(proof['populationComplete'])
            marker=directory/'promotion.json'
            marker.write_text(json.dumps(dict(defensiveAdmission=str(output),defensiveAdmissionSha256=A.B.sha(output.read_bytes()))))
            promotion=dict(promotionManifest=str(marker),promotionManifestSha256=A.B.sha(marker.read_bytes()),gamePk='822693',
                rawSha256=proof['sourceSha256'],authoritativeRdfSha256=proof['authoritativeRdfSha256'],authoritativeGraph=proof['graph'])
            retained=A.promoted_admission(root,promotion)
            self.assertEqual(retained['status'],'withheld');self.assertEqual(retained['selectedActCount'],20)
            for key in ('rawSha256','authoritativeRdfSha256','authoritativeGraph'):
                self.assertEqual(A.promoted_admission(root,dict(promotion,**{key:'changed'}))['issues'][0]['code'],'DEFENSIVE_PROOF_MISSING_OR_STALE')
            output.with_suffix('.source.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'artifact changed'):A.promoted_admission(root,promotion)


if __name__=='__main__':unittest.main()
