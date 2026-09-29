"""Exact existing C2 membership, isolated by PA rather than by game."""
import copy
import importlib.util
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

    def test_later_retained_witness_keeps_its_distinct_source_identity(self):
        from test_admission_evidence import E
        raw=(ROOT/'data/raw/game-566279.json').read_bytes()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source_path=root/'retained.json';source_path.write_bytes(raw)
            proof_path=root/'c2.json';E.atomic(proof_path.with_suffix('.source.json'),P.R.census(raw,'566279'))
            witness=dict(kind='retained-source-response',path=str(source_path),sha256=E.sha(source_path))
            proof=dict(sourceSha256=witness['sha256'],retainedSourceEvidence=witness)
            promotion=dict(gamePk='566279',rawSha256='different-original-input')
            with patch.object(E,'checked_marker',return_value={}), \
                 patch.object(E.EXISTING_GRAPH,'load',return_value=proof), \
                 patch.object(E.EXISTING_GRAPH,'path_for',return_value=proof_path):
                source,_=P.retained_source(E,root,promotion)
                self.assertEqual(source['resolution']['sourceSha256'],witness['sha256'])
                self.assertEqual(source['batting']['sourceSha256'],witness['sha256'])
                self.assertNotEqual(source['batting']['sourceSha256'],promotion['rawSha256'])
                source_path.write_bytes(raw+b' ')
                with self.assertRaisesRegex(ValueError,'witness changed'):P.retained_source(E,root,promotion)


if __name__=='__main__':unittest.main()
