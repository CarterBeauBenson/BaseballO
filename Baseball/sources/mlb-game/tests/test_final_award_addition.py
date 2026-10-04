"""W3's exact retained cases and their count/dependency boundaries."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from rdflib import Graph, Namespace, URIRef
from test_targeted_award_addition import W


class FinalAwardAddition(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases=W.read(W.FINAL_AWARD_CASES)['cases']
        if any(not Path(c['sourceWitness']['path']).is_file() for c in cls.cases):
            raise unittest.SkipTest('Transient W3 witnesses retired; immutable result evidence is retained by NiFi')

    def test_named_awards_keep_physical_counts_and_separate_earlier_running(self):
        sh=Namespace('http://www.w3.org/ns/shacl#');base=Namespace(W.C.B.BASE)
        for case in self.cases:
            with self.subTest(game=case['gamePk']):
                witness=case['sourceWitness'];self.assertEqual(W.sha(Path(witness['path'])),witness['sha256'])
                raw=Path(witness['path']).read_bytes();selected=W.select(raw,case['gamePk'])
                chosen=[p for p in selected if p.get('selectionDecision')==W.FINAL_AWARD_DECISION]
                self.assertEqual(len(chosen),1)
                self.assertEqual([(r['runnerIndex'],r['runnerId']) for r in chosen[0]['awardAdvances']],
                    [(str(case['runnerIndex']),str(case['runnerId']))])
                for key in ('runnerEpisodes','safeDecisionDestinations'):
                    self.assertEqual([r['runnerIndex'] for r in chosen[0][key]],[str(case['runnerIndex'])])
                pa=W.C.B.BASE+'data/game/'+case['gamePk']+'/plate-appearance/'+str(case['atBatIndex'])
                census=W.C.census(raw,case['gamePk']);count=next(p for p in census['plateAppearances'] if p['pa']==pa)
                self.assertEqual([e['playId'] for e in count['events'] if e['kind']=='pitch'],case['physicalPitchIds'])
                self.assertEqual([i for i in census['issues'] if i.get('plateAppearance')==pa],[])
                self.assertEqual(count.get('zeroPitchIntentionalWalk',False),case['gamePk']=='823350')
                if case['gamePk']=='823048':self.assertEqual([e['kind'] for e in count['events']],['award','pitch'])
                shapes=Graph().parse(data=W.shapes(case['gamePk'],chosen),format='turtle')
                nodes=list(shapes.subjects(sh.targetNode,URIRef(pa+'/result')))
                self.assertEqual({c for n in nodes for c in shapes.objects(n,sh['class'])},
                    {base[W.C.B.RESULTS[case['result']]]})

    def test_w3_never_selects_a_changed_response_or_reacquires_missing_input(self):
        case=next(c for c in self.cases if c['gamePk']=='823523')
        doc=W.read(Path(case['sourceWitness']['path']));doc['irrelevantChangedRevision']=True
        self.assertEqual(W.select(json.dumps(doc).encode(),case['gamePk']),[])
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);(state/'pipeline/evidence/nifi/game-promotion/823523').mkdir(parents=True)
            request=state/'cases.json';case={**case,'sourceWitness':dict(path=str(state/'missing.json'),sha256=case['sourceWitness']['sha256'])}
            W.atomic(request,dict(cases=[case]))
            with patch.object(W,'FINAL_AWARD_CASES',request),patch.object(W.urllib.request,'urlopen') as acquire:
                self.assertIsNone(W.final_award_witness(state));acquire.assert_not_called()
            result=W.read(state/'pipeline/control/mlb-game/award-addition/823523.json')
            self.assertEqual(result['status'],'failed');self.assertEqual(result['attempts'],2)


if __name__=='__main__':unittest.main()
