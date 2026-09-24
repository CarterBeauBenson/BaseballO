"""NiFi-owned immutable serving code releases paired with published SQL builds.

Capture committed Git objects, never a moving checkout. All original serving
and source-admission checks still run inside the selected release. Legacy
databases may acquire a sidecar only after every recorded code hash matches.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile

SCOPES = ('Baseball/scripts/pipeline', 'Baseball/serving', 'Baseball/sparql',
          'Baseball/sources/mlb-game', 'Baseball/mappings/policies', 'Baseball/shacl')
POINTER_ENV = 'BASEBALLO_PINNED_SERVING_POINTER'


def sha(data): return hashlib.sha256(data).hexdigest()
def encoded(value): return (json.dumps(value, sort_keys=True, separators=(',', ':'))+'\n').encode()
def read(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def atomic(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('wb', dir=path.parent, delete=False) as f:
        f.write(encoded(value)); f.flush(); os.fsync(f.fileno()); temporary=Path(f.name)
    try: os.replace(temporary, path)
    finally: temporary.unlink(missing_ok=True)


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.PIPE)


def safe_relative(value):
    p=PurePosixPath(value)
    if not value or '\\' in value or ':' in value or p.is_absolute() or any(x in {'','.','..'} for x in value.split('/')):
        raise ValueError('Unsafe serving release path')
    return p


def verify_release(state, descriptor):
    if not isinstance(descriptor, dict): raise ValueError('Invalid serving release descriptor')
    release_id=descriptor.get('releaseId', '')
    if not isinstance(release_id, str) or not re.fullmatch('[0-9a-f]{64}', release_id):
        raise ValueError('Invalid serving release identity')
    releases=(Path(state)/'serving/releases').resolve()
    directory=releases/release_id
    if directory.is_symlink() or directory.resolve().parent != releases: raise ValueError('Serving release escaped its directory')
    manifest=directory/'release.json'
    raw=manifest.read_bytes()
    if sha(raw)!=descriptor.get('manifestSha256'): raise ValueError('Serving release manifest changed')
    record=json.loads(raw)
    if (record.get('artifactType')!='baseballo-serving-runtime-release' or record.get('contractVersion')!=1
            or sha(encoded(record))!=release_id or record.get('sourceCommit')!=descriptor.get('sourceCommit')):
        raise ValueError('Serving release identity does not match manifest')
    root=directory/'Baseball'
    expected=record['files']
    if not isinstance(expected, dict) or not expected: raise ValueError('Serving release is empty')
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    if actual!=set(expected): raise ValueError('Serving release file inventory changed')
    identities={}
    for name in expected:
        p=root.joinpath(*safe_relative(name).parts)
        if p.is_symlink() or not p.resolve().is_relative_to(root.resolve()):
            raise ValueError('Serving release file escaped its directory: '+name)
        st=p.stat()
        identities[name]=[st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns]
    receipt=Path(state)/'serving/release-verification'/(release_id+'.json')
    identity=dict(manifestSha256=sha(raw),files=identities)
    try:
        if read(receipt)==identity: return root
    except (OSError,ValueError): pass
    for name, digest in expected.items():
        p=root.joinpath(*safe_relative(name).parts)
        if p.is_symlink() or not p.resolve().is_relative_to(root.resolve()) or sha(p.read_bytes())!=digest:
            raise ValueError('Serving release file changed: '+name)
    # Same local-file receipt policy as immutable serving databases. Replaced,
    # edited, added or removed files still invalidate the prior verification.
    for name, before in identities.items():
        st=(root/name).stat()
        if [st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns]!=before:
            raise ValueError('Serving release changed while verifying: '+name)
    try: atomic(receipt,identity)
    except OSError: pass  # Read-only installations remain correct, just slower.
    return root


def capture(repo, state, revision='HEAD'):
    repo=Path(repo).resolve(); state=Path(state).resolve()
    commit=git(repo,'rev-parse','--verify',revision+'^{commit}').decode().strip()
    if not re.fullmatch('[0-9a-f]{40}',commit): raise ValueError('Invalid committed serving revision')
    names=git(repo,'ls-tree','-r','--name-only',commit,'Baseball').decode().splitlines()
    selected=[n for n in names if any(n.startswith(s+'/') for s in SCOPES)
              or (n.startswith('Baseball/data/raw/samples/') and n.endswith('/schedule.json'))]
    # Exclude developer fixtures and documentation, keeping every executable
    # and declarative runtime dependency from the declared source boundaries.
    selected=[n for n in selected if '/tests/' not in n and '/fixtures/' not in n
              and not n.endswith(('.md','.png','.svg'))]
    if not selected: raise ValueError('No committed serving files')
    archive_paths=[s for s in SCOPES if any(n.startswith(s+'/') for n in selected)]
    archive_paths.extend(n for n in selected if n.startswith('Baseball/data/raw/'))
    archive=git(repo,'archive','--format=zip',commit,'--',*archive_paths)
    selected=set(selected)
    files={}
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        for item in z.infolist():
            if item.is_dir(): continue
            name=safe_relative(item.filename)
            if name.parts[0]!='Baseball' or stat.S_ISLNK(item.external_attr >> 16):
                raise ValueError('Invalid serving archive entry')
            if item.filename not in selected: continue
            relative=PurePosixPath(*name.parts[1:]).as_posix()
            if relative in files: raise ValueError('Duplicate serving archive entry')
            files[relative]=z.read(item)
    record=dict(artifactType='baseballo-serving-runtime-release',contractVersion=1,
                sourceCommit=commit,files={k:sha(v) for k,v in sorted(files.items())})
    raw=encoded(record); release_id=sha(raw)
    descriptor=dict(releaseId=release_id,manifestSha256=sha(raw),sourceCommit=commit)
    releases=state/'serving/releases';releases.mkdir(parents=True,exist_ok=True)
    target=releases/release_id
    if not target.exists():
        staging=Path(tempfile.mkdtemp(prefix='.capture-',dir=releases))
        try:
            for name, value in files.items():
                path=staging/'Baseball'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(value)
            (staging/'release.json').write_bytes(raw)
            try: os.rename(staging,target)
            except OSError:
                if not target.exists(): raise
        finally:
            # Only remove the verified temporary child created by this call.
            if staging.exists() and staging.resolve().parent==releases.resolve(): shutil.rmtree(staging)
    verify_release(state,descriptor)
    return descriptor


def own_descriptor(root):
    manifest=Path(root).parent/'release.json'
    if not manifest.is_file(): return None
    raw=manifest.read_bytes();record=json.loads(raw)
    return dict(releaseId=sha(raw),manifestSha256=sha(raw),sourceCommit=record['sourceCommit'])


def runtime_hashes(root):
    spec=importlib.util.spec_from_file_location('released_serving_adapter',root/'scripts/pipeline/query-serving-layer.py')
    adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter)
    result={key:sha(path.read_bytes()) for key,path in (
        ('schemaSha256',adapter.SCHEMA),('contractSha256',adapter.CONTRACT),
        ('sourceQuerySha256',adapter.SOURCE_QUERY),('materializerSha256',adapter.MATERIALIZER),
        ('mappingSha256',adapter.MAPPING),('validationSha256',adapter.VALIDATOR),
        ('ratingSpecSha256',adapter.QUALITY_SPEC))}
    catalog=read(adapter.ADVANCED_CATALOG);reducers=read(adapter.ADVANCED_REDUCERS)
    result.update(metricSuiteSha256=adapter._metric_suite.fingerprint(),
        advancedQuerySetSha256=adapter.advanced_query_set_sha256(catalog),
        advancedReducerSha256=sha(adapter.ADVANCED_REDUCERS.read_bytes()),
        dsqMaterializationCatalogSha256=sha(adapter.DSQ_MATERIALIZATIONS.read_bytes()),
        dsqQuerySetSha256=adapter.dsq_query_set_sha256(read(adapter.DSQ_MATERIALIZATIONS),catalog,reducers,read(adapter.QUERY_INDEX_ROUTING)),
        exploreQuerySetSha256=adapter.file_set_sha256(adapter.SERVING_QUERY_FILES))
    return result


def legacy_sidecar(state, pointer):
    return Path(state)/'serving/legacy-releases'/(sha(encoded(pointer))+'.json')


def prepare_legacy(repo, state):
    """Idempotent NiFi migration; never relabel or mutate an old database/pointer."""
    path=Path(state)/'serving/current.json'
    if not path.exists(): return {'status':'no-published-build'}
    pointer=read(path)
    if (pointer.get('artifactType')!='baseball-analytical-serving-pointer' or pointer.get('contractVersion')!=5
            or not all(re.fullmatch('[0-9a-f]{64}',str(pointer.get(k,''))) for k in ('materializerSha256','validationSha256'))):
        return {'status':'unsupported-legacy-pointer'}
    if pointer.get('runtimeRelease'): return {'status':'already-paired'}
    sidecar=legacy_sidecar(state,pointer)
    if sidecar.exists():
        resolve_pointer_release(state,pointer)
        return {'status':'already-paired-legacy','buildId':pointer['buildId']}
    # A failed exact-match search must not rescan/copy history every 15 minutes.
    # New commits or a new pointer invalidate this negative result.
    attempt_key=sha(encoded(dict(pointer=pointer,head=git(repo,'rev-parse','HEAD').decode().strip())))
    attempt_path=Path(state)/'serving/legacy-releases'/('unmatched-'+attempt_key+'.json')
    if attempt_path.exists(): return read(attempt_path)
    commits=git(repo,'log','-100','--format=%H','--',*SCOPES).decode().splitlines()
    for commit in commits:
        # Cheap rejection before copying any historical code.
        matching=True
        for key,name in [('materializerSha256','materialize-serving-layer.py'),('validationSha256','query-serving-layer.py')]:
            blob=git(repo,'show',commit+':Baseball/scripts/pipeline/'+name)
            if sha(blob)!=pointer.get(key): matching=False;break
        if not matching: continue
        descriptor=capture(repo,state,commit);root=verify_release(state,descriptor)
        old_bytecode=sys.dont_write_bytecode;sys.dont_write_bytecode=True
        try: hashes=runtime_hashes(root)
        finally: sys.dont_write_bytecode=old_bytecode
        if any(pointer.get(k)!=v for k,v in hashes.items()): continue
        if read(path)!=pointer: return {'status':'pointer-changed-retry'}
        atomic(sidecar,dict(artifactType='baseballo-legacy-serving-release',contractVersion=1,
            pointerSha256=sha(encoded(pointer)),buildId=pointer['buildId'],runtimeRelease=descriptor,
            verifiedRuntimeHashes=hashes))
        return {'status':'paired-legacy','buildId':pointer['buildId'],'runtimeRelease':descriptor}
    result={'status':'no-exact-legacy-code-match','buildId':pointer.get('buildId')}
    atomic(attempt_path,result)
    return result


def resolve_pointer_release(state, pointer):
    descriptor=pointer.get('runtimeRelease')
    if descriptor is None:
        sidecar=legacy_sidecar(state,pointer)
        if not sidecar.exists(): return None
        record=read(sidecar)
        if (record.get('artifactType')!='baseballo-legacy-serving-release' or record.get('contractVersion')!=1
                or record.get('pointerSha256')!=sha(encoded(pointer)) or record.get('buildId')!=pointer.get('buildId')):
            raise ValueError('Legacy serving pairing does not match published pointer')
        descriptor=record['runtimeRelease']
    return verify_release(state,descriptor)


def state_from_args(argv):
    parser=argparse.ArgumentParser(add_help=False)
    default=os.environ.get('BASEBALLO_STATE_ROOT') or Path(os.environ.get('LOCALAPPDATA','.'))/'BaseballO'/'state'
    parser.add_argument('--state-root',type=Path,default=Path(default))
    args,_=parser.parse_known_args(argv)
    return args.state_root.resolve()


def query_pointer(state, root, request=None):
    if os.environ.get(POINTER_ENV) and own_descriptor(root):
        pointer=json.loads(os.environ[POINTER_ENV])
        if resolve_pointer_release(state,pointer)!=Path(root).resolve(): raise ValueError('Pinned serving pointer uses another release')
        return pointer
    return read(query_pointer_path(state, request))


def query_pointer_path(state, request=None):
    dashboard=Path(state)/'serving/dashboard-current.json'
    if isinstance(request,dict) and request.get('route')=='metric-suite':
        return dashboard
    return Path(state)/'serving/current.json'


def dispatch(root, argv, *, mode):
    """Return None inside the release; otherwise execute its existing entrypoint."""
    if any(arg in {'-h','--help'} for arg in argv): return None
    if mode not in {'build','dashboard-build','query'}: raise ValueError('Unknown serving release operation')
    state=state_from_args(argv);root=Path(root).resolve()
    descriptor=own_descriptor(root)
    if descriptor:
        if verify_release(state,descriptor)!=root: raise ValueError('Incorrect serving release root')
        return None
    if mode in {'build','dashboard-build'}:
        # Legacy recovery is optional; its failure must not prevent a new
        # fully validated candidate from replacing an unpaired old build.
        if mode=='build':
            try: preparation=prepare_legacy(root.parent,state)
            except (OSError,ValueError,subprocess.SubprocessError) as error:
                preparation={'status':'failed','error':str(error)}
            atomic(state/'serving/runtime-preparation.json',preparation)
        descriptor=capture(root.parent,state)
        selected=verify_release(state,descriptor)
        if not (selected/'scripts/pipeline/serving_release.py').is_file():
            raise ValueError('Commit the serving release launcher before deploying it')
        script='materialize-dashboard.py' if mode=='dashboard-build' else 'materialize-serving-layer.py'
        pointer=None
    else:
        # Select the product from the request even when its publication is
        # absent. Missing dashboard SQL must not borrow the report database.
        raw=sys.stdin.read()
        sys.stdin=io.StringIO(raw)
        request=json.loads(raw)
        pointer=read(query_pointer_path(state,request))
        selected=resolve_pointer_release(state,pointer)
        if selected is None: return None  # Legacy compatibility retains all original stale-code checks.
        # Import the immutable adapter without executing its launcher. Pin the
        # pointer read for legacy adapters too, so promotion during a request
        # cannot pair the old reader with the newly published database.
        prior_argv=sys.argv;prior_env=os.environ.get(POINTER_ENV);prior_bytecode=sys.dont_write_bytecode
        try:
            sys.dont_write_bytecode=True
            spec=importlib.util.spec_from_file_location('published_serving_query',selected/'scripts/pipeline/query-serving-layer.py')
            adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter)
            original_load=adapter.load_object
            pointer_path=state/'serving/current.json'
            adapter.load_object=lambda path: pointer if Path(path).resolve()==pointer_path else original_load(path)
            os.environ[POINTER_ENV]=json.dumps(pointer,separators=(',',':'))
            sys.argv=[str(selected/'scripts/pipeline/query-serving-layer.py'),*argv]
            return adapter.main()
        finally:
            sys.argv=prior_argv;sys.dont_write_bytecode=prior_bytecode
            if prior_env is None:os.environ.pop(POINTER_ENV,None)
            else:os.environ[POINTER_ENV]=prior_env
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
    env.pop(POINTER_ENV,None)
    if pointer is not None:env[POINTER_ENV]=json.dumps(pointer,separators=(',',':'))
    return subprocess.run([sys.executable,'-B',str(selected/'scripts/pipeline'/script),*argv],
                          env=env,check=False).returncode
