"""Remove MLB Game's obsolete acquisition prerequisite, preserving queued work.

One-time, idempotent deployment migration. No FlowFile drop, graph operation,
processor-wide reconciliation or changes to other source modules are involved.
"""
import importlib.util
import json
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('acquisition_nifi', ROOT / 'scripts/infra/nifi_worker.py')
N = importlib.util.module_from_spec(spec)
spec.loader.exec_module(N)
GATES = {'Check Proof Release', 'Require Proof Release Success',
         'Retry Proof Release Readiness', 'Fail Proof Release'}
DIRECT = '01 schedule batch to acquisition'


def unique(flow, name):
    matches = [p for p in flow['processors'] if p['component']['name'] == name]
    if len(matches) != 1:
        raise ValueError('Expected one MLB Game processor: ' + name)
    return matches[0]


def reconcile(group, api=N.api):
    def flow():
        return api('GET', '/flow/process-groups/' + group)['processGroupFlow']['flow']

    current = flow()
    prepare = unique(current, 'Prepare Schedule Batch')['id']
    acquire = unique(current, 'Acquire MLB Schedule')['id']
    gates = {p['id'] for p in current['processors'] if p['component']['name'] in GATES}
    direct = [c for c in current['connections'] if c['component']['name'] == DIRECT]
    if len(direct) > 1 or (direct and (
            direct[0]['component']['source']['id'] != prepare or
            direct[0]['component']['destination']['id'] != acquire or
            direct[0]['component']['selectedRelationships'] != ['success'])):
        raise ValueError('Existing direct acquisition route differs')
    edges = [c for c in current['connections'] if
             {c['component']['source']['id'], c['component']['destination']['id']} & gates]
    if not gates:
        if not direct:
            raise ValueError('Neither the retired gate nor direct acquisition route exists')
        return dict(status='complete', retiredProcessors=0, preservedRequests=0)
    selected = gates | {prepare, acquire} | {
        c['component'][end]['id'] for c in edges for end in ('source', 'destination')}
    resume, deleted, preserved = [], set(), 0
    try:
        for identifier in sorted(selected):
            entity = api('GET', '/processors/' + identifier)
            if entity['component']['state'] == 'RUNNING':
                if identifier not in gates:
                    resume.append(identifier)
                api('PUT', '/processors/' + identifier + '/run-status', dict(
                    revision=entity['revision'], state='STOPPED', disconnectedNodeAcknowledged=False))
        deadline = time.monotonic() + 10
        while True:
            pending = [p for p in flow()['processors'] if p['id'] in selected and (
                p['component']['state'] == 'RUNNING' or
                p['status']['aggregateSnapshot']['activeThreadCount'])]
            if not pending:
                break
            if time.monotonic() >= deadline:
                raise ValueError('Acquisition processors are still stopping; queued requests are preserved')
            time.sleep(.25)
        # Reread queues after stopping: a request can have moved during shutdown.
        for prior in edges:
            entity = api('GET', '/connections/' + prior['id'])
            component = entity['component']
            count = entity['status']['aggregateSnapshot']['flowFilesQueued']
            is_entry = component['source']['id'] == prepare
            if is_entry and direct:
                raise ValueError('Both legacy and direct schedule entry routes exist')
            if is_entry or count:
                component['destination'] = dict(id=acquire, groupId=group, type='PROCESSOR')
                component['name'] = DIRECT if is_entry else 'Recovered schedule ' + entity['id']
                api('PUT', '/connections/' + entity['id'], dict(revision=entity['revision'], component=component))
                preserved += count
                if is_entry:
                    direct = [entity]
            else:
                api('DELETE', '/connections/' + entity['id'] + '?version=' + str(entity['revision']['version']))
        if not direct:
            raise ValueError('Legacy flow has no schedule entry connection')
        remaining = flow()['connections']
        attached = {c['component'][end]['id'] for c in remaining for end in ('source', 'destination')}
        for identifier in sorted(gates - attached):
            entity = api('GET', '/processors/' + identifier)
            api('DELETE', '/processors/' + identifier + '?version=' + str(entity['revision']['version']))
            deleted.add(identifier)
    finally:
        for identifier in resume:
            entity = api('GET', '/processors/' + identifier)
            api('PUT', '/processors/' + identifier + '/run-status', dict(
                revision=entity['revision'], state='RUNNING', disconnectedNodeAcknowledged=False))
    return dict(status='draining' if gates - deleted else 'complete',
                retiredProcessors=len(deleted), preservedRequests=preserved,
                remainingRetiredProcessors=sorted(gates - deleted))


if __name__ == '__main__':
    contract = json.loads((Path(__file__).with_name('flow-contract.json')).read_text())
    if contract['scheduleDiscovery'].get('requiresCompletedProof') is not False:
        raise SystemExit('MLB Game acquisition gate removal is not configured')
    root = N.api('GET', '/flow/process-groups/root')['processGroupFlow']['id']
    parent = N.group(root, 'BaseballO', 0, 0)
    owner = N.group(parent, 'MLB Game', 0, 0)
    print(json.dumps(reconcile(owner)))
