#!/usr/bin/env python3
"""Bounded recovery stages for NiFi; no scheduler and no live-store restore."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with temporary.open('x', encoding='utf-8', newline='\n') as stream:
            json.dump(value, stream, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def http_json(server: str, route: str, method: str = 'GET'):
    parsed = urlparse(server)
    if parsed.scheme != 'http' or parsed.hostname not in {'127.0.0.1', 'localhost', '::1'} or parsed.username or parsed.password or parsed.path not in {'', '/'} or parsed.query or parsed.fragment:
        raise ValueError('Recovery accepts a loopback Fuseki server only')
    with urlopen(Request(server.rstrip('/') + route, method=method), timeout=30) as response:
        raw = response.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ValueError('Fuseki task response exceeds its limit')
    return json.loads(raw)


def stamp(path: Path) -> tuple:
    stat = path.stat()
    return stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns


def archive_integrity(path: Path) -> dict:
    if path.is_symlink() or not path.is_file() or not path.name.endswith('.nq.gz'):
        raise ValueError('Expected a regular gzip N-Quads backup')
    before = stamp(path)
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    uncompressed = 0
    # Reading to EOF checks gzip CRC and truncation, using bounded memory.
    with gzip.open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            uncompressed += len(block)
    if before != stamp(path):
        raise ValueError('Backup changed during verification')
    return {'sha256': digest.hexdigest(), 'bytes': before[0], 'uncompressedBytes': uncompressed}


def job_path(root: Path, job_id: str) -> Path:
    if not re.fullmatch(r'[0-9a-f]{32}', job_id):
        raise ValueError('Invalid recovery job identity')
    return root.resolve() / 'jobs' / (job_id + '.json')


def read_job(root: Path, job_id: str) -> tuple[Path, dict]:
    path = job_path(root, job_id)
    job = json.loads(path.read_text(encoding='utf-8'))
    if job.get('artifactType') != 'baseballo-rdf-backup-job' or job.get('jobId') != job_id:
        raise ValueError('Recovery job identity mismatch')
    return path, job


def submit(root: Path, server: str, dataset: str, backups: Path, request=http_json, request_id: str | None = None) -> dict:
    if not re.fullmatch(r'[A-Za-z0-9_-]+', dataset):
        raise ValueError('Invalid dataset name')
    backups = backups.resolve(strict=True)
    if not backups.is_dir():
        raise ValueError('Backup directory is missing')
    job_id = uuid.UUID(request_id).hex if request_id else uuid.uuid4().hex
    path = job_path(root, job_id)
    job = {'artifactType': 'baseballo-rdf-backup-job', 'contractVersion': 1,
           'jobId': job_id, 'status': 'submitting', 'submittedAtUtc': now(),
           'server': server, 'dataset': dataset, 'backupDirectory': str(backups),
           'priorFiles': sorted(p.name for p in backups.glob(dataset + '_*.nq.gz'))}
    # Persist intent before POST. An ambiguous network failure must be reviewed;
    # retrying this job never silently launches a second backup.
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open('x', encoding='utf-8') as stream:
            json.dump(job, stream)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        _, existing = read_job(root, job_id)
        if any(existing.get(key) != job[key] for key in ('server', 'dataset', 'backupDirectory')):
            raise ValueError('Backup request identity was reused with different inputs')
        if existing['status'] not in {'submitted', 'verified'}:
            raise ValueError('Existing submission requires review; no second POST was issued')
        return existing
    try:
        response = request(server, '/$/backup/' + quote(dataset), 'POST')
        task_id = str(response['taskId'])
        if not re.fullmatch(r'[A-Za-z0-9_-]+', task_id):
            raise ValueError('Invalid Fuseki task identity')
        job.update(status='submitted', taskId=task_id)
    except Exception as error:
        job.update(status='submission-uncertain', error=str(error))
        atomic_json(path, job)
        raise
    atomic_json(path, job)
    return job


def complete(root: Path, job_id: str, request=http_json) -> dict:
    path, job = read_job(root, job_id)
    if job['status'] == 'verified':
        verify(root, job_id)
        return job
    if job['status'] != 'submitted':
        raise ValueError('This job is not an unambiguous submitted backup')
    response = request(job['server'], '/$/tasks/' + quote(job['taskId']))
    tasks = response if isinstance(response, list) else [response]
    matching = [t for t in tasks if str(t.get('taskId')) == job['taskId']]
    if len(matching) != 1:
        raise ValueError('Fuseki did not return the exact backup task')
    task = matching[0]
    if task.get('task') not in {'backup', 'Backup'}:
        raise ValueError('Task identity was reused for another operation')
    started = datetime.fromisoformat(str(task['started']).replace('Z', '+00:00'))
    submitted = datetime.fromisoformat(job['submittedAtUtc'])
    if started.tzinfo is None or started < submitted:
        raise ValueError('Task predates this backup request; possible server restart or reused ID')
    if not (task.get('finished') or task.get('finishPoint')):
        return {**job, 'status': 'pending'}
    if task.get('success') is not True:
        job.update(status='failed', task=task)
        atomic_json(path, job)
        raise ValueError('Fuseki backup task failed')
    directory = Path(job['backupDirectory'])
    candidates = [p for p in directory.glob(job['dataset'] + '_*.nq.gz') if p.name not in job['priorFiles']]
    if len(candidates) != 1:
        raise ValueError('Cannot associate exactly one fresh backup with this task')
    archive = candidates[0]
    integrity = archive_integrity(archive)
    job.update(status='verified', verifiedAtUtc=now(), task=task,
               archive={'path': str(archive), **integrity}, scope='rdf-dataset-only')
    atomic_json(path, job)
    return job


def verify(root: Path, job_id: str) -> dict:
    _, job = read_job(root, job_id)
    if job.get('status') != 'verified':
        raise ValueError('Backup has not passed completion and integrity checks')
    actual = archive_integrity(Path(job['archive']['path']))
    if any(actual[key] != job['archive'].get(key) for key in actual):
        raise ValueError('Backup no longer matches its verified manifest')
    return job


def export(root: Path, job_id: str, destination: Path) -> dict:
    job = verify(root, job_id)
    destination = destination.resolve(strict=True)
    if not destination.is_dir():
        raise ValueError('Backup destination must already exist')
    target = destination / ('baseballo-rdf-' + job_id)
    if target.exists():
        manifest = json.loads((target / 'manifest.json').read_text(encoding='utf-8'))
        expected = {k: job['archive'][k] for k in ('sha256', 'bytes', 'uncompressedBytes')}
        if manifest.get('artifactType') != 'baseballo-rdf-recovery-export' or manifest.get('jobId') != job_id or manifest.get('archive') != {'file': 'dataset.nq.gz', **expected} or archive_integrity(target / 'dataset.nq.gz') != expected:
            raise ValueError('Existing export differs from this backup')
        return manifest
    staging = destination / ('.baseballo-rdf-' + job_id + '-' + uuid.uuid4().hex + '.partial')
    staging.mkdir()
    # Failed partial copies remain identifiable for diagnosis; never publish a
    # success manifest or replace an existing export after a copy failure.
    shutil.copyfile(job['archive']['path'], staging / 'dataset.nq.gz')
    expected = {k: job['archive'][k] for k in ('sha256', 'bytes', 'uncompressedBytes')}
    if archive_integrity(staging / 'dataset.nq.gz') != expected:
        raise ValueError('Copied backup failed integrity verification')
    manifest = {'artifactType': 'baseballo-rdf-recovery-export', 'contractVersion': 1,
                'jobId': job_id, 'scope': 'rdf-dataset-only', 'exportedAtUtc': now(),
                'archive': {'file': 'dataset.nq.gz', **expected}, 'backup': job}
    atomic_json(staging / 'manifest.json', manifest)
    staging.rename(target)
    return manifest


def stage_restore(export_directory: Path, recovery_root: Path, java: Path, jena: Path, timeout: int = 3600) -> dict:
    manifest = json.loads((export_directory / 'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('artifactType') != 'baseballo-rdf-recovery-export' or manifest.get('archive', {}).get('file') != 'dataset.nq.gz':
        raise ValueError('Invalid RDF recovery export')
    archive = export_directory / 'dataset.nq.gz'
    actual = archive_integrity(archive)
    if any(actual[key] != manifest['archive'].get(key) for key in actual):
        raise ValueError('Export archive failed manifest verification')
    # The caller never names a live TDB directory. A fresh UUID directory is
    # always allocated, and no live endpoint, pointer or storage config is used.
    stage = recovery_root.resolve() / 'restores' / uuid.uuid4().hex
    stage.mkdir(parents=True, exist_ok=False)
    report = {'artifactType': 'baseballo-rdf-restore-proof', 'scope': 'isolated-rdf-dataset',
              'status': 'loading', 'startedAtUtc': now(), 'jobId': manifest['jobId'], 'archive': actual,
              'databasePath': str(stage / 'tdb2'), 'promoted': False}
    atomic_json(stage / 'restore.json', report)
    with (stage / 'loader.stdout.log').open('wb') as out, (stage / 'loader.stderr.log').open('wb') as err:
        try:
            subprocess.run([str(java), '-Xmx1g', '-cp', str(jena), 'tdb2.tdbloader', '--loader=basic',
                            '--loc=' + str(stage / 'tdb2'), str(archive.resolve())],
                           stdout=out, stderr=err, check=True, timeout=timeout,
                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            if archive_integrity(archive) != actual:
                raise ValueError('Export changed during restore')
            report.update(status='loaded', finishedAtUtc=now())
        except Exception as error:
            report.update(status='failed', error=str(error), finishedAtUtc=now())
            atomic_json(stage / 'restore.json', report)
            raise
    atomic_json(stage / 'restore.json', report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    commands = parser.add_subparsers(dest='action', required=True)
    submit_args = commands.add_parser('submit')
    submit_args.add_argument('--server', default='http://127.0.0.1:3031')
    submit_args.add_argument('--dataset', default='baseball-dev')
    submit_args.add_argument('--backups', type=Path, required=True)
    submit_args.add_argument('--request-id', help='Stable UUID supplied by NiFi for idempotent submission retries')
    for action in ('complete', 'verify', 'export'):
        child = commands.add_parser(action)
        child.add_argument('--job', required=True)
        if action == 'export':
            child.add_argument('--destination', type=Path, required=True)
    restore_args = commands.add_parser('stage-restore')
    restore_args.add_argument('--export-directory', type=Path, required=True)
    restore_args.add_argument('--java', type=Path, required=True)
    restore_args.add_argument('--jena', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.action == 'submit':
            result = submit(args.root, args.server, args.dataset, args.backups, request_id=args.request_id)
        elif args.action == 'complete':
            result = complete(args.root, args.job)
        elif args.action == 'verify':
            result = verify(args.root, args.job)
        elif args.action == 'export':
            result = export(args.root, args.job, args.destination)
        else:
            result = stage_restore(args.export_directory, args.root, args.java, args.jena)
        print(json.dumps(result, ensure_ascii=True))
        return 0
    except Exception as error:
        print(json.dumps({'status': 'failed', 'error': str(error)}, ensure_ascii=True))
        return 1


if __name__ == '__main__':
    sys.exit(main())
