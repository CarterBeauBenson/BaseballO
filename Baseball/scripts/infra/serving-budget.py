"""NiFi launch budget: one heavy SQL/repair worker, with dashboard priority.

This coordinates resources only. It never changes source schedules, evidence,
RDF or serving pointers, and never terminates an existing worker.
"""
import argparse
from contextlib import contextmanager, ExitStack
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]


def module(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts/pipeline'/(name+'.py'))
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


LOCK=module('process_lock')
PROCESS=module('process_state')


@contextmanager
def reserve(state,kind):
    state=Path(state).resolve();ticket=state/'serving/dashboard-budget-request.json'
    if kind=='dashboard':
        ticket.parent.mkdir(parents=True,exist_ok=True)
        temporary=ticket.with_suffix('.'+str(os.getpid())+'.pending')
        temporary.write_text(json.dumps(dict(expiresAt=time.time()+120)),encoding='utf-8')
        temporary.replace(ticket)
    elif ticket.is_file() and json.loads(ticket.read_text())['expiresAt']>time.time():
        yield 'waiting-dashboard';return
    # Reuse the existing repair lease so there is no second resource queue.
    with ExitStack() as stack:
        try:stack.enter_context(LOCK.exclusive(state/'pipeline/work/mlb-game-locks/targeted-repair-budget.lock'))
        except (BlockingIOError,PermissionError):
            yield 'heavy-worker-busy';return
        # Older workers may have started before this launch budget was deployed.
        if any(r['status']=='running' for r in PROCESS.reconcile_builds(state)):
            yield 'existing-serving-worker';return
        available=PROCESS.available_memory()
        if available is not None and available<1024**3:
            yield 'waiting-for-memory';return
        try:yield None
        finally:
            if kind=='dashboard':ticket.unlink(missing_ok=True)


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
