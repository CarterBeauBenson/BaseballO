"""NiFi-owned checkpoints prevent publishing mixed implementation revisions."""
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import tempfile


class InputsChanged(RuntimeError):pass


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class BuildInputGuard:
    def __init__(self,*,paths,metric_fingerprint,progress_path,build_id,loaded_hashes=None,loaded_metric_hash=None):
        self.paths=paths;self.metric_fingerprint=metric_fingerprint
        self.hashes={name:digest(path) for name,path in paths.items()}
        self.hashes.update(loaded_hashes or {})
        self.metric_hash=loaded_metric_hash or metric_fingerprint();self.path=Path(progress_path)
        self.record=dict(artifactType='baseballo-serving-build-progress',contractVersion=1,
            buildId=build_id,processId=os.getpid(),startedAtUtc=datetime.now(timezone.utc).isoformat(),
            inputHashes=self.hashes,metricSuiteSha256=self.metric_hash,status='running',completedGames=0)

    def save(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.record['updatedAtUtc']=datetime.now(timezone.utc).isoformat()
        with tempfile.NamedTemporaryFile('w',encoding='utf-8',dir=self.path.parent,delete=False) as f:
            json.dump(self.record,f,indent=2);f.write('\n');name=f.name
        os.replace(name,self.path)

    def check(self,*,completed,total,phase):
        current={}
        for name,path in self.paths.items():
            try:current[name]=digest(path)
            except FileNotFoundError:current[name]=None
        changed=sorted(name for name,value in current.items() if value!=self.hashes[name])
        try:metric_hash=self.metric_fingerprint()
        except FileNotFoundError:metric_hash=None
        if metric_hash!=self.metric_hash:changed.append('metric-suite')
        self.record.update(completedGames=completed,totalGames=total,phase=phase)
        if changed:
            self.record.update(status='invalidated',reason='IMPLEMENTATION_CHANGED_DURING_MATERIALIZATION',changedInputs=changed)
            self.save()
            raise InputsChanged('Serving implementation changed during materialization: '+', '.join(changed))
        self.save()

    def finish(self,status):
        self.record.update(status=status);self.save()

    def fail(self,error):
        if self.record['status']!='invalidated':
            self.record.update(status='failed',error=str(error));self.save()
