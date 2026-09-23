"""NiFi-owned daily backup/export and weekly isolated restore; one stage per tick."""
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import re
import shutil
import uuid
import argparse

HERE=Path(__file__).resolve().parent
def module(name,file):
    spec=importlib.util.spec_from_file_location(name,HERE/file)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
R=module('rdf_recovery','rdf-recovery.py')
P=module('recovery_process_state','process_state.py')
LOCK=module('recovery_process_lock','process_lock.py')


def retain_exports(root,current,keep=2):
    root=Path(root).resolve()
    candidates=[]
    for path in root.glob('baseballo-rdf-*'):
        if path.resolve().parent!=root or not re.fullmatch('baseballo-rdf-[0-9a-f]{32}',path.name): continue
        manifest=path/'manifest.json'
        if not manifest.is_file(): continue
        record=json.loads(manifest.read_text(encoding='utf-8'))
        if record.get('artifactType')=='baseballo-rdf-recovery-export' and path.name=='baseballo-rdf-'+record.get('jobId',''):
            candidates.append(path)
    candidates.sort(key=lambda p:p.stat().st_mtime_ns,reverse=True)
    for path in candidates[keep:]:
        if path.resolve()!=Path(current).resolve(): shutil.rmtree(path)


def retain_restores(root,current,keep=2):
    root=(Path(root)/'restores').resolve();candidates=[]
    for path in root.glob('*'):
        if path.resolve().parent!=root or not re.fullmatch('[0-9a-f]{32}',path.name): continue
        manifest=path/'restore.json'
        if not manifest.is_file(): continue
        record=json.loads(manifest.read_text(encoding='utf-8'))
        if (record.get('artifactType')=='baseballo-rdf-restore-proof' and record.get('status') in {'loaded','failed'}
                and Path(record.get('databasePath','')).resolve()==(path/'tdb2').resolve()): candidates.append(path)
    candidates.sort(key=lambda p:p.stat().st_mtime_ns,reverse=True)
    for path in candidates[keep:]:
        if (path/'tdb2').resolve()!=Path(current).resolve(): shutil.rmtree(path)


def tick(config):
    state=Path(config['stateRoot']);root=state/'recovery';root.mkdir(parents=True,exist_ok=True)
    with LOCK.exclusive(root/'worker.lock'):
        return advance(config,root)


def advance(config,root):
    latest=root/'current.json';today=datetime.now().astimezone().date().isoformat()
    job=json.loads(latest.read_text(encoding='utf-8')) if latest.is_file() else {}
    def save(**values):
        job.update(values,updatedAtUtc=R.now());R.atomic_json(latest,job);return dict(job)
    if job.get('phase')=='complete' and job.get('day')==today: return dict(status='unchanged',day=today)
    if not job or job.get('phase')=='complete':
        job=dict(artifactType='baseballo-recovery-work',day=today,jobId=uuid.uuid4().hex,phase='queued',attempts=0)
        save(status='queued')
    if job.get('status')=='failed' and job.get('attempts',0)>=2: return job
    # Preserve source and serving work priority. A pending Fuseki backup is
    # queried once below; no worker sleeps waiting for another stage.
    running=[r for r in P.reconcile_builds(Path(config['stateRoot'])) if r['status']=='running']
    if running: return save(status='waiting-for-serving',activeBuilds=len(running))
    try:
        if job['phase']=='queued':
            backups=Path(config['backups']);backups.mkdir(parents=True,exist_ok=True)
            submitted=R.submit(root,config['server'],config['dataset'],backups,request_id=job['jobId'])
            return save(status='submitted',phase='submitted',taskId=submitted['taskId'])
        if job['phase']=='submitted':
            result=R.complete(root,job['jobId'])
            if result['status']=='pending': return save(status='pending')
            return save(status='verified',phase='verified',archive=result['archive'])
        if job['phase']=='verified':
            destination=Path(config['exportDirectory']).resolve();destination.mkdir(parents=True,exist_ok=True)
            archive=Path(job['archive']['path']).resolve()
            if archive.drive.lower()==destination.drive.lower(): raise ValueError('Export must use a separate drive')
            required=job['archive']['bytes']+config['reserveBytes']
            if shutil.disk_usage(destination).free<required: return save(status='waiting-for-export-space',requiredFreeBytes=required)
            R.export(root,job['jobId'],destination)
            export=destination/('baseballo-rdf-'+job['jobId'])
            retain_exports(destination,export)
            return save(status='exported',phase='exported',exportDirectory=str(export))
        if job['phase']=='exported':
            proof_path=root/'last-restore.json'
            previous=json.loads(proof_path.read_text(encoding='utf-8')) if proof_path.is_file() else {}
            if previous.get('status')=='loaded' and (datetime.now(timezone.utc)-datetime.fromisoformat(previous['finishedAtUtc'])).days<7:
                return save(status='complete',phase='complete',restoreProof=str(proof_path))
            destination=Path(config['restoreRoot']).resolve()
            for prior_path in (destination/'restores').glob('*/restore.json'):
                prior=json.loads(prior_path.read_text(encoding='utf-8'))
                if prior.get('jobId')!=job['jobId'] or prior.get('status')!='loading': continue
                alive=P.alive(prior.get('processId') or prior.get('controllerProcessId'))
                if alive is not False:
                    return save(status='waiting-for-existing-restore',restoreProgress=str(prior_path))
                prior.update(status='failed',error='Isolated restore worker exited without a completion record')
                R.atomic_json(prior_path,prior)
                save(attempts=job.get('attempts',0)+1)
                if job['attempts']>=2: return save(status='failed',error=prior['error'])
            memory=P.available_memory()
            if memory is None or memory<2*1024**3: return save(status='waiting-for-restore-memory',availableMemoryBytes=memory)
            destination.mkdir(parents=True,exist_ok=True)
            required=job['archive']['uncompressedBytes']*3+config['reserveBytes']
            if shutil.disk_usage(destination).free<required: return save(status='waiting-for-restore-space',requiredFreeBytes=required)
            result=R.stage_restore(Path(job['exportDirectory']),destination,Path(config['java']),Path(config['jena']),timeout=21600)
            R.atomic_json(proof_path,result)
            retain_restores(destination,result['databasePath'])
            return save(status='complete',phase='complete',restoreProof=str(proof_path))
        raise ValueError('Unknown recovery phase')
    except Exception as error:
        return save(status='failed',attempts=job.get('attempts',0)+1,error=str(error))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--config',required=True,type=Path)
    args=parser.parse_args()
    try: result=tick(json.loads(args.config.read_text(encoding='utf-8-sig')))
    except BlockingIOError: result=dict(status='already-running')
    print(json.dumps(result))
