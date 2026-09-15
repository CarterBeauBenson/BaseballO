"""E1/C1 accounted operative review effects and Q4 batter-only changes."""
import copy
import json
import unittest

from test_runner_structural_patterns import CONTEXT, ROOT


class RunnerHistoryEffects(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw=(ROOT/'data/raw/samples/2026-07-20/824087.json').read_bytes()
        cls.doc=json.loads(cls.raw)

    def changed(self, mutate):
        doc=copy.deepcopy(self.doc);mutate(doc)
        return CONTEXT.personal_runner_histories(json.dumps(doc).encode())

    def half(self,result,inning,half):
        return next(h for h in result['halves'] if h['inning']==inning and h['half']==half)

    def test_completed_affirmation_and_overturn_keep_all_seven_scoring_histories(self):
        result=CONTEXT.personal_runner_histories(self.raw)
        self.assertEqual(len(result['histories']),21)
        self.assertEqual(sum(h['terminal']=='score' for h in result['histories']),7)
        self.assertEqual(len(result['episodeMembership']),37)
        self.assertEqual(self.half(result,1,'top')['status'],'reconciled')
        self.assertEqual(self.half(result,4,'bottom')['status'],'reconciled')
        self.assertFalse(result['metricPopulationAdmitted'])
        self.assertEqual((ROOT/'data/raw/samples/2026-07-20/824087.json').read_bytes(),self.raw)

    def test_pending_unknown_or_inconsistent_pitch_review_withholds_affected_half(self):
        for fault in ('pending','outcome','call','count','mechanism'):
            def mutate(doc):
                event=doc['liveData']['plays']['allPlays'][32]['playEvents'][1]
                if fault=='pending':event['reviewDetails']['inProgress']=True
                elif fault=='outcome':event['reviewDetails'].pop('isOverturned')
                elif fault=='call':event['details']['isBall']=True
                elif fault=='count':event['count']['strikes']=0
                else:event['reviewDetails']['reviewType']='unknown'
            result=self.changed(mutate)
            self.assertEqual(self.half(result,4,'bottom')['status'],'withheld',fault)
            self.assertEqual(self.half(result,9,'bottom')['status'],'reconciled',fault)

    def test_narrative_and_structured_review_conflict_is_not_resolved_by_final_status(self):
        result=self.changed(lambda doc:doc['liveData']['plays']['allPlays'][1]['reviewDetails'].update(isOverturned=False))
        self.assertEqual(self.half(result,1,'top')['status'],'withheld')

    def test_resolved_operative_walk_keeps_accepted_award_without_original_call_inference(self):
        play=copy.deepcopy(self.doc['liveData']['plays']['allPlays'][1])
        result=CONTEXT.runner_metric_evidence(play,'1','2026')
        self.assertEqual(len(result['awardAdvances']),1)
        play['reviewDetails']['inProgress']=True
        self.assertEqual(CONTEXT.runner_metric_evidence(play,'1','2026')['awardAdvances'],[])

    def test_field_review_does_not_take_the_pitch_effect_path(self):
        play=copy.deepcopy(self.doc['liveData']['plays']['allPlays'][1])
        play['result']['description']=play['result']['description'].replace('pitch result','tag play')
        self.assertIn('UNRESOLVED_PA_REVIEW',CONTEXT.accounted_runner_count_reviews(play)['issues'])

    def test_pinch_runner_still_requires_its_own_personal_lifetime(self):
        result=CONTEXT.personal_runner_histories(self.raw)
        self.assertEqual(self.half(result,7,'bottom')['status'],'withheld')
        self.assertTrue(any(i['code']=='UNSUPPORTED_EVENT_EFFECT:offensive_substitution'
                            for i in self.half(result,7,'bottom')['issues']))

    def test_intermediate_steal_keeps_its_existing_episode_without_a_new_lifetime_anchor(self):
        result=CONTEXT.personal_runner_histories(self.raw)
        self.assertEqual(self.half(result,5,'top')['status'],'reconciled')
        runner=next(h for h in result['histories'] if h['runnerId']=='691740' and h['inning']=='5')
        self.assertEqual(runner['terminal'],'stranded')
        self.assertEqual(len(runner['episodes']),2)
        self.assertNotEqual(runner['entryAnchor'],runner['terminationAnchor'])
        # Entry and termination still require positive stable anchors.
        result=self.changed(lambda d:d['liveData']['plays']['allPlays'][36]['playEvents'][-1].pop('playId'))
        self.assertEqual(self.half(result,5,'top')['status'],'withheld')

    def test_explicit_batter_only_replacement_does_not_destroy_runner_history(self):
        raw=(ROOT/'data/raw/samples/2026-08-23/824315.json').read_bytes()
        result=CONTEXT.personal_runner_histories(raw)
        self.assertEqual(self.half(result,6,'bottom')['status'],'reconciled')
        doc=json.loads(raw)
        change=doc['liveData']['plays']['allPlays'][53]['playEvents'][0]
        change['position']['abbreviation']='PR'
        result=CONTEXT.personal_runner_histories(json.dumps(doc).encode())
        self.assertEqual(self.half(result,6,'bottom')['status'],'withheld')


if __name__=='__main__':unittest.main()
