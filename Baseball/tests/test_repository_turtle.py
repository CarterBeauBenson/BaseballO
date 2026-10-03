"""Syntax validation renders literal parameters only for the registered template."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from Baseball.tests.test_repository_json import V


class RepositoryTurtle(unittest.TestCase):
    def test_award_template_is_parsed_without_changing_its_bytes(self):
        relative=Path('sources/mlb-game/shacl/intentional-walk-award-addition.ttl')
        original=(V.ROOT/relative).read_bytes()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);path=root/relative;path.parent.mkdir(parents=True);path.write_bytes(original)
            with patch.object(V,'ROOT',root):self.assertEqual(V.validate_turtle(),1)
            self.assertEqual(path.read_bytes(),original)

    def test_unknown_bare_placeholder_is_rejected_with_filename(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'broken.ttl').write_text('<urn:s> <urn:p> __UNKNOWN__ .',encoding='utf-8')
            with patch.object(V,'ROOT',root),self.assertRaisesRegex(ValueError,'broken.ttl'):
                V.validate_turtle()


if __name__=='__main__':unittest.main()
