"""Exact existing C2 membership, isolated by PA rather than by game."""
import copy
import importlib.util
import json
import unittest
from unittest.mock import patch
import tempfile
from pyshacl import validate
from rdflib import Graph,Namespace,RDF,URIRef
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('pa_resolution',ROOT/'sources/mlb-game/pipeline/pa-resolution-admission.py')
P=importlib.util.module_from_spec(spec);spec.loader.exec_module(P)
BASE=Namespace('https://baseballontology.org/');BFO=Namespace('http://purl.obolibrary.org/obo/')
CCO=Namespace('https://www.commoncoreontologies.org/')


class PaResolution(unittest.TestCase):
    def fixture(self):
        game=str(BASE)+'data/game/1';graph=Graph();rows=[];pas=[game+'/plate-appearance/'+str(i) for i in range(3)]
        half,inning=URIRef(game+'/half'),URIRef(game+'/inning')
        graph.add((half,BFO.BFO_0000132,inning));graph.add((inning,BFO.BFO_0000132,URIRef(game)))
        for i,pa in enumerate(pas):
            graph.add((URIRef(pa),RDF.type,BASE.PlateAppearance));graph.add((URIRef(pa),BFO.BFO_0000132,half))
            if i==2:continue  # Verified empty resolution census still checks PA membership.
            row=dict(pa=pa,player=str(BASE)+'data/player/'+str(i),resolution=pa+'/out',act=pa+'/act',
                episode=pa+'/episode',outcome='OutProcess',stealAttempt=False,origin=None,destination=None)
            rows.append(row);resolution,act,episode=(URIRef(row[k]) for k in ('resolution','act','episode'))
            for cls in (BASE.RunnerResolutionProcess,BASE.OutProcess):graph.add((resolution,RDF.type,cls))
            graph.add((resolution,BFO.BFO_0000132,URIRef(pa)));graph.add((resolution,BFO.BFO_0000062,act))
            graph.add((act,RDF.type,BASE.BaserunningAct));graph.add((act,BFO.BFO_0000132,URIRef(pa)))
            graph.add((act,CCO.ont00001833,URIRef(row['player'])))
            graph.add((episode,RDF.type,BASE.RunnerResolutionEpisode));graph.add((episode,BFO.BFO_0000132,URIRef(pa)))
            graph.add((episode,BFO.BFO_0000117,act));graph.add((episode,BFO.BFO_0000117,resolution))
        common=dict(game=game,gamePk='1',sourceSha256='source',issues=[])
        return graph,dict(resolution=dict(common,resolutions=rows,nonMovementRecords=[]),
                          batting=dict(common,members=[dict(pa=pa) for pa in pas])),pas

    def outcomes(self,graph,source):
        text,members=P.shape_text(source)
        _,report,_=validate(graph,shacl_graph=text,shacl_graph_format='turtle',advanced=True)
        return {r['plateAppearance']:r['status'] for r in P.outcome(members,report)}

    def test_wrong_runner_and_extra_resolution_do_not_admit_bad_pa_or_block_unrelated_pa(self):
        graph,source,pas=self.fixture()
        self.assertEqual(self.outcomes(graph,source),dict.fromkeys(pas,'admitted'))
        graph.set((URIRef(pas[0]+'/act'),CCO.ont00001833,URIRef('urn:wrong-player')))
        self.assertEqual(self.outcomes(graph,source),dict(zip(pas,['withheld','admitted','admitted'])))
        extra=URIRef('urn:extra-resolution');graph.add((extra,RDF.type,BASE.RunnerResolutionProcess))
        graph.add((extra,BFO.BFO_0000132,URIRef(pas[2])))
        self.assertEqual(self.outcomes(graph,source),dict(zip(pas,['withheld','admitted','withheld'])))

    def test_unknown_source_issues_block_all_but_explicit_boundary_issue_keeps_pa_scope(self):
        graph,source,pas=self.fixture()
        source['resolution']['issues']=[dict(code='UNRESOLVED_RUNNER_BOUNDARY',atBatIndex='0')]
        self.assertEqual(self.outcomes(graph,source),dict(zip(pas,['withheld','admitted','admitted'])))
        source['resolution']['issues']=[dict(code='SOURCE_RECONCILIATION',detail=dict(atBatIndex=0))]
        self.assertEqual(self.outcomes(graph,source),dict.fromkeys(pas,'withheld'))

    def test_missing_pa_never_certifies_an_empty_census(self):
        graph,source,pas=self.fixture();graph.remove((URIRef(pas[2]),None,None))
        self.assertEqual(self.outcomes(graph,source),dict(zip(pas,['admitted','admitted','withheld'])))
        extra=copy.deepcopy(source['resolution']['resolutions'][0]);extra['pa']='urn:unknown-turn'
        source['resolution']['resolutions'].append(extra)
        self.assertEqual(self.outcomes(graph,source),dict.fromkeys(pas,'withheld'))

    def scoped_fixture(self, issues):
        graph,source,pas=self.fixture()
        raw=json.dumps(dict(liveData=dict(plays=dict(allPlays=[
            dict(atBatIndex=i,about=dict(inning=inning,halfInning=half,isComplete=complete))
            for i,(inning,half,complete) in enumerate([
                (9,'top',True),(8,'bottom',True),(9,'bottom',False)])]),
            linescore=dict(innings=[dict(num=8,away=dict(runs=0),home=dict(runs=1)),
                                   dict(num=9,away={},home={})])))).encode()
        for census in source.values():census['sourceSha256']=P.R.B.sha(raw)
        source['resolution']['issues']=issues
        return graph,P.with_reconciliation_scope(source,raw),pas,raw

    def test_missing_inning_total_and_incomplete_play_keep_exact_source_scope(self):
        issues=[dict(code='SOURCE_RECONCILIATION',detail=dict(code='INNING_RUN_TOTAL_MISMATCH',
                    path='/liveData/linescore/innings/1/away',reported=None,observedScoringRows=0)),
                dict(code='SOURCE_RECONCILIATION',detail=dict(code='INCOMPLETE_SOURCE_PLAY',
                    path='/liveData/plays/allPlays/2/about/isComplete'))]
        graph,source,pas,_=self.scoped_fixture(issues)
        self.assertEqual(self.outcomes(graph,source),dict(zip(pas,['withheld','admitted','withheld'])))
        self.assertEqual(source['resolution']['issues'],issues)  # No global completeness claim.
        # The unaffected turn still has to satisfy the unchanged exact C2 graph contract.
        graph.set((URIRef(pas[1]+'/act'),CCO.ont00001833,URIRef('urn:wrong-player')))
        self.assertEqual(self.outcomes(graph,source),dict.fromkeys(pas,'withheld'))

    def test_numeric_conflicts_unknown_issues_and_missing_locations_remain_global(self):
        details=[dict(code='INNING_RUN_TOTAL_MISMATCH',
                     path='/liveData/linescore/innings/1/away',reported=1,observedScoringRows=0),
                 dict(code='INCOMPLETE_SOURCE_PLAY',path='/liveData/plays/allPlays/99/about/isComplete'),
                 dict(code='INCOMPLETE_SOURCE_PLAY',path='/liveData/plays/allPlays/1/about/isComplete'),
                 dict(code='MOVEMENT_EVENT_MEMBERSHIP_MISMATCH',path='/liveData/plays/allPlays/0/runners/0')]
        for detail in details:
            with self.subTest(detail=detail):
                graph,source,pas,_=self.scoped_fixture([dict(code='SOURCE_RECONCILIATION',detail=detail)])
                self.assertEqual(self.outcomes(graph,source),dict.fromkeys(pas,'withheld'))

    def test_scope_cannot_use_a_different_witness_or_pa_inventory(self):
        _,source,_,raw=self.scoped_fixture([])
        with self.assertRaisesRegex(ValueError,'witness differs'):
            P.with_reconciliation_scope(source,raw+b' ')
        source['batting']['members'].reverse()
        with self.assertRaisesRegex(ValueError,'inventory differs'):
            P.with_reconciliation_scope(source,raw)

    def test_later_retained_witness_keeps_its_distinct_source_identity(self):
        from test_admission_evidence import E
        raw=(ROOT/'data/raw/game-566279.json').read_bytes()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source_path=root/'retained.json';source_path.write_bytes(raw)
            proof_path=root/'c2.json';E.atomic(proof_path.with_suffix('.source.json'),P.R.census(raw,'566279'))
            witness=dict(kind='retained-source-response',path=str(source_path),sha256=E.sha(source_path))
            proof=dict(sourceSha256=witness['sha256'],retainedSourceEvidence=witness,implementationSha256='prior-independent')
            promotion=dict(gamePk='566279',rawSha256='different-original-input')
            with patch.object(E,'checked_marker',return_value={}), \
                 patch.object(E.EXISTING_GRAPH,'load',return_value=proof), \
                 patch.object(E,'refresh_path',return_value=proof_path):
                source,_=P.retained_source(E,root,promotion)
                self.assertEqual(source['resolution']['sourceSha256'],witness['sha256'])
                self.assertEqual(source['batting']['sourceSha256'],witness['sha256'])
                self.assertNotEqual(source['batting']['sourceSha256'],promotion['rawSha256'])
                source_path.write_bytes(raw+b' ')
                with self.assertRaisesRegex(ValueError,'witness changed'):P.retained_source(E,root,promotion)
                alternate=root/'another-retained-copy.json';alternate.write_bytes(raw)
                source_path.unlink()
                recovered=dict(kind='retained-source-response',path=str(alternate),sha256=E.sha(alternate))
                with patch.object(E,'retained_raw_witness',return_value=recovered):
                    source,witnesses=P.retained_source(E,root,promotion)
                    self.assertEqual(witnesses[1]['path'],str(alternate))
                    self.assertEqual(witnesses[1]['originalWitness'],witness)

    def test_retired_raw_uses_exact_retained_batting_census_or_stays_unavailable(self):
        from test_admission_evidence import E
        _,source,_=self.fixture()
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);paths={name:state/(name+'.json') for name in ('c2','b1')}
            for name,key in (('c2','resolution'),('b1','batting')):
                E.atomic(paths[name].with_suffix('.source.json'),source[key])
            resolution=dict(sourceSha256='source',implementationSha256='c2',
                retainedSourceEvidence=dict(path=str(state/'retired.json'),sha256='source'))
            batting=dict(sourceSha256='source',implementationSha256='b1',
                sourceCensusSha256=E.sha(paths['b1'].with_suffix('.source.json')))
            def load(evidence,state,promotion,family,adapter):
                return resolution if family=='runner-resolution' else batting
            with patch.object(E,'checked_marker',return_value={}), \
                 patch.object(E,'retained_raw_witness',return_value=None), \
                 patch.object(E.EXISTING_GRAPH,'load',side_effect=load), \
                 patch.object(E,'refresh_path',side_effect=lambda state,promotion,kind,version:paths[kind]):
                retained,witnesses=P.retained_source(E,state,dict(gamePk='1'))
                self.assertEqual(retained,source)
                self.assertTrue(all(Path(w['path']).is_file() for w in witnesses))
                batting['sourceSha256']='another-response'
                self.assertIsNone(P.retained_source(E,state,dict(gamePk='1')))
                batting['sourceSha256']='source'
                E.atomic(paths['b1'].with_suffix('.source.json'),{})
                with self.assertRaisesRegex(ValueError,'census changed'):
                    P.retained_source(E,state,dict(gamePk='1'))


if __name__=='__main__':unittest.main()
