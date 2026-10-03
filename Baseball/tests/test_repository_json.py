"""Repository JSON parsing preserves Windows-produced evidence bytes."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

PATH=Path(__file__).resolve().parents[1]/'scripts/validate_repository.py'
SPEC=importlib.util.spec_from_file_location('repository_json',PATH)
V=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(V)


class RepositoryJson(unittest.TestCase):
    def test_bom_is_read_without_rewriting_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);path=root/'evidence.json'
            original=b'\xef\xbb\xbf{"value": 1}\r\n';path.write_bytes(original)
            with patch.object(V,'ROOT',root):self.assertEqual(V.validate_json(),1)
            self.assertEqual(path.read_bytes(),original)

    def test_invalid_json_still_fails_and_names_its_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'broken.json').write_bytes(b'\xef\xbb\xbf{"value":')
            with patch.object(V,'ROOT',root),self.assertRaisesRegex(ValueError,'broken.json'):
                V.validate_json()


if __name__=='__main__':unittest.main()
