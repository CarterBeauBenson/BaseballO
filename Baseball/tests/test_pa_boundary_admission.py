"""PA scope preserves complete dependent histories and exact C1/C2 checks."""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from pyshacl import validate
from rdflib import Graph, Literal, RDF, URIRef
from test_runner_boundary_admission import fixture, A
from runner_pattern_fixture import BASE, BFO, CCO

spec=importlib.util.spec_from_file_location('pa_boundary',A.HERE/'pa-boundary-admission.py')
P=importlib.util.module_from_spec(spec);spec.loader.exec_module(P)


class PaBoundary(unittest.TestCase):
    def test_checked_current_boundary_census_replaces_only_stale_negative_expectations(self):
        from test_admission_evidence import E
        with tempfile.TemporaryDirectory() as temporary:
            state=Path(temporary);promotion=dict(gamePk='1',promotionManifestSha256='promotion')
            path=E.refresh_path(state,promotion,'b2','checked-producer').with_suffix('.source.json')
            source=dict(gamePk='1',sourceSha256='later-source',issues=[],boundaries=[],histories=[])
            E.atomic(path,source)
            checked=dict(implementationSha256='checked-producer',sourceSha256='later-source',
                sourceCensusSha256=E.sha(path),proofSha256='checked-proof')
            old=dict(implementationSha256=P.PREVIOUS_SOURCE_SELECTION,
                plateAppearances=[dict(status='withheld')],retainedSourceEvidence=dict(sha256='original-census'))
            with patch.object(E.EXISTING_GRAPH,'load',return_value=checked),patch.object(
                    E,'checked_marker',side_effect=AssertionError('do not fall back to older expectations')):
                current,witness=P.retained_source(E,state,promotion)
                self.assertEqual(current,source)
                self.assertEqual(witness['boundaryProofSha256'],'checked-proof')
                self.assertTrue(P.needs_source_refresh(E,state,promotion,old))
                old['implementationSha256']=P.fingerprint()
                self.assertTrue(P.needs_source_refresh(E,state,promotion,old))
                old['retainedSourceEvidence']=witness
                self.assertFalse(P.needs_source_refresh(E,state,promotion,old))
                old['retainedSourceEvidence']={};old['plateAppearances'][0]['status']='admitted'
                self.assertFalse(P.needs_source_refresh(E,state,promotion,old))
                path.write_text('{}',encoding='utf-8')
                with self.assertRaisesRegex(ValueError,'census changed'):
                    P.retained_source(E,state,promotion)

    def population(self):
        graph,source=fixture();pa=source['boundaries'][0]['pa'];half=source['game']+'/inning/1/top'
        second=pa.rsplit('/',1)[0]+'/1'
        for s,p,o in list(graph):
            if str(s).startswith(pa):
                graph.add((URIRef(str(s).replace(pa,second)),p,
                    URIRef(str(o).replace(pa,second)) if isinstance(o,URIRef) and str(o).startswith(pa) else o))
        boundary=copy.deepcopy(source['boundaries'][0]);boundary['pa']=second
        boundary['occupants'][0]['stasis']=boundary['occupants'][0]['stasis'].replace(pa,second)
        source['boundaries'].append(boundary)
        return graph,source,{pa:half,second:half}

    def outcomes(self,graph,source,halves):
        text,members=P.shape_text(source,halves)
        _,report,_=validate(graph,shacl_graph=text,shacl_graph_format='turtle',advanced=True)
        failures={str(n) for n in report.objects(None,P.SH.sourceShape)}
        return {r['plateAppearance']:r['status']=='pending' and r['shape'] not in failures for r in members}

    def test_bad_boundary_is_local_but_bad_history_blocks_dependent_pas(self):
        graph,source,halves=self.population();first,second=halves
        self.assertEqual(self.outcomes(graph,source,halves),{first:True,second:True})
        graph.set((URIRef(first+'/count'),CCO.ont00001773,Literal(1)))
        self.assertEqual(self.outcomes(graph,source,halves),{first:False,second:True})
        whole=URIRef(source['game']+'/runner-trajectory/whole')
        graph.add((whole,BFO.BFO_0000117,URIRef('urn:unexpected-episode')))
        self.assertEqual(self.outcomes(graph,source,halves),{first:False,second:False})

    def test_unreconciled_sources_keep_their_full_dependency_scope(self):
        graph,source,halves=self.population();first,second=halves
        source['issues']=[dict(code='UNSUPPORTED_PA_START_BOUNDARY',detail=dict(atBatIndex=0))]
        self.assertEqual(self.outcomes(graph,source,halves),{first:False,second:True})
        source['issues']=[dict(code='INCOMPLETE_PERSONAL_HISTORIES',detail=dict(inning=1,half='bottom'))]
        self.assertEqual(self.outcomes(graph,source,halves),{first:True,second:True})
        source['issues'][0]['detail']['half']='top'
        self.assertEqual(self.outcomes(graph,source,halves),{first:False,second:False})

    def test_out_judgment_and_unexpected_occupancy_remain_required(self):
        graph,source,halves=self.population();first,second=halves
        out=URIRef('urn:out')
        for cls in (BASE.OutProcess,BASE.RunnerResolutionProcess):graph.add((out,RDF.type,cls))
        graph.add((out,BFO.BFO_0000132,URIRef(first)))
        self.assertEqual(self.outcomes(graph,source,halves),{first:False,second:False})
        graph.remove((out,None,None))
        extra=URIRef('urn:extra-stasis')
        graph.add((extra,RDF.type,BASE.PlateAppearanceStartBaserunnerAtBaseStasis))
        graph.add((extra,BFO.BFO_0000132,URIRef(first)))
        self.assertEqual(self.outcomes(graph,source,halves),{first:False,second:True})

    def test_overlapping_regions_preserve_complete_logical_boundary_but_not_unknown_history(self):
        graph,source,halves=self.population();first,second=halves
        overlap=dict(code='UNSUPPORTED_PA_START_BOUNDARY',detail=dict(code='AMBIGUOUS_PA_TIME_ORDER',
            atBatIndex=0,previousEndBound='2026-08-30T19:11:51.804+00:00',startBound='2026-08-30T19:11:48.815Z'))
        source['issues']=[overlap];before=copy.deepcopy(source)
        self.assertEqual(self.outcomes(graph,source,halves),{first:True,second:True})
        self.assertEqual(source,before)
        _,members=P.shape_text(source,halves)
        self.assertEqual(members[0]['clockOverlaps'],[overlap])
        self.assertEqual(members[0]['boundaryEvidenceDecision'],P.OVERLAP_DECISION)
        source['issues'].append(dict(code='INCOMPLETE_PERSONAL_HISTORIES',detail=dict(inning=1,half='top',
            issues=[dict(code='UNRESOLVED_REVIEW_EFFECT')])))
        self.assertEqual(self.outcomes(graph,source,halves),{first:False,second:False})
        source['issues']=[dict(code='UNSUPPORTED_PA_START_BOUNDARY',detail=dict(code='UNSUPPORTED_PA_CLOCK_PAIR',atBatIndex=0))]
        self.assertEqual(self.outcomes(graph,source,halves),{first:False,second:True})


if __name__=='__main__':unittest.main()
