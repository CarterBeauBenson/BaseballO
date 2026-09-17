"""Preserve the accepted substituted-batter grain through disposable indexes."""
import unittest
from rdflib import Dataset, Graph, Namespace, RDF, URIRef
from pyshacl import validate
from test_query_index_consumer_contract import ROOT, SHAPES, GRAPH_HEADER, HOME, AWAY

IDX = Namespace('https://w3id.org/baseball/query-index/')
BASE = Namespace('https://baseballontology.org/')
GAME = BASE['data/game/1']
PA = URIRef(str(GAME) + '/pa/1')
RESULT = URIRef(str(PA) + '/result')
ACTS = [URIRef(str(PA) + '/batter/' + str(i)) for i in (1, 2)]
PLAYERS = [BASE['data/player/' + str(i)] for i in (1, 2)]


def constructed(hit=False):
    dataset = Dataset()
    graph = dataset.graph(URIRef('urn:baseball:query-index:source-graph'))
    graph.parse(data='''
        @prefix base: <https://baseballontology.org/> .
        @prefix obo: <http://purl.obolibrary.org/obo/> .
        @prefix cco: <https://www.commoncoreontologies.org/> .
        @prefix d: <https://baseballontology.org/data/> .
        <https://baseballontology.org/data/game/1/pa/1> a base:PlateAppearance ;
            obo:BFO_0000132 d:half .
        d:half obo:BFO_0000132 d:inning .
        d:inning obo:BFO_0000132 <urn:baseball:query-index:game> .
        <https://baseballontology.org/data/game/1/pa/1/result>
            a base:BaseballInstitutionalProcess, base:WalkProcess ;
            obo:BFO_0000132 <https://baseballontology.org/data/game/1/pa/1> ;
            obo:BFO_0000117 d:judgment .
        d:judgment a base:BaseballAdjudicationAct .
    ''', format='turtle')
    bfo = Namespace('http://purl.obolibrary.org/obo/')
    cco = Namespace('https://www.commoncoreontologies.org/')
    if hit:
        graph.remove((RESULT, RDF.type, BASE.WalkProcess))
        graph.add((RESULT, RDF.type, BASE.SingleProcess))
        graph.add((BASE['data/judgment'], RDF.type, BASE.HitJudgmentAct))
        graph.add((RESULT, cco.ont00001918, BASE['data/field']))
        graph.add((BASE['data/field'], RDF.type, BASE.BaseballFieldSite))
        graph.add((BASE['data/field'], bfo.BFO_0000171, BASE['data/venue/1']))
    for act, player in zip(ACTS, PLAYERS):
        graph.add((act, RDF.type, BASE.BatterAct))
        graph.add((act, bfo.BFO_0000132, PA))
        graph.add((act, bfo.BFO_0000057, player))
        graph.add((player, RDF.type, cco.ont00001262))
    output = Graph().parse(data=GRAPH_HEADER + HOME + AWAY, format='turtle')
    for component in ('15-plate-appearances.rq', '20-plate-appearance-results.rq', '30-hits.rq'):
        query = (ROOT / 'sparql/query-index/components' / component).read_text()
        for s, p, o in dataset.query(query).graph:
            output.add((s, p, GAME if o == URIRef('urn:baseball:query-index:game') else o))
    return output


class BattingParticipationIndexTests(unittest.TestCase):
    def check(self, graph, expected):
        conforms, _, report = validate(graph, shacl_graph=SHAPES)
        self.assertEqual(bool(conforms), expected, str(report))

    def test_one_pa_and_result_retain_both_actual_batters(self):
        graph = constructed()
        self.check(graph, True)
        self.assertEqual(list(graph.subjects(RDF.type, IDX.PlateAppearanceFact)), [PA])
        self.assertEqual(list(graph.subjects(RDF.type, IDX.PlateAppearanceResultFact)), [RESULT])
        for fact in (PA, RESULT):
            self.assertEqual(set(graph.objects(fact, IDX.agent)), set(PLAYERS))
        for act, player in zip(ACTS, PLAYERS):
            self.assertEqual(list(graph.objects(act, IDX.agent)), [player])

    def test_no_unsupported_or_omitted_actor(self):
        for fact in (PA, RESULT):
            for operation in ('add', 'remove'):
                with self.subTest(fact=fact, operation=operation):
                    graph = constructed()
                    if operation == 'add':
                        graph.add((fact, IDX.agent, BASE['data/player/999']))
                    else:
                        graph.remove((fact, IDX.agent, PLAYERS[0]))
                    self.check(graph, False)

    def test_hit_projection_keeps_the_same_actual_participation_grain(self):
        graph = constructed(hit=True)
        self.check(graph, True)
        self.assertEqual(list(graph.subjects(RDF.type, IDX.HitFact)), [RESULT])
        self.assertEqual(set(graph.objects(RESULT, IDX.agent)), set(PLAYERS))
        graph.remove((RESULT, IDX.agent, PLAYERS[0]))
        self.check(graph, False)

    def test_support_requires_one_actor_in_the_same_pa_and_game(self):
        for predicate in (IDX.agent, IDX.plateAppearance, IDX.game):
            with self.subTest(predicate=predicate):
                graph = constructed()
                graph.add((ACTS[0], predicate, BASE['data/wrong']))
                self.check(graph, False)


if __name__ == '__main__':
    unittest.main()
