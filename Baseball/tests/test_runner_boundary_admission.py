"""Source completeness and exact existing boundary-graph conformance."""
import copy
import json
import unittest

from pyshacl import validate
from rdflib import Graph,Literal,URIRef,RDF,XSD
from test_metric_suite_serving import M
from runner_pattern_fixture import BASE,BFO,CCO

import importlib.util
spec=importlib.util.spec_from_file_location('boundary_admission',M.ROOT/'sources/mlb-game/pipeline/runner-boundary-admission.py')
A=importlib.util.module_from_spec(spec);spec.loader.exec_module(A)


def fixture():
    game='https://baseballontology.org/data/game/101';pa=game+'/plate-appearance/0'
    person='https://baseballontology.org/data/player/1';venue='https://baseballontology.org/data/venue/1'
    stasis=pa+'/start-state/base/3B/stasis';half=game+'/inning/1/top'
    source=dict(game=game,venue=venue,boundaries=[dict(pa=pa,outs=2,occupants=[dict(player=person,base='3B',stasis=stasis)])],
        histories=[dict(lifetimeKey='whole',runnerId='1',inning='1',half='top',episodes=[dict(atBatIndex='0',runnerIndex='0')])])
    graph=Graph()
    def add(s,p,o):graph.add((URIRef(s),p,o if isinstance(o,Literal) else URIRef(o)))
    add(game,RDF.type,BASE.BaseballGame);add(game+'/inning/1',BFO.BFO_0000132,game)
    add(half,RDF.type,BASE.HalfInning);add(half,BFO.BFO_0000132,game+'/inning/1')
    add(pa,RDF.type,BASE.PlateAppearance);add(pa,BFO.BFO_0000132,half)
    add(pa,BFO.BFO_0000199,pa+'/interval');add(pa+'/interval',RDF.type,BFO.BFO_0000038)
    add(pa+'/interval',BFO.BFO_0000222,pa+'/start')
    add(pa+'/count',RDF.type,BASE.PlateAppearanceStartOutCountICE);add(pa+'/count',CCO.ont00001808,pa)
    add(pa+'/count',CCO.ont00001773,Literal(2))
    add(person,RDF.type,CCO.ont00001262)
    add(stasis,RDF.type,BASE.PlateAppearanceStartBaserunnerAtBaseStasis);add(stasis,BFO.BFO_0000132,pa)
    add(stasis,BFO.BFO_0000057,person);add(stasis,BFO.BFO_0000057,venue+'/artifact/base/3B')
    add(stasis,CCO.ont00001918,venue+'/site/base/3B');add(stasis,BFO.BFO_0000199,stasis+'/interval')
    add(stasis+'/interval',RDF.type,BFO.BFO_0000038);add(stasis+'/interval',BFO.BFO_0000139,pa+'/interval')
    add(stasis+'/interval',BFO.BFO_0000222,pa+'/start')
    add(venue+'/artifact/base/3B',RDF.type,BASE.Base);add(venue+'/artifact/base/3B',BFO.BFO_0000171,venue+'/site/base/3B')
    add(venue+'/site/base/3B',RDF.type,BASE.BaseSite);add(venue+'/identifier',RDF.type,CCO.ont00000649)
    add(venue+'/identifier',CCO.ont00001916,venue+'/artifact/base/3B');add(venue+'/identifier',CCO.ont00001765,Literal('3B'))
    whole=game+'/runner-trajectory/whole';member=game+'/runner-episode/0/0'
    add(whole,RDF.type,BFO.BFO_0000015);add(whole,BFO.BFO_0000132,half);add(whole,BFO.BFO_0000057,person)
    add(whole,BFO.BFO_0000199,whole+'/interval');add(whole+'/interval',RDF.type,BFO.BFO_0000038)
    add(whole,BFO.BFO_0000117,member);add(member,RDF.type,BASE.RunnerResolutionEpisode)
    return graph,source


class BoundaryAdmission(unittest.TestCase):
    def test_real_source_reconciles_all_boundaries_without_modification(self):
        path=M.ROOT/'data/raw/game-566279.json';raw=path.read_bytes()
        source=A.census(raw,'566279')
        self.assertEqual(source['status'],'reconciled')
        self.assertEqual(len(source['boundaries']),79)
        self.assertEqual(len(source['histories']),31)
        self.assertEqual(path.read_bytes(),raw)
        self.assertTrue(any(b['outs']==2 and b['occupants'] for b in source['boundaries']))
        # An omitted positive post-base field cannot erase a verified runner.
        changed=json.loads(raw)
        for play in changed['liveData']['plays']['allPlays']:
            for key in ('postOnFirst','postOnSecond','postOnThird'):play['matchup'].pop(key,None)
        self.assertEqual(A.census(json.dumps(changed).encode(),'566279')['boundaries'],source['boundaries'])

    def test_unresolved_source_history_never_certifies_empty_occupancy(self):
        doc=json.loads((M.ROOT/'data/raw/game-566279.json').read_bytes())
        doc['liveData']['plays']['allPlays'][2]['playEvents'].pop()
        source=A.census(json.dumps(doc).encode(),'566279')
        self.assertEqual(source['status'],'withheld')
        self.assertTrue(source['issues'])

    def test_exact_existing_graph_and_negative_boundary_membership(self):
        graph,source=fixture()
        def conforms(g):return validate(g,shacl_graph=A.shape_text(source),shacl_graph_format='turtle',advanced=True)[0]
        self.assertTrue(conforms(graph))
        for fault in ('missing-stasis','wrong-outs','wrong-anchor','extra-stasis','missing-episode','extra-episode','wrong-person'):
            changed=Graph()
            for triple in graph:changed.add(triple)
            pa=URIRef(source['boundaries'][0]['pa']);stasis=URIRef(source['boundaries'][0]['occupants'][0]['stasis'])
            whole=URIRef(source['game']+'/runner-trajectory/whole')
            if fault=='missing-stasis':changed.remove((stasis,RDF.type,BASE.PlateAppearanceStartBaserunnerAtBaseStasis))
            elif fault=='wrong-outs':changed.set((URIRef(str(pa)+'/count'),CCO.ont00001773,Literal(1)))
            elif fault=='wrong-anchor':changed.set((URIRef(str(stasis)+'/interval'),BFO.BFO_0000222,URIRef('urn:wrong')))
            elif fault=='extra-stasis':
                changed.add((URIRef('urn:extra'),RDF.type,BASE.PlateAppearanceStartBaserunnerAtBaseStasis));changed.add((URIRef('urn:extra'),BFO.BFO_0000132,pa))
            elif fault=='missing-episode':changed.remove((whole,BFO.BFO_0000117,None))
            elif fault=='extra-episode':changed.add((whole,BFO.BFO_0000117,URIRef('urn:extra')))
            else:changed.set((whole,BFO.BFO_0000057,URIRef('urn:wrong')))
            self.assertFalse(conforms(changed),fault)


if __name__=='__main__':unittest.main()
