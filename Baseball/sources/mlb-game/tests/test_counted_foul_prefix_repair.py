"""The four recorded 822678 omissions and contradictory source mutations."""
import copy
import json
from pathlib import Path
import unittest
from test_metric_mapping_completion import CONTEXT

FIXTURE=Path(__file__).parent/'fixtures/counted-foul-prefix-822678.json'


class CountedFoulPrefixRepair(unittest.TestCase):
    def selected(self,pa,mutate=lambda p,d:None):
        doc=json.loads(FIXTURE.read_text(encoding='utf-8'))
        play=next(p for p in doc['liveData']['plays']['allPlays'] if p['atBatIndex']==pa)
        doc['liveData']['plays']['allPlays']=[play];mutate(play,doc)
        return CONTEXT.metric_pitch_context(doc)['countedFouls']

    def test_all_four_recorded_fouls_are_selected(self):
        for pa,index in [(24,3),(60,5),(63,6),(70,5)]:
            self.assertEqual([r['eventIndex'] for r in self.selected(pa)],[index])

    def test_pickoff_requires_exact_runner_out_and_attempt(self):
        for fault in ('runner','attempt','out-number','inning-end','counter','duplicate'):
            def change(p,d):
                event=p['playEvents'][2]
                row=next(r for r in p['runners'] if r['details']['playIndex']==2)
                if fault=='runner':event['player']['id']=1
                if fault=='attempt':event['actionPlayId']='absent'
                if fault=='out-number':row['movement']['outNumber']=2
                if fault=='inning-end':event['count']['outs']=3
                if fault=='counter':event['count']['balls']=1
                if fault=='duplicate':p['runners'].append(copy.deepcopy(row))
            self.assertFalse(self.selected(24,change),fault)

    def test_pinch_hitter_requires_initial_count_and_actual_agency(self):
        for fault in ('roster','agency','counter','review','invalid-clock','pitch-overlap'):
            def change(p,d):
                event=p['playEvents'][1]
                if fault=='roster':
                    side='away' if p['about']['isTopInning'] else 'home'
                    d['liveData']['boxscore']['teams'][side]['players'].pop('ID678391')
                if fault=='agency':p['playEvents'][2]['_baseballO']['batterId']='683083'
                if fault=='counter':event['count']['strikes']=1
                if fault=='review':event['details']['hasReview']=True
                if fault=='invalid-clock':event['endTime']='2026-09-26T18:00:00Z'
                if fault=='pitch-overlap':p['playEvents'][3]['startTime']=p['playEvents'][2]['startTime']
            self.assertFalse(self.selected(60,change),fault)

    def test_defensive_switch_requires_rostered_fielder_and_unchanged_count(self):
        for fault in ('roster','position','counter'):
            def change(p,d):
                event=p['playEvents'][0]
                if fault=='roster':event['player']['id']=1
                if fault=='position':event['position']['abbreviation']='PH'
                if fault=='counter':event['count']['strikes']=1
            self.assertFalse(self.selected(63,change),fault)


if __name__=='__main__':unittest.main()
