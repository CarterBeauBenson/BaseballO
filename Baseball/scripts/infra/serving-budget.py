"""NiFi launch budget: one heavy worker, with bounded dashboard publication turns.

This coordinates resources only. It never changes source schedules, evidence,
RDF or serving pointers, and never terminates an existing worker.
"""
import argparse
from contextlib import contextmanager, ExitStack
import importlib.util
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[2]


def module(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts/pipeline'/(name+'.py'))
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


LOCK=module('process_lock')
PROCESS=module('process_state')


def control_timestamp(value):
    # PowerShell writes seven fractional digits; Python 3.10 accepts only
    # three or six. These scheduler timestamps compare at microsecond precision.
    text = re.sub(r'\.(\d+)(?=Z|[+-]\d{2}:\d{2}$)',
                  lambda match: '.'+match[1][:6].ljust(6, '0'), value)
    result = datetime.fromisoformat(text.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Repair control timestamp requires a time zone')
    return result


def upstream_repair_priority(state,kind='report',*,now=None):
    """Honor the temporary repair phase using NiFi's existing status report.

    Repairs keep priority over the legacy report. The dashboard can publish
    supported results between repair batches, at most once per ten minutes.
    One unresolved repair must not suppress all other completed results.
    """
    control=state/'pipeline/control/mlb-game'
    path=control/'repair-priority.json'
    if not path.is_file():return False
    request=json.loads(path.read_text(encoding='utf-8-sig'))
    if request.get('enabled') is not True:return False
    report_path=control/'repair-status.json'
    if not report_path.is_file():return True
    report=json.loads(report_path.read_text(encoding='utf-8-sig'))
    checked=control_timestamp(report['checkedAtUtc'])
    requested=control_timestamp(request['requestedAtUtc'])
    if checked<requested:return True
    now=now or datetime.now(timezone.utc)
    if report.get('recordedWorkClear') is not True:
        if kind!='dashboard':return True
        pointer=state/'serving/dashboard-current.json'
        last_publication=requested
        if pointer.is_file():
            published=json.loads(pointer.read_text(encoding='utf-8-sig')).get('promotedAtUtc')
            if published:last_publication=max(last_publication,control_timestamp(published))
        return (now-last_publication).total_seconds()<600
    request.update(enabled=False,releasedAtUtc=datetime.now(timezone.utc).isoformat(),
        releaseReason='NiFi recorded upstream repair work clear',repairStatusCheckedAtUtc=report['checkedAtUtc'])
    temporary=path.with_suffix('.'+str(os.getpid())+'.pending')
    temporary.write_text(json.dumps(request),encoding='utf-8');temporary.replace(path)
    return False


@contextmanager
def reserve(state,kind,*,wait_seconds=0):
    state=Path(state).resolve()
    # Reuse the existing repair lease so there is no second resource queue.
    with ExitStack() as stack:
        # NiFi's minute timers can otherwise collide with the same short
        # admission sweep forever. Both SQL owners use the same bounded
        # handoff window, without tickets, priority or concurrent heavy work.
        deadline=time.monotonic()+wait_seconds
        while True:
            try:
                stack.enter_context(LOCK.exclusive(state/'pipeline/work/mlb-game-locks/targeted-repair-budget.lock'))
                break
            except (BlockingIOError,PermissionError):
                remaining=deadline-time.monotonic()
                if remaining<=0:
                    yield 'heavy-worker-busy';return
                time.sleep(min(0.25,remaining))
        if upstream_repair_priority(state,kind):
            yield 'upstream-repairs-first';return
        # Older workers may have started before this launch budget was deployed.
        if any(r['status']=='running' for r in PROCESS.reconcile_builds(state)):
            yield 'existing-serving-worker';return
        available=PROCESS.available_memory()
        if available is not None and available<1024**3:
            yield 'waiting-for-memory';return
        yield None


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-root',type=Path,default=Path(os.environ.get('BASEBALLO_STATE_ROOT') or Path(os.environ.get('LOCALAPPDATA','.'))/'BaseballO/state'))
    parser.add_argument('--kind',choices=('dashboard','report'),required=True)
    args,remaining=parser.parse_known_args(argv)
    with reserve(args.state_root,args.kind,wait_seconds=45) as reason:
        if reason:
            print(json.dumps(dict(status='deferred',reason=reason)));return 0
        script='materialize-dashboard.py' if args.kind=='dashboard' else 'materialize-serving-layer.py'
        return subprocess.run([sys.executable,'-B',str(ROOT/'scripts/pipeline'/script),
            '--state-root',str(args.state_root),*remaining],stdin=subprocess.DEVNULL,
            env=dict(os.environ,BASEBALLO_SERVING_BUDGET_HELD='1')).returncode


if __name__=='__main__':raise SystemExit(main())
