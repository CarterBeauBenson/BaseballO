#!/usr/bin/env python3
from pathlib import Path
from collections import Counter
import json, re, sys
from rdflib import Graph, RDF, URIRef

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
mapping=HERE/'mlb-direct.rml.ttl'
source=HERE/'game.json'

errors=[]
notes=[]

g=Graph()
try:
    g.parse(mapping,format='turtle')
except Exception as e:
    errors.append(f'RML Turtle parse failed: {e}')
else:
    RR=URIRef('http://www.w3.org/ns/r2rml#TriplesMap')
    tms=set(g.subjects(RDF.type,RR))
    notes.append(f'Triples maps: {len(tms)}')

if not source.exists():
    notes.append('game.json is not present; source-specific checks skipped.')
else:
    j=json.load(open(source,encoding='utf-8'))
    plays=j.get('liveData',{}).get('plays',{}).get('allPlays',[])
    notes.append(f'gamePk: {j.get("gamePk")}')
    notes.append(f'allPlays: {len(plays)}')
    pitches=[e for p in plays for e in p.get('playEvents',[]) if e.get('isPitch')]
    ids=[e.get('playId') for e in pitches]
    if any(x is None for x in ids): errors.append('At least one pitch lacks playId.')
    dup=[(k,v) for k,v in Counter(ids).items() if k is not None and v>1]
    if dup: errors.append(f'Duplicate pitch playId values: {dup[:10]}')
    notes.append(f'pitches: {len(pitches)}; unique pitch playIds: {len(set(ids))}')

    expected={'home_run','field_out','double','walk','force_out','strikeout','single','grounded_into_double_play','sac_fly','double_play','fielders_choice'}
    observed={p.get('result',{}).get('eventType') for p in plays}
    unmapped=sorted(x for x in observed if x and x not in expected)
    if unmapped: notes.append('Observed result types with generic-only mapping: '+', '.join(unmapped))

    runner_keys=[]
    for p in plays:
        for r in p.get('runners',[]):
            m=r.get('movement',{}); d=r.get('details',{}); rid=d.get('runner',{}).get('id'); pi=d.get('playIndex'); et=d.get('eventType')
            if m.get('isOut') is True:
                key=('out',rid,pi,et,m.get('outBase'),m.get('outNumber'))
            elif m.get('isOut') is False and m.get('end')=='score' and m.get('start') is None:
                key=('score-origin',rid,pi,et)
            elif m.get('isOut') is False and m.get('end')=='score':
                key=('score-base',rid,pi,et,m.get('start'))
            elif m.get('isOut') is False and m.get('start') is None:
                key=('reach',rid,pi,et,m.get('end'))
            else:
                key=('advance',rid,pi,et,m.get('start'),m.get('end'))
            runner_keys.append(key)
    duplicates=[(k,v) for k,v in Counter(runner_keys).items() if v>1]
    if duplicates: errors.append(f'Runner composite-key collisions: {duplicates[:20]}')
    notes.append(f'runner records: {len(runner_keys)}; unique composite keys: {len(set(runner_keys))}')

print('\n'.join(notes))
if errors:
    print('\nERRORS:',file=sys.stderr)
    print('\n'.join('- '+e for e in errors),file=sys.stderr)
    raise SystemExit(1)
print('Validation passed.')
