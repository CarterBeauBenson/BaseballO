"""One read-only source diagnostic; exercise repair in a temporary state root."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile

ROOT=Path(__file__).resolve().parents[1]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


Q=load('schedule_qualification_proof',ROOT/'sources/mlb-game/pipeline/schedule-qualification.py')
B=load('schedule_batch_provenance',ROOT/'sources/mlb-game/pipeline/batting-admission.py')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--batch',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();original=args.batch.read_bytes();batch=json.loads(original)
    with tempfile.TemporaryDirectory() as directory:
        state=Path(directory);copy=state/'pipeline/control/mlb-game/batches'/args.batch.name
        copy.parent.mkdir(parents=True);copy.write_bytes(original)
        before=B.schedule_coverage(state)
        result=Q.refresh_incomplete_batches(state)
        assert result['status']=='refreshed',result
        snapshot=json.loads(Path(result['path']).read_bytes())
        after=Q.merge_snapshots(state,before)
        def no_fetch(_):raise AssertionError('Completed repair acquired the schedule again')
        assert Q.refresh_incomplete_batches(state,fetch=no_fetch)['status']=='idle'
        assert copy.read_bytes()==original and args.batch.read_bytes()==original
        coverage=snapshot['qualificationCoverage']
        assert coverage['responseOccurrences']==coverage['coveredOccurrences']
        assert all(d['completeResponse'] for d in after.values())
        report=dict(artifactType='baseballo-schedule-qualification-developer-proof',batchId=batch['batchId'],
            originalBatchSha256=hashlib.sha256(original).hexdigest(),
            originalSourceSha256=batch['scheduleSha256'],refreshedSourceSha256=snapshot['scheduleSha256'],
            implementationSha256=Q.fingerprint(),snapshotSha256=Path(result['path']).stem,
            requestedStartDate=batch['requestedStartDate'],requestedEndDate=batch['requestedEndDate'],
            completeDaysBefore=sum(d['completeResponse'] for d in before.values()),
            completeDaysAfter=sum(d['completeResponse'] for d in after.values()),
            responseOccurrences=coverage['responseOccurrences'],coveredOccurrences=coverage['coveredOccurrences'],
            rescheduledGame823543=[dict(date=day,**g) for day,d in after.items() for g in d['games'] if g['gamePk']=='823543'],
            noRepeatedAcquisition=True,originalBatchUnchanged=True,gameRequestsEmitted=0,
            runtimeStateChanged=False,liveDashboardAdmissionAssessed=False)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_bytes((json.dumps(report,indent=2)+'\n').encode())
    print(json.dumps(report))


if __name__=='__main__':main()
