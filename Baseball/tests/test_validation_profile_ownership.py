"""Operational registration preserves exact ownership and pinned source contracts."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_sparql_source_scopes import ROOT,VALIDATOR


class ValidationProfileOwnership(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)
        original=json.loads((ROOT/'sources/source-modules.json').read_text(encoding='utf-8'))
        self.module=copy.deepcopy(original['modules'][0])
        self.module_root=self.root/self.module['moduleRoot']
        for key in ('schemaRoot','mappingRoot','reviewRoot'):(self.root/self.module[key]).mkdir(parents=True,exist_ok=True)
        for key in ('rml','shacl','policies'):
            for name in self.module[key]:self.write(name,'# ownership fixture\n')
        for key in ('nifiContract','nifiProvisioner'):self.write(self.module[key],'# ownership fixture\n')
        self.write(self.module['semanticStatusRecord'],(ROOT/self.module['semanticStatusRecord']).read_text(encoding='utf-8'))
        status=json.loads((ROOT/self.module['semanticStatusRecord']).read_text(encoding='utf-8'))
        self.write(status['audit'],'# Audit path fixture\n')
        self.catalog=self.write('sources/source-modules.json',json.dumps(dict(original,modules=[self.module])))
        self.write('proposals/README.md','# Proposal fixture\n')
        self.write('sources/mlb-game/shacl/metric-check.ttl','# operational check\n')
        self.record=dict(artifactType='baseballo-source-validation-profile-catalog',contractVersion=1,
                         moduleId='mlb-game',profiles=['shacl/metric-check.ttl'])
        self.save()

    def write(self,path,text):
        target=self.root/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(text,encoding='utf-8')
        return target

    def save(self):self.manifest=self.write('sources/mlb-game/pipeline/validation-profiles.json',json.dumps(self.record))

    def validate(self):
        with patch.object(VALIDATOR,'ROOT',self.root),patch.object(VALIDATOR,'SOURCE_MODULE_CATALOG',self.catalog):
            return VALIDATOR.validate_source_module_contract()

    def test_operational_profiles_have_exact_owner_without_editing_main_catalog(self):
        before=self.catalog.read_bytes()
        self.assertEqual(self.validate(),(1,{'mlb-game'}))
        self.assertEqual(self.catalog.read_bytes(),before)
        self.assertEqual(self.module['shacl'],['sources/mlb-game/shacl/authoritative.ttl'])

    def test_missing_registration_and_unregistered_extra_profile_still_fail(self):
        self.manifest.unlink()
        with self.assertRaisesRegex(ValueError,'Every active source SHACL'):self.validate()
        self.save();self.write('sources/mlb-game/shacl/forgotten.ttl','# omitted\n')
        with self.assertRaisesRegex(ValueError,'Every active source SHACL'):self.validate()

    def test_duplicate_profiles_and_duplicate_owner_across_catalogs_fail(self):
        self.record['profiles']*=2;self.save()
        with self.assertRaisesRegex(ValueError,'duplicate operational'):self.validate()
        self.record['profiles']=['shacl/metric-check.ttl','shacl/authoritative.ttl'];self.save()
        with self.assertRaisesRegex(ValueError,'owned by multiple source modules'):self.validate()

    def test_invalid_missing_foreign_or_traversing_path_fails(self):
        for value in ('shacl/missing.ttl','../mlb-other/shacl/extra.ttl','/shacl/extra.ttl',
                      'shacl/*.ttl','shacl/../mapping/mlb-game.rml.ttl'):
            with self.subTest(value=value):
                self.record['profiles']=[value];self.save()
                with self.assertRaises(ValueError):self.validate()

    def test_module_identity_and_undeclared_module_catalog_fail(self):
        self.record['moduleId']='mlb-other';self.save()
        with self.assertRaisesRegex(ValueError,'Invalid operational'):self.validate()
        self.record['moduleId']='mlb-game';self.save()
        self.write('sources/mlb-other/pipeline/validation-profiles.json',json.dumps(self.record))
        with self.assertRaisesRegex(ValueError,'declared source module'):self.validate()

    def test_operational_registration_does_not_exempt_mapping_inventory(self):
        self.write('sources/mlb-game/mapping/unregistered.rml.ttl','# still prohibited\n')
        with self.assertRaisesRegex(ValueError,'Every active source RML'):self.validate()


if __name__=='__main__':unittest.main()
