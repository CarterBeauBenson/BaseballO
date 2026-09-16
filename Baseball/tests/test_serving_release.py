"""Release isolation, exact legacy pairing and atomic reader/database selection."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('serving_release',ROOT/'scripts/pipeline/serving_release.py')
R=importlib.util.module_from_spec(spec);spec.loader.exec_module(R)
spec=importlib.util.spec_from_file_location('build_guard',ROOT/'scripts/pipeline/serving_build_guard.py')
G=importlib.util.module_from_spec(spec);spec.loader.exec_module(G)

QUERY='''import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def load_object(path):return json.loads(Path(path).read_text())
def main():
 state=Path(sys.argv[sys.argv.index('--state-root')+1])
 pointer=load_object(state/'serving/current.json')
 print(json.dumps(dict(build=pointer['buildId'],code=(ROOT/'serving/value.txt').read_text())))
 return 0
'''


class ServingRelease(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='baseballo-release-test-')
        self.addCleanup(self.tmp.cleanup)
        self.repo=Path(self.tmp.name)/'repo';self.repo.mkdir();self.state=Path(self.tmp.name)/'state'
        self.root=self.repo/'Baseball';self.pipeline=self.root/'scripts/pipeline';self.pipeline.mkdir(parents=True)
        (self.root/'serving').mkdir();(self.root/'serving/value.txt').write_text('version-one')
        (self.pipeline/'query-serving-layer.py').write_text(QUERY,newline='\n')
        (self.pipeline/'materialize-serving-layer.py').write_text('# original materializer\n',newline='\n')
        (self.pipeline/'serving_release.py').write_bytes(Path(R.__file__).read_bytes())
        self.command('init','-q');self.command('config','user.name','Release Fixture')
        self.command('config','user.email','fixture@example.invalid')
        self.commit()

    def command(self,*args):return subprocess.check_output(['git','-C',str(self.repo),*args],stderr=subprocess.PIPE)
    def commit(self):
        self.command('add','Baseball');self.command('commit','-qm','fixture')
    def capture(self):return R.capture(self.repo,self.state)
    def pointer(self,descriptor,build='one'):
        p=dict(artifactType='baseball-analytical-serving-pointer',contractVersion=5,buildId=build,runtimeRelease=descriptor)
        R.atomic(self.state/'serving/current.json',p);return p

    def test_committed_snapshot_survives_edits_and_new_commits(self):
        first=self.capture();root=R.verify_release(self.state,first)
        (self.root/'serving/value.txt').write_text('dirty-worktree')
        self.assertEqual(self.capture(),first)
        self.assertEqual((root/'serving/value.txt').read_text(),'version-one')
        self.commit();second=self.capture()
        self.assertNotEqual(first,second)
        self.assertEqual((R.verify_release(self.state,first)/'serving/value.txt').read_text(),'version-one')

    def test_build_guard_uses_snapshot_and_still_rejects_snapshot_corruption(self):
        release=self.capture();root=R.verify_release(self.state,release);p=root/'serving/value.txt'
        guard=G.BuildInputGuard(paths={'runtime':p},metric_fingerprint=lambda:R.sha(p.read_bytes()),
                               progress_path=self.state/'progress.json',build_id='fixture')
        guard.check(completed=0,total=2,phase='queries')
        (self.root/'serving/value.txt').write_text('changed-during-build')
        guard.check(completed=1,total=2,phase='queries')
        p.write_text('corrupted-release')
        with self.assertRaises(G.InputsChanged):guard.check(completed=2,total=2,phase='promotion')
        with self.assertRaisesRegex(ValueError,'file changed'):R.verify_release(self.state,release)

    def test_query_uses_published_runtime_even_when_checkout_is_broken(self):
        release=self.capture();self.pointer(release)
        (self.root/'serving/value.txt').write_text('unfinished-calculation')
        (self.pipeline/'query-serving-layer.py').write_text('invalid Python !')
        output=io.StringIO()
        with contextlib.redirect_stdout(output):code=R.dispatch(self.root,['--state-root',str(self.state)],mode='query')
        self.assertEqual(code,0);self.assertEqual(json.loads(output.getvalue()),dict(build='one',code='version-one'))
        R.verify_release(self.state,release)  # Queries must not add bytecode files.

    def test_build_launcher_runs_committed_entrypoint_with_its_release_identity(self):
        source='''import importlib.util,json
from pathlib import Path
root=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('release',root/'scripts/pipeline/serving_release.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
state=r.state_from_args(__import__('sys').argv[1:])
descriptor=r.own_descriptor(root)
assert r.verify_release(state,descriptor)==root
r.atomic(state/'built.json',dict(code=(root/'serving/value.txt').read_text(),release=descriptor))
'''
        (self.pipeline/'materialize-serving-layer.py').write_text(source,newline='\n');self.commit()
        (self.pipeline/'materialize-serving-layer.py').write_text('raise RuntimeError("moving checkout")')
        (self.root/'serving/value.txt').write_text('unfinished-edit')
        self.assertEqual(R.dispatch(self.root,['--state-root',str(self.state)],mode='build'),0)
        result=R.read(self.state/'built.json')
        self.assertEqual(result['code'],'version-one')
        R.verify_release(self.state,result['release'])

    def test_promotion_during_request_keeps_original_code_database_pair(self):
        first=self.capture();old=self.pointer(first)
        (self.root/'serving/value.txt').write_text('version-two');self.commit();second=self.capture()
        resolve=R.resolve_pointer_release
        def promote_after_read(state,pointer):
            root=resolve(state,pointer);self.pointer(second,'two');return root
        output=io.StringIO()
        with patch.object(R,'resolve_pointer_release',side_effect=promote_after_read),contextlib.redirect_stdout(output):
            self.assertEqual(R.dispatch(self.root,['--state-root',str(self.state)],mode='query'),0)
        self.assertEqual(json.loads(output.getvalue()),dict(build='one',code='version-one'))
        self.assertEqual(R.read(self.state/'serving/current.json')['buildId'],'two')

    def test_corrupt_extra_file_manifest_and_path_escape_fail_closed(self):
        descriptor=self.capture();root=R.verify_release(self.state,descriptor)
        for bad in ('../escape','a'*63,'/absolute'):
            with self.assertRaises(ValueError):R.verify_release(self.state,{**descriptor,'releaseId':bad})
        with self.assertRaisesRegex(ValueError,'manifest changed'):
            R.verify_release(self.state,{**descriptor,'manifestSha256':'0'*64})
        (root/'serving/injected.py').write_text('pass')
        with self.assertRaisesRegex(ValueError,'inventory changed'):R.verify_release(self.state,descriptor)

    def test_legacy_pairing_requires_every_recorded_runtime_hash_and_keeps_pointer(self):
        pointer=dict(artifactType='baseball-analytical-serving-pointer',contractVersion=5,buildId='legacy',
            materializerSha256=R.sha((self.pipeline/'materialize-serving-layer.py').read_bytes()),
            validationSha256=R.sha((self.pipeline/'query-serving-layer.py').read_bytes()),metricSuiteSha256='a'*64)
        R.atomic(self.state/'serving/current.json',pointer);before=(self.state/'serving/current.json').read_bytes()
        with patch.object(R,'runtime_hashes',return_value={'metricSuiteSha256':'b'*64}):
            self.assertEqual(R.prepare_legacy(self.repo,self.state)['status'],'no-exact-legacy-code-match')
        self.assertIsNone(R.resolve_pointer_release(self.state,pointer))
        with patch.object(R,'runtime_hashes',side_effect=AssertionError('must use cached non-match')):
            self.assertEqual(R.prepare_legacy(self.repo,self.state)['status'],'no-exact-legacy-code-match')
        (self.root/'serving/value.txt').write_text('new-committed-candidate');self.commit()
        with patch.object(R,'runtime_hashes',return_value={'metricSuiteSha256':'a'*64}):
            self.assertEqual(R.prepare_legacy(self.repo,self.state)['status'],'paired-legacy')
        self.assertEqual((self.state/'serving/current.json').read_bytes(),before)
        self.assertIsNotNone(R.resolve_pointer_release(self.state,pointer))
        self.assertEqual(R.prepare_legacy(self.repo,self.state)['status'],'already-paired-legacy')
        self.assertIsNone(R.resolve_pointer_release(self.state,{**pointer,'buildId':'unverified'}))

    def test_configured_state_root_is_not_appended_to(self):
        with patch.dict(os.environ,{'BASEBALLO_STATE_ROOT':str(self.state)}):
            self.assertEqual(R.state_from_args([]),self.state.resolve())


if __name__=='__main__':unittest.main()
