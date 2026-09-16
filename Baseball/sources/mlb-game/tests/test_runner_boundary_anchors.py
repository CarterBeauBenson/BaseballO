"""C3 real boundary cases, ambiguous source rejection and correction identity."""
import copy
import importlib.util
import json
import unittest
from rdflib import Graph, RDF, URIRef
from pyshacl import validate
from test_runner_structural_patterns import CONTEXT, ROOT, BASE, BFO, CCO

spec=importlib.util.spec_from_file_location('c3_admission',ROOT/'sources/mlb-game/pipeline/runner-history-admission.py')
A=importlib.util.module_from_spec(spec);spec.loader.exec_module(A)


def source(game):return json.loads((ROOT/f'data/raw/samples/2026-08-25/{game}.json').read_bytes())
def history(doc,previous=None):return CONTEXT.personal_runner_histories(json.dumps(doc).encode(),previous)


class RunnerBoundaryAnchors(unittest.TestCase):
    def test_action_association_is_not_aliased_to_a_pitch(self):
        d=source(824233);result=history(d)
        self.assertTrue(all(h['status']=='reconciled' for h in result['halves']))
        row=next(h for h in result['histories'] if h['runnerId']=='802415' and h['terminal']=='out')
        self.assertEqual(row['terminationAnchor'],'action/d9c8510c-a2da-3bc8-b8a2-799b8271921e/caught_stealing_2b/802415')
        self.assertEqual(len(row['episodes']),2)
        self.assertEqual(row['terminationWitness']['form'],'action')
        self.assertIn('/playEvents/3',row['terminationWitness']['sourcePointer'])
        self.assertFalse(result['metricPopulationAdmitted'])

    def test_pinch_runner_keeps_a_distinct_personal_whole(self):
        d=source(823259);result=history(d)
        outgoing=next(h for h in result['histories'] if h['terminal']=='replaced')
        incoming=next(h for h in result['histories'] if h.get('entryWitness',{}).get('form')=='replacement')
        self.assertEqual((outgoing['runnerId'],incoming['runnerId']),('664034','687749'))
        self.assertEqual(outgoing['terminationAnchor'],incoming['entryAnchor'])
        self.assertNotEqual(outgoing['lifetimeKey'],incoming['lifetimeKey'])
        self.assertTrue(all(h['status']=='reconciled' for h in result['halves']))
        self.assertTrue(set(map(str,outgoing['episodes'])).isdisjoint(map(str,incoming['episodes'])))
        for h in (outgoing,incoming):
            for ep in h['episodes']:
                row=d['liveData']['plays']['allPlays'][int(ep['atBatIndex'])]['runners'][int(ep['runnerIndex'])]
                self.assertEqual(str(row['details']['runner']['id']),h['runnerId'])
        self.assertIn('C3_ADMINISTRATIVE_BASE_BOUNDARY',{i['code'] for i in result['boundaryIssues']})

    def test_placed_runner_starts_at_existing_episode_without_fictitious_advance(self):
        d=source(823989);result=history(d)
        placed=[h for h in result['histories'] if h['entryAnchor'].startswith('placement/')]
        self.assertEqual(len(placed),2)
        for h in placed:
            ep=h['episodes'][0];p=d['liveData']['plays']['allPlays'][int(ep['atBatIndex'])]
            self.assertEqual(p['runners'][int(ep['runnerIndex'])]['movement']['start'],'2B')
            self.assertNotEqual(h['entryAnchor'],h['terminationAnchor'])
        self.assertTrue(all(h['status']=='reconciled' for h in result['halves']))
        other=history(source(823585))
        top=next(h for h in other['halves'] if h['inning']==10 and h['half']=='top')
        self.assertEqual(top['status'],'withheld')
        self.assertIn('ZERO_EPISODE_PERSONAL_HISTORY',{i['code'] for i in top['issues']})
        retained=next(h for h in other['withheldHistories'] if h['inning']==10 and h['half']=='top')
        self.assertTrue(any(h['runnerId']=='666152' and not h['episodes'] for h in retained['completedCandidates']))
        ninth=next(h for h in other['halves'] if h['inning']==9 and h['half']=='bottom')
        self.assertEqual(ninth['status'],'reconciled')  # Pickoff uses pre-count, action uses post-count.

    def test_ambiguous_anchor_census_does_not_append_source_array_positions(self):
        for game,pa,event in ((824233,8,3),(823259,64,0),(823989,86,1)):
            with self.subTest(game=game):
                d=source(game);play=d['liveData']['plays']['allPlays'][pa]
                if game==823989:event=next(i for i,e in enumerate(play['playEvents']) if e['details'].get('eventType')=='runner_placed')
                selected=play['playEvents'][event]
                before=CONTEXT.runner_boundary_anchors(d)
                play['playEvents'].append(copy.deepcopy(selected))
                _,witnesses,collisions=CONTEXT.runner_boundary_anchors(d)
                self.assertEqual(len(collisions),1)
                self.assertNotIn(collisions[0]['anchor'],witnesses)
                self.assertEqual(len(witnesses),len(before[1])-1)

    def test_bad_admin_base_person_time_count_and_placement_scope_withhold(self):
        for fault in ('base','person','time','out-count','count','review'):
            with self.subTest(fault=fault):
                d=source(823259);e=d['liveData']['plays']['allPlays'][64]['playEvents'][0]
                if fault=='base':e['base']=3
                elif fault=='person':e['replacedPlayer']['id']=e['player']['id']
                elif fault=='time':e['endTime']='2026-08-26T04:01:30Z'
                elif fault=='out-count':e['count']['outs']=1
                elif fault=='count':e['count']['balls']=1
                else:e['details']['hasReview']=True
                result=history(d)
                self.assertFalse(any(h['terminal']=='replaced' for h in result['histories']))
                self.assertTrue(result['sourceConsistency']!='consistent' or any(
                    h['status']=='withheld' for h in result['halves'] if h['inning']==9 and h['half']=='bottom'))
        d=source(823989);d['gameData']['game']['type']='P'
        self.assertFalse(any(h['entryAnchor'].startswith('placement/') for h in history(d)['histories']))

    def test_identity_retry_is_stable_and_ambiguous_correction_is_quarantined(self):
        d=source(823259);before=history(d)
        self.assertEqual(history(d,before),before)
        changed=copy.deepcopy(before);changed['histories'][0]['terminationAnchor']='changed'
        with self.assertRaisesRegex(ValueError,'identity no longer aligns'):CONTEXT.verify_runner_history_correction(changed,before)
        changed=copy.deepcopy(before);changed['episodeMembership'][0]['lifetimeKey']='other'
        with self.assertRaisesRegex(ValueError,'allocation no longer aligns'):CONTEXT.verify_runner_history_correction(changed,before)

    def test_exact_source_shacl_rejects_missing_extra_or_misattributed_histories(self):
        source_census=A.census(json.dumps(source(823259)).encode(),'823259')
        row=next(h for h in source_census['history']['histories'] if h['terminal']=='replaced')
        source_census['history']['histories']=[row]
        shape=Graph().parse(data=A.shape_text(source_census),format='turtle')
        whole=URIRef(source_census['game']+'/runner-trajectory/'+row['lifetimeKey']);interval=URIRef(str(whole)+'/temporal-interval')
        person=URIRef(str(BASE)+'data/player/'+row['runnerId'])
        half=URIRef(source_census['game']+'/inning/'+row['inning']+'/'+row['half'])
        g=Graph()
        for triple in ((whole,RDF.type,BFO.BFO_0000015),(whole,BFO.BFO_0000057,person),
                       (whole,BFO.BFO_0000132,half),(whole,BFO.BFO_0000199,interval),
                       (interval,RDF.type,BFO.BFO_0000038),(person,RDF.type,CCO.ont00001262),(half,RDF.type,BASE.HalfInning)):
            g.add(triple)
        for ep in row['episodes']:
            member=URIRef(source_census['game']+'/runner-episode/'+ep['atBatIndex']+'/'+ep['runnerIndex'])
            g.add((whole,BFO.BFO_0000117,member));g.add((member,RDF.type,BASE.RunnerResolutionEpisode))
        self.assertTrue(validate(g,shacl_graph=shape)[0])
        for fault in ('member','person','interval','extra'):
            changed=Graph()
            for t in g:changed.add(t)
            if fault=='member':changed.remove((whole,BFO.BFO_0000117,None))
            elif fault=='person':changed.set((whole,BFO.BFO_0000057,URIRef(str(person)+'wrong')))
            elif fault=='interval':changed.remove((whole,BFO.BFO_0000199,None))
            else:changed.add((URIRef(source_census['game']+'/runner-trajectory/extra'),RDF.type,BFO.BFO_0000015))
            self.assertFalse(validate(changed,shacl_graph=shape)[0],fault)


if __name__=='__main__':unittest.main()
