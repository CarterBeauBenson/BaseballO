"""Count-query equivalence, including missing and incorrectly identified graphs."""
import importlib.util
from pathlib import Path
import unittest

from rdflib import Dataset, Literal, Namespace, RDF, URIRef

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('preflight', ROOT/'scripts/pipeline/serving_preflight_queries.py')
Q = importlib.util.module_from_spec(spec)
spec.loader.exec_module(Q)
IDX = Namespace('https://w3id.org/baseball/query-index/')


def record(identifier):
    value = str(identifier)
    return dict(gamePk=value, authoritativeGraph=Q.SOURCE+value, queryIndexGraph=Q.INDEX+value,
                gameIri=Q.GAME+value, queryIndexResource=Q.RESOURCE+value)


def reference(records, index=False):
    # The previous production grouped queries are the independent oracle.
    if not index:
        values = ' '.join(f"(<{r['authoritativeGraph']}> <{r['gameIri']}>)" for r in records)
        return '''SELECT ?sourceGraph ?game (COUNT(?sourceObject) AS ?sourceCount) WHERE {
            VALUES (?sourceGraph ?game) { %s }
            GRAPH ?sourceGraph { ?sourceSubject ?sourcePredicate ?sourceObject }
        } GROUP BY ?sourceGraph ?game ORDER BY ?sourceGraph''' % values
    values = ' '.join('(<%s> <%s> <%s> <%s>)' % tuple(r[k] for k in
        ('queryIndexGraph', 'authoritativeGraph', 'gameIri', 'queryIndexResource')) for r in records)
    return '''PREFIX idx: <https://w3id.org/baseball/query-index/>
        SELECT ?indexGraph ?sourceGraph ?game ?indexResource (COUNT(?indexObject) AS ?indexCount) WHERE {
            VALUES (?indexGraph ?sourceGraph ?game ?indexResource) { %s }
            GRAPH ?indexGraph { ?indexSubject ?indexPredicate ?indexObject }
            FILTER EXISTS { GRAPH ?indexGraph {
                ?indexResource a idx:QueryIndex ; idx:sourceGraph ?sourceGraph ; idx:indexedGame ?game .
            } }
        } GROUP BY ?indexGraph ?sourceGraph ?game ?indexResource ORDER BY ?indexGraph''' % values


class FixedGraphCounts(unittest.TestCase):
    def setUp(self):
        self.dataset = Dataset()
        self.records = [record(i) for i in (1, 2, 3)]
        for i in (1, 2, 9):
            row = record(i)
            graph = self.dataset.graph(URIRef(row['authoritativeGraph']))
            graph.add((URIRef(row['gameIri']), RDF.type, URIRef('urn:test:Game')))
            graph.add((URIRef(row['gameIri']), URIRef('urn:test:value'), Literal(i)))
            index = self.dataset.graph(URIRef(row['queryIndexGraph']))
            resource = URIRef(row['queryIndexResource'])
            index.add((resource, RDF.type, IDX.QueryIndex))
            index.add((resource, IDX.sourceGraph, URIRef(row['authoritativeGraph'])))
            index.add((resource, IDX.indexedGame, URIRef(row['gameIri'])))
        self.dataset.default_context.add((URIRef('urn:default'), RDF.type, URIRef('urn:test:Game')))

    def rows(self, query):
        return [tuple(row) for row in self.dataset.query(query)]

    def test_exact_bindings_preserve_missing_graphs_and_ignore_unselected_graphs(self):
        for index, factory in ((False, Q.source_counts), (True, Q.index_counts)):
            with self.subTest(index=index):
                expected = self.rows(reference(self.records, index))
                self.assertEqual(self.rows(factory(self.records)), expected)
                self.assertEqual(len(expected), 2)
                self.assertEqual([int(row[-1]) for row in expected], [3, 3] if index else [2, 2])

    def test_wrong_or_incomplete_index_identity_is_not_counted(self):
        row = record(2)
        graph = self.dataset.graph(URIRef(row['queryIndexGraph']))
        resource = URIRef(row['queryIndexResource'])
        for predicate in (RDF.type, IDX.sourceGraph, IDX.indexedGame):
            with self.subTest(predicate=predicate):
                original = list(graph.triples((resource, predicate, None)))
                graph.remove((resource, predicate, None))
                graph.add((resource, predicate, URIRef('urn:wrong')))
                expected = self.rows(reference(self.records, True))
                self.assertEqual(self.rows(Q.index_counts(self.records)), expected)
                self.assertEqual(len(expected), 1)
                graph.remove((resource, predicate, None))
                for triple in original:
                    graph.add(triple)

    def test_empty_population_has_no_zero_count_row(self):
        for factory in (Q.source_counts, Q.index_counts):
            self.assertEqual(self.rows(factory([record(3)])), [])

    def test_invalid_duplicate_and_cross_game_scope_rejected(self):
        bad = record(1)
        bad['queryIndexGraph'] = Q.INDEX+'2'
        injected = record('1> } UNION { ?s ?p ?o')
        for records in ([], [record(1)]*2, [record(i) for i in range(201)], [bad], [injected]):
            for factory in (Q.source_counts, Q.index_counts):
                with self.subTest(records=len(records), factory=factory.__name__):
                    with self.assertRaises(ValueError):
                        factory(records)


if __name__ == '__main__':
    unittest.main()
