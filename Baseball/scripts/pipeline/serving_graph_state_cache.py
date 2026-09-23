"""Reuse a completed live graph check while Fuseki reports no possible writes.

This is NiFi build-time caching, never an HTTP metric request dependency. A
restart, write-capable endpoint request, changed promotion inventory, unknown
endpoint, active request or unavailable counters falls back to the original
live graph check. Read-only queries do not invalidate it.
"""
import hashlib
import json
from pathlib import Path
import urllib.parse
import urllib.request


def encoded(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()
def digest(value):return hashlib.sha256(encoded(value)).hexdigest()


def read_json(url):
    with urllib.request.urlopen(url,timeout=10) as response:return json.load(response)


def state_token(endpoint):
    parsed=urllib.parse.urlsplit(endpoint)
    # This cache is specifically for the configured local Fuseki server, whose
    # dataset mutation paths are enumerated by its own service description.
    if parsed.scheme!='http' or parsed.hostname not in {'localhost','127.0.0.1','::1'}:return None
    dataset=parsed.path.rsplit('/',1)[0]
    if not dataset or dataset=='/':return None
    base=urllib.parse.urlunsplit((parsed.scheme,parsed.netloc,'','',''))
    try:
        server=read_json(base+'/$/server')
        stats=read_json(base+'/$/stats')['datasets'][dataset]
        after=read_json(base+'/$/server')
        started=server['startDateTime']
        if not isinstance(started,str) or not started or after['startDateTime']!=started:return None
        description=next(row for row in server['datasets'] if row['ds.name']==dataset)
        if description.get('ds.state') is not True:return None
        if next(row for row in after['datasets'] if row['ds.name']==dataset)!=description:return None
        configured={name:service['srv.type'] for service in description['ds.services'] for name in service['srv.endpoints']}
        endpoints=stats['endpoints']
        if set(configured)!=set(endpoints):return None
        writes={}
        for name,item in endpoints.items():
            operation=item['operation']
            if operation!=configured[name]:return None
            if operation in {'query','gsp-r'}:continue
            if operation not in {'update','gsp-rw','upload','patch'}:return None
            counts={key:item[key] for key in ('Requests','RequestsGood','RequestsBad')}
            if any(type(n) is not int or n<0 for n in counts.values()):return None
            if counts['Requests']!=counts['RequestsGood']+counts['RequestsBad']:return None
            writes[name]=dict(operation=operation,**counts)
        return dict(base=base,dataset=dataset,started=started,endpoints=configured,writes=writes)
    except (OSError,ValueError,KeyError,TypeError,StopIteration):return None


def snapshot(state,endpoint,inventory,definition,fetch,atomic):
    token=state_token(endpoint)
    key=dict(inventory=inventory['fingerprint'],definition=definition,
        cacheImplementation=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),server=token)
    path=Path(state)/'serving/live-graph-state.json'
    if token is not None:
        try:
            if path.stat().st_size<=16*1024*1024:
                record=json.loads(path.read_bytes())
                if (record['key']==key and record['liveSha256']==digest(record['live'])
                        and state_token(endpoint)==token):
                    return record['live']
        except (OSError,ValueError,KeyError,TypeError):pass
    live=fetch()
    if token is not None and state_token(endpoint)==token:
        atomic(path,dict(key=key,live=live,liveSha256=digest(live)))
    return live
