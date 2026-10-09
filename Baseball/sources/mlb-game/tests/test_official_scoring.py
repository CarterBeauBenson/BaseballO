"""EG4/EG5 source reconciliation, real RML patterns and conformance regressions."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest
from pyshacl import validate
from rdflib import Dataset, Graph, Namespace, RDF, URIRef
from test_batting_admission import fixture, ROOT, BASE, CCO, OBO

spec=importlib.util.spec_from_file_location('official_scoring_test',ROOT/'sources/mlb-game/pipeline/scoring-admission.py')
S=importlib.util.module_from_spec(spec);spec.loader.exec_module(S)
P=S.B.module(ROOT/'sources/mlb-game/pipeline/player-participation-admission.py','scoring_players')


def mapped(selected):
    """Execute the selected flat reference/constant RML expressions in memory."""
    mapping=Graph().parse(ROOT/'sources/mlb-game/mapping/mlb-game.rml.ttl')
    rr=Namespace('http://www.w3.org/ns/r2rml#');rml=Namespace('http://semweb.mmlab.be/ns/rml#')
    graph=Graph()
    def term(node,row):
        value=mapping.value(node,rr.constant)
        if value is not None:return value
        ref=mapping.value(node,rml.reference)
        if ref is not None and str(ref) in row:return URIRef(row[str(ref)])
        return None
    for name in S.MAPS:
        node=URIRef('https://baseballontology.org/mapping/mlb-direct#'+name)
        source=mapping.value(node,rml.logicalSource);iterator=str(mapping.value(source,rml.iterator))
        rows=[{}] if name=='ErrorRuleMap' else selected.get(iterator.split('.')[2].split('[')[0],[])
        sm=mapping.value(node,rr.subjectMap)
        for row in rows:
            subject=term(sm,row)
            for kind in mapping.objects(sm,rr['class']):graph.add((subject,RDF.type,kind))
            for pom in mapping.objects(node,rr.predicateObjectMap):
                value=term(mapping.value(pom,rr.objectMap),row)
                if value is not None:graph.add((subject,mapping.value(pom,rr.predicate),value))
    return graph


class OfficialScoring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw=(ROOT/'data/raw/samples/2026-07-18/824169.json').read_bytes()
        cls.document=json.loads(cls.raw)
        cls.witnesses=json.loads((ROOT/'archive/design-records/mlb-game-secondary-error-attribution/evidence.json').read_text())['witnesses']
        for witness in cls.witnesses:witness['play']['atBatIndex']=witness['atBatIndex']

    def test_actual_participation_is_separate_from_reconciled_official_credit(self):
        census=S.B.census(self.raw,'824169')
        self.assertEqual(census['status'],'reconciled',census['issues'])
        row=next(r for r in census['members'] if r['atBatIndex']==31)
        self.assertEqual(row['player'],str(BASE)+'data/player/664774')
        self.assertEqual({r['playerId'] for r in row['actualBatters']},{'572233','664774'})
        self.assertEqual(len(S.S.pa_rows(census)),1)
        changed=copy.deepcopy(self.document)
        people=changed['liveData']['boxscore']['teams']['home']['players']
        people['ID664774']['stats']['batting']['plateAppearances']-=1
        people['ID572233']['stats']['batting']['plateAppearances']+=1
        self.assertEqual(S.S.pa_rows(S.B.census(json.dumps(changed).encode(),'824169')),[])
        play=copy.deepcopy(self.document['liveData']['plays']['allPlays'][31])
        change=next(e for e in play['playEvents'] if e.get('isSubstitution'))
        change['count']['strikes']=2;play['playEvents'][1]['count']['strikes']=2
        play['result']['eventType']='strikeout'
        self.assertEqual(S.S.pa_assignment(play,row['actualBatters']),'572233')
        play['result']['eventType']='walk'
        self.assertEqual(S.S.pa_assignment(play,row['actualBatters']),'664774')
        change['count']['balls']=3
        self.assertIsNone(S.S.pa_assignment(play,row['actualBatters']))

    def test_secondary_errors_deduplicate_and_keep_mixed_contact_visible(self):
        for witness in self.witnesses:
            rows=S.S.secondary_errors(witness['play'],witness['gamePk'],True)
            self.assertEqual(len({r['error'] for r in rows}),1)
            self.assertEqual(len(rows),3 if witness['gamePk']=='822688' else 1)
            self.assertEqual(any(r.get('contactPlay') for r in rows),witness['gamePk']=='822688')
            self.assertEqual(S.S.secondary_errors(witness['play'],witness['gamePk'],False),[])
            selected=dict(secondaryErrors=rows);graph=mapped(selected)
            for row in rows:
                graph.add((URIRef(row['resolution']),RDF.type,BASE.RunnerResolutionProcess))
                if row.get('contactPlay'):graph.add((URIRef(row['contactPlay']),RDF.type,BASE.BattedBallPlayProcess))
            shape=Graph().parse(data=S.shapes(selected),format='turtle')
            self.assertTrue(validate(graph,shacl_graph=shape,advanced=True)[0])
            graph.remove((URIRef(rows[0]['record']),CCO.ont00001808,URIRef(rows[0]['decision'])))
            self.assertFalse(validate(graph,shacl_graph=shape,advanced=True)[0])
        broken=copy.deepcopy(self.witnesses[0]['play'])
        broken['runners'][0]['credits'].append(dict(credit='f_throwing_error',player=dict(id=999)))
        self.assertEqual(S.S.secondary_errors(broken,'822700',True),[])
        primary=self.document['liveData']['plays']['allPlays'][31]
        self.assertEqual(S.S.secondary_errors(primary,'824169',True),[])  # existing PA Error, not a second error

    def test_rbi_requires_explicit_flags_and_matching_official_totals(self):
        census=S.B.census(self.raw,'824169')
        rows=S.S.rbi_rows(self.document,census,lambda p:True)
        self.assertEqual(len(rows),6)
        selected=dict(rbiCredits=rows);graph=mapped(selected)
        for row in rows:graph.add((URIRef(row['subject']),RDF.type,BASE.RunProcess))
        self.assertTrue(validate(graph,shacl_graph=Graph().parse(data=S.shapes(selected),format='turtle'),advanced=True)[0])
        changed=copy.deepcopy(self.document)
        next(r for p in changed['liveData']['plays']['allPlays'] for r in p['runners'] if r['details'].get('rbi'))['details']['rbi']=False
        self.assertEqual(S.S.rbi_rows(changed,census,lambda p:True),[])
        self.assertEqual(S.S.rbi_rows(self.document,census,lambda p:False),[])

    def test_two_actual_batters_have_one_official_pa_in_source_owned_shacl(self):
        source,graph=fixture();row=source['members'][0];pa=row['pa'];player2=source['roster'][1]['player']
        row.update(officialCredit=True,actualBatters=[dict(playerId='1',actIri=pa+'/batter-act'),dict(playerId='2',actIri=pa+'/batter-act/2')])
        role=URIRef(player2+'/role/batter');act=URIRef(pa+'/batter-act/2')
        for triple in [(act,RDF.type,BASE.BatterAct),(act,OBO.BFO_0000132,URIRef(pa)),
                       (act,OBO.BFO_0000055,role),(role,RDF.type,BASE.BatterRole),(role,OBO.BFO_0000197,URIRef(player2))]:graph.add(triple)
        selected=dict(officialPACredits=[S.S.credit_row(pa,row['player'],'official-pa-credit',pa)])
        shape=Graph().parse(data=S.B.shape_text(source),format='turtle')
        self.assertFalse(validate(graph,shacl_graph=shape,advanced=True)[0])
        graph+=mapped(selected)
        self.assertTrue(validate(graph,shacl_graph=shape,advanced=True)[0])
        _,report,_=validate(graph,shacl_graph=Graph().parse(data=P.shape_text(source),format='turtle'),advanced=True)
        result=P.outcome(source,report)
        self.assertEqual([p['status'] for p in result['players']],['admitted','admitted'])
        self.assertEqual(result['eligiblePlayers'],[row['player']])
        metric=S.B.module(ROOT/'serving/metric_suite.py','official_scoring_metric_query')
        dataset=Dataset();graph_iri='https://w3id.org/baseball/graph/game/1'
        target=dataset.graph(URIRef(graph_iri))
        for triple in graph:target.add(triple)
        answers=json.loads(dataset.query(metric.evidence_query([graph_iri])).serialize(format='json'))
        bindings=metric.normalize_bindings(answers['results']['bindings'],[graph_iri])
        turns=[r for r in bindings if r['kind']=='plate_appearance' and r.get('recognizedBattingResult')=='true']
        self.assertEqual({r['player'] for r in turns},{row['player'],player2})
        self.assertEqual({r['creditedPlayer'] for r in turns},{row['player']})
        graph.add((URIRef(selected['officialPACredits'][0]['decision']),CCO.ont00001808,URIRef(player2)))
        self.assertFalse(validate(graph,shacl_graph=Graph().parse(data=S.shapes(selected),format='turtle'),advanced=True)[0])

    def test_compatibility_keeps_only_prior_positive_expanded_selections(self):
        e=S.B.module(ROOT/'sources/mlb-game/pipeline/admission-evidence.py','eg45_compatibility_test')
        bridge=e.read(e.COMPATIBILITY_PATH)['emptyGameScoringCompletion']
        self.assertEqual(e.sha(ROOT/'scripts/pipeline/prepare-rml-context.py'),bridge['currentContextSha256'])
        for family,entry in bridge['families'].items():
            adapter=e.module(e.HERE/(family+'-admission.py'),'eg45_'+family)
            self.assertEqual(adapter.fingerprint(),entry['currentImplementationSha256'])
            self.assertEqual(e.code_equivalence(family,entry['previousImplementationSha256'],adapter.fingerprint())['kind'],entry['reuseKind'])
            self.assertIsNone(e.code_equivalence(family,'unknown',adapter.fingerprint()))


if __name__=='__main__':unittest.main()
