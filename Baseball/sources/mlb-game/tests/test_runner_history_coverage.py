"""Real C1 history coverage remains separate from uncertain PA-start bounds."""
import copy
import importlib.util
import json
import unittest
from datetime import datetime, timedelta

from test_runner_structural_patterns import CONTEXT, ROOT

spec = importlib.util.spec_from_file_location('boundary_coverage', ROOT/'sources/mlb-game/pipeline/runner-boundary-admission.py')
B = importlib.util.module_from_spec(spec); spec.loader.exec_module(B)


def source(game):
    return json.loads((ROOT/f'data/raw/samples/2026-08-25/{game}.json').read_bytes())


def histories(doc):
    return CONTEXT.personal_runner_histories(json.dumps(doc).encode())


class RunnerHistoryCoverage(unittest.TestCase):
    def test_overlapping_pa_headers_do_not_erase_independently_ordered_histories(self):
        doc=source(823505); result=histories(doc)
        self.assertTrue(all(h['status']=='reconciled' for h in result['halves']))
        self.assertEqual(len(result['histories']),35)
        self.assertEqual(sum(h['terminal']=='score' for h in result['histories']),16)
        self.assertEqual(len(result['boundaryIssues']),6)
        proof=B.census(json.dumps(doc).encode(),'823505')
        self.assertEqual(proof['status'],'withheld')
        self.assertEqual(sum(i['code']=='UNSUPPORTED_PA_START_BOUNDARY' for i in proof['issues']),6)
        self.assertFalse(result['metricPopulationAdmitted'])

    def test_actual_cross_pa_event_overlap_withholds_the_half(self):
        doc=source(823505); plays=doc['liveData']['plays']['allPlays']
        end=datetime.fromisoformat(plays[11]['playEvents'][-1]['endTime'].replace('Z','+00:00'))
        plays[12]['playEvents'][0]['startTime']=(end-timedelta(milliseconds=1)).isoformat()
        result=histories(doc)
        half=next(h for h in result['halves'] if h['inning']==plays[12]['about']['inning'] and h['half']==plays[12]['about']['halfInning'])
        self.assertEqual(half['status'],'withheld')
        self.assertIn('UNSUPPORTED_EVENT_TIME_ORDER',{i['code'] for i in half['issues']})

    def test_completed_field_review_preserves_final_history_without_original_call(self):
        for game,pa,count in ((823098,45,5),(824962,47,6)):
            doc=source(game);play=doc['liveData']['plays']['allPlays'][pa]
            before=copy.deepcopy(play)
            review=CONTEXT.accounted_runner_history_reviews(play)
            self.assertEqual(review['issues'],[])
            self.assertIn('accountedFieldReview',review)
            self.assertNotIn('originalDecision',review['accountedFieldReview'])
            self.assertEqual(play,before)
            result=histories(doc)
            self.assertTrue(all(h['status']=='reconciled' for h in result['halves']))
            self.assertEqual(sum(h['terminal']=='score' for h in result['histories']),count)
            # A field review still does not authorize the pitch-count path.
            self.assertIn('UNRESOLVED_PA_REVIEW',CONTEXT.accounted_runner_count_reviews(play)['issues'])

    def test_incomplete_or_conflicting_field_review_and_earlier_reviews_stay_unknown(self):
        for fault in ('pending','missing-disposition','conflict','wrong-kind','missing-anchor','missing-rows','unknown-out','earlier-review'):
            p=source(823098)['liveData']['plays']['allPlays'][45]
            if fault=='pending':p['reviewDetails']['inProgress']=True
            elif fault=='missing-disposition':p['result']['description']=p['result']['description'].replace(', call on the field was upheld','')
            elif fault=='conflict':p['reviewDetails']['isOverturned']=True
            elif fault=='wrong-kind':p['reviewDetails']['reviewType']='MJ'
            elif fault=='missing-anchor':p['playEvents'][-1].pop('playId')
            elif fault=='missing-rows':p['runners']=[]
            elif fault=='unknown-out':
                next(r for r in p['runners'] if r['details']['playIndex']==p['playEvents'][-1]['index'])['movement']['isOut']=None
            else:p['playEvents'][0]['details']['hasReview']=True
            self.assertTrue(CONTEXT.accounted_runner_history_reviews(p)['issues'],fault)

    def test_defensive_indifference_is_preserved_as_its_own_existing_episode(self):
        doc=source(823098); result=histories(doc)
        lifetime=next(h for h in result['histories'] if any(e['atBatIndex']=='68' and e['runnerIndex']=='0' for e in h['episodes']))
        self.assertEqual(lifetime['runnerId'],'664761')
        episode=next(e for e in lifetime['episodes'] if e['atBatIndex']=='68' and e['runnerIndex']=='0')
        self.assertEqual(episode['resolutionKind'],'advance')
        proof=B.census(json.dumps(doc).encode(),'823098')
        self.assertEqual(proof['issues'],[])
        self.assertFalse(any(a['act'].endswith('/movement/68/0') for a in proof['awards']))
        doc['liveData']['plays']['allPlays'][68]['runners'][0]['details']['playIndex']=0
        result=histories(doc)
        self.assertIn('MISSING_INDEPENDENT_MOVEMENT',{i['code'] for h in result['halves'] for i in h['issues']})

    def test_delay_requires_unchanged_count_and_no_runner_or_scoring_effect(self):
        for fault in (None,'count','out','scoring','running','review','unknown-label'):
            doc=source(824556);event=doc['liveData']['plays']['allPlays'][8]['playEvents'][0]
            if fault=='count':event['count']['balls']=1
            elif fault=='out':event['details']['isOut']=True
            elif fault=='scoring':event['details']['isScoringPlay']=True
            elif fault=='running':event['isBaseRunningPlay']=True
            elif fault=='review':event['details']['hasReview']=True
            elif fault=='unknown-label':event['details']['description']='Unknown delay.'
            result=histories(doc)
            if fault=='scoring':
                self.assertEqual(result['sourceConsistency'],'inconsistent')
                self.assertEqual(result['histories'],[])
                continue
            half=next(h for h in result['halves'] if h['inning']==1 and h['half']=='bottom')
            self.assertEqual(half['status'],'withheld' if fault else 'reconciled',fault)


if __name__=='__main__':unittest.main()
