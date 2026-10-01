"""Category repairs over immutable MLB witnesses; no graph or network execution."""
import copy
import json
import unittest
from test_runner_structural_patterns import CONTEXT, ROOT


def source(game):
    return json.loads(next((ROOT/'data/raw/samples').glob('*/'+str(game)+'.json')).read_bytes())


def history(document):
    return CONTEXT.personal_runner_histories(json.dumps(document).encode())


class SelectionFamilies(unittest.TestCase):
    def test_administration_needs_positive_unchanged_counts_and_no_effect(self):
        cases = [(822777,'ejection'),(824398,'umpire_substitution'),(824727,'pitcher_switch'),
                 (822858,'injury'),(822705,'error'),(822699,'game_advisory')]
        for game,kind in cases:
            doc=source(game)
            p,e=next((p,e) for p in doc['liveData']['plays']['allPlays'] for e in p['playEvents']
                     if e.get('details',{}).get('eventType')==kind)
            before=copy.deepcopy(e['count']); original=copy.deepcopy(e)
            self.assertTrue(CONTEXT.runner_state_neutral_event(p,e,before),(game,kind))
            self.assertEqual(e,original)
            for fault in ('count','out','score','review','pitch','substitution'):
                changed=copy.deepcopy(e)
                if fault=='count':changed['count']['balls']+=1
                elif fault in ('out','score','review'):changed['details'][{'out':'isOut','score':'isScoringPlay','review':'hasReview'}[fault]]=True
                elif fault=='pitch':changed['isPitch']=True
                else:changed['isSubstitution']=True
                self.assertFalse(CONTEXT.runner_state_neutral_event(p,changed,before),(kind,fault))

    def test_completed_field_review_does_not_require_same_result_label(self):
        for game,pa in [(822937,4),(822946,6),(822697,72),(822707,14),(823260,93),(824077,44),(824395,17)]:
            play=source(game)['liveData']['plays']['allPlays'][pa];original=copy.deepcopy(play)
            self.assertFalse(CONTEXT.accounted_runner_history_reviews(play)['issues'],(game,pa))
            self.assertEqual(play,original)
            for fault in ('pending','disposition','unknown-code'):
                bad=copy.deepcopy(play)
                if fault=='pending':bad['reviewDetails']['inProgress']=True
                elif fault=='disposition':bad['reviewDetails']['isOverturned']=not bad['reviewDetails']['isOverturned']
                else:bad['reviewDetails']['reviewType']='UNKNOWN'
                self.assertTrue(CONTEXT.accounted_runner_history_reviews(bad)['issues'],(game,fault))
        play=source(822707)['liveData']['plays']['allPlays'][14]
        play['reviewDetails']['additionalReviews'][0]['inProgress']=True
        self.assertTrue(CONTEXT.accounted_runner_history_reviews(play)['issues'])

    def test_multi_runner_and_count_reviews_preserve_final_evidence(self):
        for game,pa in [(822939,33),(823258,43),(823438,56),(823835,7),(823998,82),
                        (824162,40),(824168,29),(824170,13),(824965,26),(825058,6)]:
            play=source(game)['liveData']['plays']['allPlays'][pa];original=copy.deepcopy(play)
            answer=CONTEXT.accounted_runner_history_reviews(play)
            self.assertFalse(answer['issues'],(game,pa))
            self.assertEqual(play,original)
            self.assertNotIn('originalDecision',json.dumps(answer))
            for e in play['playEvents']:
                if e.get('reviewDetails'):
                    e['reviewDetails']['inProgress']=True
            self.assertTrue(CONTEXT.accounted_runner_history_reviews(play)['issues'],(game,pa))

    def test_running_prefix_does_not_absorb_corrupt_count_or_movement(self):
        d=source(823835);p=d['liveData']['plays']['allPlays'][7];event=p['playEvents'][3]
        before=p['playEvents'][2]['count'];prior=before['balls'],before['strikes']
        self.assertEqual(CONTEXT.counted_foul_running_prefix(d,p,event,prior),'reconciled-running-count')
        for fault in ('association','count','score','duplicate'):
            q=copy.deepcopy(p);e=q['playEvents'][3]
            if fault=='association':e['actionPlayId']='unknown'
            elif fault=='count':e['count']['strikes']+=1
            elif fault=='score':q['runners'][0]['details']['isScoringEvent']=False
            else:q['runners'].append(copy.deepcopy(q['runners'][0]))
            self.assertIsNone(CONTEXT.counted_foul_running_prefix(d,q,e,prior),fault)

    def test_pitch_overlap_requires_independent_ordinal_and_counter(self):
        p=source(824246)['liveData']['plays']['allPlays'][52]
        a,b=p['playEvents'][2:4]
        self.assertTrue(CONTEXT.reconciled_pitch_counter_order(p,a,b))
        for fault in ('number','counter','identity','membership'):
            q=copy.deepcopy(p);a,b=q['playEvents'][2:4]
            if fault=='number':b['pitchNumber']=a['pitchNumber']
            elif fault=='counter':b['count']['balls']+=1
            elif fault=='identity':b['playId']=a['playId']
            else:a=copy.deepcopy(a)
            self.assertFalse(CONTEXT.reconciled_pitch_counter_order(q,a,b),fault)

    def test_replacement_overlap_retains_observed_clocks(self):
        doc=source(825049);original=copy.deepcopy(doc);h=history(doc)
        self.assertTrue(all(x['status']=='reconciled' for x in h['halves']))
        self.assertEqual(doc,original)
        incoming=next(x for x in h['histories'] if x['entryAnchor']=='replacement/8/bottom/571448/545121')
        self.assertEqual(incoming['entryWitness']['latestEndBound'],'2026-08-09T02:44:42.189Z')
        doc['liveData']['plays']['allPlays'][62]['playEvents'][0]['replacedPlayer']['id']=1
        self.assertTrue(any(x['status']=='withheld' for x in history(doc)['halves']))

    def test_overlap_alone_does_not_withhold_reconciled_start_state(self):
        result=history(source(823505))
        self.assertEqual(result['boundaryIssues'],[])
        self.assertEqual(len(result['reconciledPaHeaderOverlaps']),6)
        self.assertEqual(len(result['histories']),35)

    def test_actual_incomplete_evidence_stays_visible(self):
        for game,issue in [(824327,'UNSUPPORTED_RUNNER_ENTRY'),(823433,'AMBIGUOUS_RUNNER_SEGMENT_CHAIN'),
                           (824071,'MISSING_STABLE_MOVEMENT_ANCHOR'),(823840,'UNSUPPORTED_EVENT_TIME_ORDER')]:
            result=history(source(game))
            self.assertIn(issue,{i['code'] for h in result['halves'] for i in h['issues']},game)
    def test_defense_selects_final_review_and_keeps_original_description_offsets(self):
        doc=source(822946);doc['_baseballO']={'runnerHistoryReconciliation':{'sourceConsistency':'consistent'}}
        play=doc['liveData']['plays']['allPlays'][6]
        result=CONTEXT.defensive_act_context(doc)
        rows=[r for r in result['acts'] if r['atBatIndex']=='6']
        self.assertEqual(len(rows),1)
        row=rows[0]
        self.assertEqual(row['description'],play['result']['description'])
        self.assertEqual(row['description'][slice(*row['descriptionSpan'])],
                         'Junior Caminero flies out sharply to center fielder Cam Cauley.')
        for fault in ('pending','disposition','credit'):
            bad=copy.deepcopy(doc);p=bad['liveData']['plays']['allPlays'][6]
            if fault=='pending':p['reviewDetails']['inProgress']=True
            elif fault=='disposition':p['reviewDetails']['isOverturned']=not p['reviewDetails']['isOverturned']
            else:
                for runner in p['runners']:runner['credits']=[]
            self.assertFalse([r for r in CONTEXT.defensive_act_context(bad)['acts'] if r['atBatIndex']=='6'],fault)

    def test_trailing_runner_sentence_does_not_hide_named_groundout_or_claim_completeness(self):
        doc=source(822693);doc['_baseballO']={'runnerHistoryReconciliation':{'sourceConsistency':'consistent'}}
        play=doc['liveData']['plays']['allPlays'][2]
        original=play['result']['description']
        play['result']['description']+=' A runner advances to third.'
        result=CONTEXT.defensive_act_context(doc)
        rows=[r for r in result['acts'] if r['atBatIndex']=='2']
        self.assertEqual(len(rows),3)
        self.assertTrue(all(r['description'][slice(*r['descriptionSpan'])]==original for r in rows))
        self.assertFalse(next(p for p in result['plays'] if p['atBatIndex']=='2')['complete'])


if __name__=='__main__':unittest.main()
