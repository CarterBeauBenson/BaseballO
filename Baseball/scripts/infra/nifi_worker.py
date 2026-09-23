"""Small provisioning helper for one explicitly owned periodic local worker."""
import argparse
import json
from pathlib import Path
import urllib.parse
import urllib.request
import time


def api(method,path,body=None):
    request=urllib.request.Request('http://127.0.0.1:8080/nifi-api'+path,method=method,
        data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=30) as response: return json.load(response)


def flow(group): return api('GET','/flow/process-groups/'+group)['processGroupFlow']['flow']


def group(parent,name,x,y,create=False):
    matches=[g for g in flow(parent)['processGroups'] if g['component']['name']==name]
    if len(matches)>1: raise ValueError('Group is not unique: '+name)
    if matches: return matches[0]['id']
    if not create: raise ValueError('Owning group is missing: '+name)
    return api('POST','/process-groups/'+parent+'/process-groups',dict(revision={'version':0},
        component=dict(name=name,position=dict(x=x,y=y))))['id']


def processor(parent,name,kind,properties,terminate,x,period='0 sec'):
    matches=[p for p in flow(parent)['processors'] if p['component']['name']==name]
    if len(matches)>1: raise ValueError('Processor is not unique: '+name)
    kind='org.apache.nifi.processors.standard.'+kind
    types=[t for t in api('GET','/flow/processor-types?type='+urllib.parse.quote(kind))['processorTypes'] if t['type']==kind]
    if len(types)!=1: raise ValueError('Processor type is not unique')
    config=dict(properties=properties,autoTerminatedRelationships=terminate,schedulingPeriod=period,
        schedulingStrategy='TIMER_DRIVEN',concurrentlySchedulableTaskCount=1,penaltyDuration='30 sec',yieldDuration='1 sec')
    if not matches:
        return api('POST','/process-groups/'+parent+'/processors',dict(revision={'version':0},component=dict(
            name=name,type=kind,bundle=types[0]['bundle'],position=dict(x=x,y=2200),config=config)))['id']
    entity=api('GET','/processors/'+matches[0]['id'])
    if entity['component']['type']!=kind: raise ValueError('Existing worker type differs')
    if entity['status']['aggregateSnapshot']['activeThreadCount']:
        raise ValueError('Worker is busy; preserve its run and reconcile on the next idle deployment')
    if entity['component']['state']=='RUNNING':
        api('PUT','/processors/'+entity['id']+'/run-status',dict(revision=entity['revision'],state='STOPPED',disconnectedNodeAcknowledged=False))
        deadline=time.monotonic()+5
        while True:
            time.sleep(.25)
            entity=api('GET','/processors/'+entity['id'])
            if entity['component']['state']=='STOPPED' and not entity['status']['aggregateSnapshot']['activeThreadCount']: break
            if time.monotonic()>=deadline: raise ValueError('Worker did not become idle for configuration')
    api('PUT','/processors/'+entity['id'],dict(revision=entity['revision'],component=dict(id=entity['id'],config=config)))
    return entity['id']


def connection(parent,name,source,dest,relationship):
    matches=[c for c in flow(parent)['connections'] if c['component']['name']==name]
    if len(matches)>1: raise ValueError('Connection is not unique')
    if matches:
        c=matches[0]['component']
        if (c['source']['id'],c['destination']['id'],c['selectedRelationships'])!=(source,dest,[relationship]):
            raise ValueError('Existing worker edge differs from its owner contract')
        return
    api('POST','/process-groups/'+parent+'/connections',dict(revision={'version':0},component=dict(name=name,
        source=dict(id=source,groupId=parent,type='PROCESSOR'),destination=dict(id=dest,groupId=parent,type='PROCESSOR'),
        selectedRelationships=[relationship],backPressureObjectThreshold=1,backPressureDataSizeThreshold='1 MB',flowFileExpiration='0 sec')))


def install(config):
    root=api('GET','/flow/process-groups/root')['processGroupFlow']['id']
    baseball=group(root,'BaseballO',100,100)
    owner=group(baseball,config['group'],config.get('x',1100),config.get('y',1000),config.get('createGroup',False))
    name=config['name']
    trigger=processor(owner,name+' Timer','GenerateFlowFile',{
        'Custom Text':'{}','File Size':'0B','Batch Size':'1','Data Format':'Text','Unique FlowFiles':'false'},[],0,config['period'])
    command=processor(owner,name,'ExecuteStreamCommand',{
        'Working Directory':config['workingDirectory'],'Command Path':config['python'],
        'Command Arguments Strategy':'Command Arguments Property','Command Arguments':';'.join(config['arguments']),
        'Argument Delimiter':';','Ignore STDIN':'true','Output Destination Attribute':'worker.result',
        'Max Attribute Length':'65536'},['output stream','nonzero status'],320)
    logger=processor(owner,'Record '+name,'LogAttribute',{'Log Payload':'false'},['success'],640)
    connection(owner,name+' requested',trigger,command,'success')
    connection(owner,name+' recorded',command,logger,'original')
    for identifier in (logger,command,trigger):
        entity=api('GET','/processors/'+identifier)
        api('PUT','/processors/'+identifier+'/run-status',dict(revision=entity['revision'],state='RUNNING',disconnectedNodeAcknowledged=False))
    return dict(groupId=owner,workerId=command,status='enabled')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--config',required=True,type=Path)
    args=parser.parse_args(); print(json.dumps(install(json.loads(args.config.read_text(encoding='utf-8-sig')))))
