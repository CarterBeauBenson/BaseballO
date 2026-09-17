"""NiFi-owned repair of retained schedule transport completeness.

Reacquire at most one affected range per batch-worker invocation. Preserve the
original batch and game requests; retain a separate hash-addressed snapshot.
This supplies calendar provenance, not RDF, scores or player admission.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import urllib.request

MODULE = Path(__file__).resolve().parents[1]
PARSER_PATH = MODULE/'nifi/prepare-schedule-batch.py'
spec = importlib.util.spec_from_file_location('mlb_schedule_transport',PARSER_PATH)
PARSER = importlib.util.module_from_spec(spec); spec.loader.exec_module(PARSER)
ARTIFACT = 'baseballo-mlb-game-schedule-coverage-snapshot'
MAX_RESPONSE = 32 * 1024 * 1024


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value,sort_keys=True,ensure_ascii=True,separators=(',',':'))+'\n').encode()


def fingerprint():
    return sha(encoded({p.name:sha(p.read_bytes()) for p in (Path(__file__),PARSER_PATH)}))


def root(state):
    return Path(state)/'pipeline/control/mlb-game/schedule-coverage'


def identity(batch):
    return {k:batch[k] for k in ('batchId','scheduleSha256','requestedStartDate','requestedEndDate')}


def timestamp(text):
    value=datetime.fromisoformat(text.replace('Z','+00:00'))
    if value.tzinfo is None:raise ValueError('Schedule observation needs an explicit time zone')
    return value


def batches(state):
    output=[]
    for path in sorted((Path(state)/'pipeline/control/mlb-game/batches').glob('*.json')):
        value=json.loads(path.read_text(encoding='utf-8-sig'))
        if value.get('artifactType')!='baseballo-mlb-game-schedule-batch' or value.get('contractVersion')!=1:
            raise ValueError('Invalid owning schedule batch')
        if value.get('qualificationCoverage',{}).get('contractVersion')!=1:continue
        if not PARSER.BATCH_ID.fullmatch(value['batchId']):raise ValueError('Invalid schedule batch identity')
        start=PARSER.iso_date(value['requestedStartDate'],'requestedStartDate')
        end=PARSER.iso_date(value['requestedEndDate'],'requestedEndDate')
        if start>end:raise ValueError('Reversed schedule range')
        output.append(value)
    return sorted(output,key=lambda b:(timestamp(b['createdAtUtc']),b['batchId']))


def snapshots(state, owners):
    current=fingerprint(); output=[]
    for path in sorted(root(state).glob('*.json')):
        raw=path.read_bytes()
        if sha(raw)!=path.stem:raise ValueError('Schedule coverage snapshot checksum mismatch')
        value=json.loads(raw)
        if value.get('artifactType')!=ARTIFACT or value.get('contractVersion')!=1:
            raise ValueError('Invalid schedule coverage snapshot')
        owner=owners.get(value.get('sourceBatch',{}).get('batchId'))
        if not owner or value['sourceBatch']!=identity(owner):
            raise ValueError('Schedule coverage snapshot differs from its owning batch')
        if value.get('implementationSha256')!=current:continue
        coverage=value['qualificationCoverage']
        if coverage.get('contractVersion')!=1:raise ValueError('Invalid schedule coverage contract')
        expected=set(); day=date.fromisoformat(owner['requestedStartDate'])
        while day<=date.fromisoformat(owner['requestedEndDate']):
            expected.add(day.isoformat()); day+=timedelta(days=1)
        if set(coverage['days'])!=expected:raise ValueError('Schedule snapshot date census differs')
        output.append((timestamp(value['createdAtUtc']),path,value))
    return sorted(output,key=lambda item:(item[0],item[1].name))


def merge_snapshots(state, days):
    """Current snapshots supplement, never rewrite, historical batch manifests."""
    output=dict(days); owners={b['batchId']:b for b in batches(state)}
    for observed,path,snapshot in snapshots(state,owners):
        coverage=snapshot['qualificationCoverage']
        for day,games in coverage['days'].items():
            if day in output and timestamp(output[day]['observedAt'])>observed:continue
            output[day]=dict(completeResponse=coverage['completeResponse'] is True,games=games,
                scheduleSha256=snapshot['scheduleSha256'],batchId=snapshot['sourceBatch']['batchId'],
                observedAt=snapshot['createdAtUtc'],provenanceSha256=path.stem,
                transportIssues=coverage['issues'])
    return output


def acquire(url):
    with urllib.request.urlopen(url,timeout=45) as response:
        raw=response.read(MAX_RESPONSE+1)
    if len(raw)>MAX_RESPONSE:raise ValueError('Schedule response exceeds transport limit')
    return raw


def publish(state, value):
    raw=encoded(value); path=root(state)/(sha(raw)+'.json')
    if path.exists():
        if path.read_bytes()!=raw:raise ValueError('Existing schedule snapshot changed')
    else:
        # Use the source lane's fsynced atomic writer, then address its exact
        # serialized bytes. The staging name is never read as a snapshot.
        path.parent.mkdir(parents=True,exist_ok=True)
        import os,tempfile
        with tempfile.NamedTemporaryFile(dir=path.parent,suffix='.partial',delete=False) as stream:
            temporary=Path(stream.name); stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        try:os.replace(temporary,path)
        finally:temporary.unlink(missing_ok=True)
    return path


def refresh_incomplete_batches(state, *, fetch=acquire, now=None):
    """One idempotent repair per tick; two transport attempts per implementation."""
    owners=batches(state); by_id={b['batchId']:b for b in owners}; latest={}
    for batch in owners:
        for day in batch['qualificationCoverage']['days']:latest[day]=batch
    retained=snapshots(state,by_id)
    completed={s['sourceBatch']['batchId'] for _,_,s in retained}
    candidates={b['batchId']:b for b in latest.values()
        if b['qualificationCoverage'].get('completeResponse') is not True and b['batchId'] not in completed}
    if not candidates:return dict(status='idle',requests=0)
    version=fingerprint()
    for batch in sorted(candidates.values(),key=lambda b:(timestamp(b['createdAtUtc']),b['batchId']),reverse=True):
        key=sha(encoded(dict(sourceBatch=identity(batch),implementationSha256=version)))
        attempt_path=root(state)/'attempts'/(key+'.json')
        attempt=json.loads(attempt_path.read_bytes()) if attempt_path.exists() else dict(attempts=0)
        if attempt['attempts']<2:break
    else:return dict(status='quarantined',requests=0,batchIds=sorted(candidates))
    when=now or datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
    url=('https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate='+batch['requestedStartDate']+
        '&endDate='+batch['requestedEndDate'])
    raw=None
    try:
        raw=fetch(url)
        document=json.loads(raw.decode('utf-8'))
        if not isinstance(document,dict):raise ValueError('Schedule response root must be an object')
        coverage=PARSER.qualification_coverage(document,PARSER.schedule_observations(document),
            batch['requestedStartDate'],batch['requestedEndDate'])
        if fingerprint()!=version:raise ValueError('Schedule implementation changed during refresh')
        snapshot=dict(artifactType=ARTIFACT,contractVersion=1,sourceBatch=identity(batch),
            implementationSha256=version,createdAtUtc=when,sourceUrl=url,scheduleSha256=sha(raw),
            qualificationCoverage=coverage)
        if not coverage['completeResponse']:raise ValueError('Schedule transport remains incomplete: '+str(coverage['issues']))
        path=publish(state,snapshot)
    except (OSError,ValueError,KeyError,TypeError) as error:
        attempt=dict(attempts=attempt['attempts']+1,sourceBatch=identity(batch),
            implementationSha256=version,observedAt=when,error=str(error))
        if raw is not None:
            quarantine=Path(state)/'pipeline/quarantine/mlb-game/schedule-coverage'/key/(sha(raw)+'.json')
            quarantine.parent.mkdir(parents=True,exist_ok=True)
            if quarantine.exists() and quarantine.read_bytes()!=raw:raise ValueError('Quarantined schedule changed')
            if not quarantine.exists():quarantine.write_bytes(raw)
            attempt.update(sourceSha256=sha(raw),quarantinePath=str(quarantine))
        PARSER.atomic_json(attempt_path,attempt)
        return dict(status='retry' if attempt['attempts']<2 else 'quarantined',requests=1,
            batchId=batch['batchId'],error=str(error))
    return dict(status='refreshed',requests=1,batchId=batch['batchId'],path=str(path),
                sourceSha256=snapshot['scheduleSha256'],completeResponse=True)
