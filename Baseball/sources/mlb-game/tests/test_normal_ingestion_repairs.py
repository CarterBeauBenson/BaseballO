"""Production context + production RML, using different synthetic game identities.

No repair worker, named repair inventory, API request or graph-store mutation.
Checked-in raw witnesses remain unchanged; only temporary test copies change IDs.
"""
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from rdflib import Graph, Namespace, RDF, URIRef
from pyshacl import validate

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tests'))
from test_rmlmapper_iterator_compatibility import installed_tools,materialized_subset,RR
CONTEXT=ROOT/'scripts/pipeline/prepare-rml-context.py'
MAPPING=ROOT/'sources/mlb-game/mapping/mlb-game.rml.ttl'
BFO=Namespace('http://purl.obolibrary.org/obo/')
CCO=Namespace('https://www.commoncoreontologies.org/')
BASE=Namespace('https://baseballontology.org/')
spec=importlib.util.spec_from_file_location('normal_history_shapes',ROOT/'sources/mlb-game/pipeline/runner-history-admission.py')
H=importlib.util.module_from_spec(spec);spec.loader.exec_module(H)
spec=importlib.util.spec_from_file_location('normal_proof_evidence',ROOT/'sources/mlb-game/pipeline/admission-evidence.py')
E=importlib.util.module_from_spec(spec);spec.loader.exec_module(E)
CASES={'placement':('2026-07-28','823350'),'pitcher':('2026-08-21','823420'),'review':('2026-07-19','823523')}

def pa(doc,index):return next(p for p in doc['liveData']['plays']['allPlays'] if p['atBatIndex']==index)

