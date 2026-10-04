"""Query syntax validation has no separate fixed inventory quota."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from Baseball.tests.test_repository_json import V


class RepositorySparql(unittest.TestCase):
    def test_accepted_agent_query_is_valid_and_retired_runner_identity_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);queries=root/'sparql';queries.mkdir();path=queries/'agents.rq'
            path.write_text('PREFIX cco: <https://www.commoncoreontologies.org/>\n'
                'SELECT ?runner WHERE { ?act cco:ont00001833 ?runner }',encoding='utf-8')
            with patch.object(V,'ROOT',root),patch.object(V,'SPARQL_ROOT',queries),patch.object(V,'QUERY_BUILDERS',[]):
                V.validate_query_contract()
                path.write_text('ASK { <urn:runner-act/advance/1> ?p ?o }',encoding='utf-8')
                with self.assertRaisesRegex(ValueError,'outcome-specific runner identity'):
                    V.validate_query_contract()

    def test_all_discovered_queries_are_parsed_and_bad_query_names_its_path(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);queries=root/'sparql';queries.mkdir()
            (queries/'one.rq').write_text('ASK { ?s ?p ?o }',encoding='utf-8')
            (queries/'new-category').mkdir()
            added=queries/'new-category/two.rq'
            added.write_text('SELECT ?s WHERE { ?s ?p ?o }',encoding='utf-8')
            with patch.object(V,'ROOT',root),patch.object(V,'SPARQL_ROOT',queries):
                self.assertEqual(V.validate_sparql(),2)
                added.write_text('SELECT broken',encoding='utf-8')
                with self.assertRaisesRegex(ValueError,'two.rq'):V.validate_sparql()


if __name__=='__main__':unittest.main()
