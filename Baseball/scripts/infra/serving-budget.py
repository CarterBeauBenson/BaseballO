"""NiFi launch budget: one heavy worker; finish requested upstream repairs first.

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


def upstream_repair_priority(state):
    """Honor the temporary repair phase using NiFi's existing status report.

    Release it once, after recorded upstream work clears. Later source work
    remains independent; this is not a permanent corpus-wide serving gate.
    """
    control=state/'pipeline/control/mlb-game'
    path=control/'repair-priority.json'
    if not path.is_file():return False
    request=json.loads(path.read_text(encoding='utf-8-sig'))
    if request.get('enabled') is not True:return False
    report_path=control/'repair-status.json'
    if not report_path.is_file():return True
    report=json.loads(report_path.read_text(encoding='utf-8-sig'))
    if report.get('recordedWorkClear') is not True:return True
    checked=control_timestamp(report['checkedAtUtc'])
    requested=control_timestamp(request['requestedAtUtc'])
    if checked<requested:return True
    request.update(enabled=False,releasedAtUtc=datetime.now(timezone.utc).isoformat(),
        releaseReason='NiFi recorded upstream repair work clear',repairStatusCheckedAtUtc=report['checkedAtUtc'])
    temporary=path.with_suffix('.'+str(os.getpid())+'.pending')
    temporary.write_text(json.dumps(request),encoding='utf-8');temporary.replace(path)
    return False


@contextmanager
def reserve(state,kind):
    state=Path(state).resolve()
    # Reuse the existing repair lease so there is no second resource queue.
    with ExitStack() as stack:
        try:stack.enter_context(LOCK.exclusive(state/'pipeline/work/mlb-game-locks/targeted-repair-budget.lock'))
        except (BlockingIOError,PermissionError):
            yield 'heavy-worker-busy';return
        if upstream_repair_priority(state):
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
    with reserve(args.state_root,args.kind) as reason:
        if reason:
            print(json.dumps(dict(status='deferred',reason=reason)));return 0
        script='materialize-dashboard.py' if args.kind=='dashboard' else 'materialize-serving-layer.py'
        return subprocess.run([sys.executable,'-B',str(ROOT/'scripts/pipeline'/script),
            '--state-root',str(args.state_root),*remaining],stdin=subprocess.DEVNULL,
            env=dict(os.environ,BASEBALLO_SERVING_BUDGET_HELD='1')).returncode


if __name__=='__main__':raise SystemExit(main())