class NormalIngestionRepairs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary=tempfile.TemporaryDirectory(prefix='baseballo-normal-rml-')
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.documents={};cls.workspaces={};cls.inputs={}
        for name,(day,pk) in CASES.items():
            path=ROOT/'data/raw/samples'/day/(pk+'.json');raw=path.read_bytes()
            doc=json.loads(raw);doc['gamePk']=int(pk)+9000000
            if 'pk' in doc['gameData']['game']:doc['gameData']['game']['pk']=doc['gamePk']
            workspace=Path(cls.temporary.name)/name;workspace.mkdir()
            (workspace/'game.json').write_text(json.dumps(doc),encoding='utf-8')
            subprocess.run([sys.executable,'-B',str(CONTEXT),str(workspace/'game.json'),str(workspace/'complete.json')],
                check=True,capture_output=True,timeout=60)
            cls.documents[name]=json.loads((workspace/'complete.json').read_bytes())
            cls.workspaces[name]=workspace;cls.inputs[path]=raw

    @classmethod
    def tearDownClass(cls):
        for path,raw in cls.inputs.items():
            if path.read_bytes()!=raw:raise AssertionError('Raw witness was modified: '+str(path))

    def mapped(self,name,pa_ids,halves=()):
        doc=copy.deepcopy(self.documents[name]);history=doc['_baseballO']['runnerHistoryReconciliation']
        history['histories']=[h for h in history['histories'] if (int(h['inning']),h['half']) in halves]
        keys={h['lifetimeKey'] for h in history['histories']}
        history['episodeMembership']=[r for r in history['episodeMembership'] if r['lifetimeKey'] in keys]
        history['placementAdjudications']=[r for r in history['placementAdjudications'] if r['lifetimeKey'] in keys]
        selected=set(pa_ids)|{int(e['atBatIndex']) for h in history['histories'] for e in h['episodes']}
        doc['liveData']['plays']['allPlays']=[p for p in doc['liveData']['plays']['allPlays'] if p['atBatIndex'] in selected]
        # Keep this a bounded fixture. These unrelated root collections are
        # populated by the normal builder, but not needed for these assertions.
        for key in ('metricPitchReviews','metricAutomaticAwards','defensiveActs','compoundDoublePlayParts'):
            doc['_baseballO'][key]=[]
        workspace=self.workspaces[name]
        (workspace/'game-context.json').write_text(json.dumps(doc),encoding='utf-8')
        maps=Graph().parse(MAPPING)
        mapping=materialized_subset(maps,list(maps.subjects(RDF.type,URIRef(RR+'TriplesMap'))),workspace)
        java,mapper=installed_tools();output=workspace/'normal-ingestion.ttl'
        result=subprocess.run([str(java),'-Xmx256m','-jar',str(mapper),'-m',str(mapping),'-o',str(output),
            '-s','turtle','-b','https://baseballontology.org/mapping/mlb-direct','--strict'],
            cwd=workspace,capture_output=True,timeout=90)
        self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace')[-3000:])
        graph=Graph().parse(output);game=BASE+'data/game/'+str(doc['gamePk'])
        shapes=Graph().parse(data=H.shape_text(dict(game=game,history=history)),format='turtle')
        conforms,_,report=validate(graph,shacl_graph=shapes)
        self.assertTrue(conforms,report)
        return doc,graph,game

    def test_placement_is_not_a_physical_start_state(self):
        doc=self.documents['placement']
        self.assertEqual(pa(doc,85)['_baseballO']['startBaseOccupancies'],[])
        self.assertTrue(any(p['_baseballO']['startBaseOccupancies'] for p in doc['liveData']['plays']['allPlays']))
        histories=doc['_baseballO']['runnerHistoryReconciliation']['histories']
        self.assertEqual(len([h for h in histories if h['inning']=='10' and h['half']=='top']),5)

    def test_main_only_fix_keeps_existing_census_proofs_and_producers(self):
        record=E.read(E.COMPATIBILITY_PATH);bridge=record['normalIngestionPlacement']
        before=subprocess.check_output(['git','-C',str(ROOT.parent),'show',
            bridge['baselineCommit']+':Baseball/scripts/pipeline/prepare-rml-context.py'])
        def outside_main(code):
            tree=ast.parse(code);tree.body=[n for n in tree.body if getattr(n,'name',None)!='main']
            return ast.dump(tree)
        completed=subprocess.check_output(['git','-C',str(ROOT.parent),'show',
            record['q6NormalIngestion']['baselineCommit']+':Baseball/scripts/pipeline/prepare-rml-context.py'])
        self.assertEqual(outside_main(before),outside_main(completed))
        self.assertEqual(hashlib.sha256(before).hexdigest(),bridge['previousContextSha256'])
        self.assertEqual(hashlib.sha256(completed).hexdigest(),bridge['currentContextSha256'])
        bridge=record['q6NormalIngestion']
        self.assertEqual(E.sha(CONTEXT),bridge['currentContextSha256'])
        for family,item in bridge['families'].items():
            adapter=E.module(E.HERE/(family+'-admission.py'),'normal_proof_'+family.replace('-','_'))
            self.assertEqual(adapter.fingerprint(),item['currentImplementationSha256'])
            reuse=E.code_equivalence(family,item['previousImplementationSha256'],adapter.fingerprint())
            self.assertEqual(reuse['kind'],item['reuseKind'])
            entry=bridge['independentProofs'][family]
            self.assertEqual(entry['currentImplementationSha256'],E.EXISTING_GRAPH.fingerprint(E,adapter))
            self.assertEqual(entry['previous'][0]['previousSourceProducerSha256'],item['previousImplementationSha256'])
        adapter=E.module(E.HERE/'runner-boundary-admission.py','normal_boundary_reuse')
        with tempfile.TemporaryDirectory() as directory:
            state=Path(directory);promotion=dict(gamePk='1',promotionManifestSha256='promotion')
            prior=bridge['independentProofs']['runner-boundary']['previous'][0]
            path=E.refresh_path(state,promotion,'b2',prior['previousImplementationSha256'])
            E.atomic(path.with_suffix('.receipt.json'),{});E.atomic(path,dict(status='withheld'))
            # Main is not called by the census. Even an earlier negative result
            # is reusable, but only after the unchanged receipt checks pass.
            with self.assertRaisesRegex(ValueError,'receipt changed'):
                E.EXISTING_GRAPH.load(E,state,promotion,'runner-boundary',adapter)

    def test_normal_rml_emits_placement_histories_and_final_walk_award(self):
        doc,g,game=self.mapped('placement',{85,98},{(10,'top')})
        self.assertFalse(any(g.triples((URIRef(game+'/plate-appearance/85/start-state/base/2B/stasis'),None,None))))
        self.assertEqual(len(doc['_baseballO']['runnerHistoryReconciliation']['histories']),5)
        awards=pa(doc,98)['_baseballO']['awardAdvances'];self.assertEqual(len(awards),1)
        act=URIRef(game+'/runner-act/movement/98/'+awards[0]['runnerIndex'])
        self.assertIn((URIRef(game+'/plate-appearance/98/result'),CCO.ont00001803,act),g)
        self.assertIn((URIRef(awards[0]['ruleIri']),CCO.ont00001974,act),g)

    def test_normal_rml_keeps_actual_pitchers_and_counted_foul_after_change(self):
        doc,g,game=self.mapped('pitcher',{38})
        play=pa(doc,38);before=play['playEvents'][0]
        pitch=URIRef(game+'/pitch/'+before['playId'])
        self.assertIn((pitch,BFO.BFO_0000057,BASE['data/player/690928']),g)
        self.assertIn((pitch,BFO.BFO_0000055,BASE['data/player/690928/role/pitcher']),g)
        self.assertNotIn((pitch,BFO.BFO_0000057,BASE['data/player/657571']),g)
        foul=next(e for e in play['playEvents'] if e.get('_baseballO',{}).get('isSecondCountedFoul'))
        self.assertIn((URIRef(game+'/process/strike/'+foul['playId']),RDF.type,BASE.StrikeProcess),g)

    def test_normal_rml_emits_reviewed_pickoff_histories_and_mixed_pitch_walk(self):
        doc,g,game=self.mapped('review',{34,72},{(9,'top')})
        self.assertEqual(len(doc['_baseballO']['runnerHistoryReconciliation']['histories']),2)
        award=pa(doc,34)['_baseballO']['awardAdvances'];self.assertEqual(len(award),1)
        self.assertTrue(any(e.get('isPitch') is True for e in pa(doc,34)['playEvents']))
        self.assertIn((URIRef(game+'/plate-appearance/34/result'),CCO.ont00001803,
            URIRef(game+'/runner-act/movement/34/'+award[0]['runnerIndex'])),g)

if __name__=='__main__':unittest.main()
