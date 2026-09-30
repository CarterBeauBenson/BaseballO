"""The same B1 constraints can pass or fail independently for each player."""
import importlib.util
import unittest
import tempfile
from pathlib import Path
from pyshacl import validate
from rdflib import Graph, RDF, URIRef
from test_batting_admission import ROOT, fixture, BASE, CCO, OBO

spec=importlib.util.spec_from_file_location('player_participation',ROOT/'sources/mlb-game/pipeline/player-participation-admission.py')
P=importlib.util.module_from_spec(spec);spec.loader.exec_module(P)
E=P.B.module(ROOT/'sources/mlb-game/pipeline/admission-evidence.py','participation_test_evidence')


class PlayerParticipation(unittest.TestCase):
    def check(self,source,graph):
        _,report,_=validate(graph,shacl_graph=Graph().parse(data=P.shape_text(source),format='turtle'),advanced=True)
        self.assertIsInstance(report,Graph)
        return P.outcome(source,report)

    def test_complete_roster_and_official_zero_pass(self):
        source,graph=fixture();result=self.check(source,graph)
        self.assertTrue(result['rosterComplete'])
        self.assertTrue(result['plateAppearanceInventoryComplete'])
        self.assertEqual([p['status'] for p in result['players']],['admitted','admitted'])

    def test_missing_result_excludes_affected_player_without_certifying_bad_record(self):
        source,graph=fixture();pa=source['members'][0]['pa']
        graph.remove((URIRef(pa+'/result'),RDF.type,BASE.WalkProcess))
        result=self.check(source,graph)
        self.assertTrue(result['rosterComplete'])
        self.assertEqual([p['status'] for p in result['players']],['withheld','admitted'])
        self.assertEqual(result['players'][0]['issues'],[dict(code='PLAYER_GRAPH_CONFORMANCE')])

    def test_k1_retained_expectation_preserves_roster_and_requires_actual_compound_graph(self):
        source,graph=fixture();row=source['members'][0];pa=row['pa']
        row.update(eventType='strikeout_double_play',resultType=str(BASE.StrikeoutProcess))
        projected=P.compound_expectations(source)
        self.assertEqual(source['members'][0]['resultType'],str(BASE.StrikeoutProcess))
        self.assertEqual(projected['roster'],source['roster'])
        self.assertEqual(projected['members'][0]['resultType'],str(BASE.DoublePlayProcess))
        self.assertEqual(projected['expectationProjection']['plateAppearances'],[pa])
        self.assertEqual(self.check(projected,graph)['players'][0]['status'],'withheld')
        graph.remove((URIRef(pa+'/result'),RDF.type,BASE.WalkProcess))
        graph.add((URIRef(pa+'/result'),RDF.type,BASE.DoublePlayProcess))
        result=self.check(projected,graph)
        self.assertTrue(result['rosterComplete'])
        self.assertTrue(all(p['status']=='admitted' for p in result['players']))

    def test_unexpected_turn_or_missing_roster_cannot_be_dropped(self):
        source,graph=fixture();extra=URIRef(source['game']+'/plate-appearance/extra')
        graph.add((extra,RDF.type,BASE.PlateAppearance))
        graph.add((extra,OBO.BFO_0000132,URIRef(source['game']+'/half')))
        result=self.check(source,graph)
        self.assertFalse(result['plateAppearanceInventoryComplete'])
        self.assertTrue(all(p['status']=='withheld' for p in result['players']))
        source,graph=fixture();player=source['roster'][1]['player']
        graph.remove((URIRef(source['game']),OBO.BFO_0000055,URIRef(player+'/team/1/role/player')))
        self.assertFalse(self.check(source,graph)['rosterComplete'])

    def test_source_issue_scope_preserves_uncertainty(self):
        source,graph=fixture();source['members'][0]['atBatIndex']=0
        source['issues']=[dict(code='OFFENSIVE_REPLACEMENT_WITHIN_TURN',atBatIndex=0)]
        result=self.check(source,graph)
        self.assertEqual([p['status'] for p in result['players']],['withheld','admitted'])
        source['issues']=[dict(code='SOURCE_RECONCILIATION')]
        self.assertTrue(all(p['status']=='withheld' for p in self.check(source,graph)['players']))

    def test_receipt_is_bound_to_graph_and_all_validation_artifacts(self):
        with tempfile.TemporaryDirectory() as temporary:
            state=Path(temporary);marker=state/'marker.json';E.atomic(marker,{'gamePk':'1'})
            promotion=dict(gamePk='1',promotionManifest=str(marker),promotionManifestSha256=E.sha(marker),
                authoritativeGraph='graph',authoritativeRdfSha256='rdf')
            path=P.proof_path(E,state,promotion)
            proof=dict(artifactType='baseballo-player-participation-admission',contractVersion=1,
                gamePk='1',graph='graph',authoritativeRdfSha256='rdf',implementationSha256=P.fingerprint())
            for suffix,key in (('.source.json','sourceCensusSha256'),('.shapes.ttl','shapeSha256'),('.report.ttl','reportSha256')):
                E.atomic(path.with_suffix(suffix),dict(artifact=key));proof[key]=E.sha(path.with_suffix(suffix))
            E.atomic(path,proof);E.atomic(path.with_suffix('.receipt.json'),dict(
                promotionManifestSha256=promotion['promotionManifestSha256'],proofSha256=E.sha(path)))
            self.assertEqual(P.load(E,state,promotion)['authoritativeRdfSha256'],'rdf')
            with self.assertRaisesRegex(ValueError,'another graph'):P.load(E,state,dict(promotion,authoritativeRdfSha256='changed'))
            E.atomic(path.with_suffix('.source.json'),dict(changed=True))
            with self.assertRaisesRegex(ValueError,'artifact changed'):P.load(E,state,promotion)


if __name__=='__main__':unittest.main()
