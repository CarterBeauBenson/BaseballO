"""Correct inventoried game-end values through the existing game transaction.

Selection comes from the shared production clock selector. The inventory only
bounds historical mutation; it is not a new game-specific mapping rule.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import re
from pathlib import Path
from rdflib import Graph, Literal, URIRef, XSD

HERE=Path(__file__).resolve().parent
def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
W=module(HERE/'targeted-award-addition.py','clock_transaction')
C=module(HERE/'clock-admission.py','corrected_clock')
INVENTORY=HERE/'clock-correction-candidates.json'
DECISION=W.read(INVENTORY)['decision']
SUCCESS={'complete','already-complete','already-present'}

def case_for(game_pk):
    matches=[c for c in W.read(INVENTORY)['cases'] if c['gamePk']==game_pk]
    if len(matches)!=1:raise ValueError('Clock correction leaves its inventoried scope')
    return matches[0]

def select(raw,game_pk):
    case=case_for(game_pk)
    if hashlib.sha256(raw).hexdigest()!=case['sha256']:raise ValueError('Clock witness changed')
    source=C.census(raw,game_pk);terminal=C.CONTEXT.terminal_baseball_play(json.loads(raw))
    if (not source['graphSourceReconciled'] or terminal['atBatIndex']!=case['terminalAtBatIndex']
            or terminal['about']['endTime']!=case['gameEnd']):
        raise ValueError('Inventoried terminal clock does not match production selection')
    rows=[r for r in source['expected'] if r['process']==source['game'] and r['side']=='end']
    if len(rows)!=1 or rows[0]['value']!=case['gameEnd']:raise ValueError('Terminal clock is withheld')
    return source

def execution_inputs(raw,game_pk,selected,context,mapping):
    row=next(r for r in selected['expected'] if r['process']==selected['game'] and r['side']=='end')
    W.atomic(context,dict(gamePk=int(game_pk),_baseballO=dict(gameEndClocks=[dict(value=compact_fraction(row['value']))])))
    W.A.subset_mapping(game_pk,mapping,('GameEndTimestampMap',))

def compact_fraction(value):
    """Match TDB2's fractional-second lexical form without changing the instant.

    Keep the original source value in the census. The clock SHACL compares
    dateTime values; the transaction compares the exact stored RDF terms.
    """
    def compact(match):
        digits=match.group(1).rstrip('0')
        return '.'+digits if digits else ''
    return re.sub(r'\.(\d+)(?=Z$|[+-]\d\d:\d\d$)',compact,value)

def removals(base,delta,game_pk,selected):
    case=case_for(game_pk);subject=URIRef(selected['game']+'/timestamp/end')
    predicate=URIRef('https://www.commoncoreontologies.org/ont00001767')
    old=(subject,predicate,Literal(case['previousGameEnd'],datatype=XSD.dateTime,normalize=False))
    new=(subject,predicate,Literal(compact_fraction(case['gameEnd']),datatype=XSD.dateTime,normalize=False))
    allowed=Graph();allowed.add(new)
    if len(delta-base-allowed) or new not in delta:raise ValueError('Clock RML delta exceeds its scope')
    existing=set(base.objects(subject,predicate))
    if existing=={new[2]}:return Graph()
    if existing!={old[2]}:raise ValueError('Existing clock differs from the diagnosed value')
    removed=Graph();removed.add(old);return removed

def shapes(game_pk,selected):
    if selected['gamePk']!=game_pk:raise ValueError('Clock source belongs to another game')
    return C.shape_text(selected)

def revalidate(marker,manifest,rdf,evidence,java,classpath,selected,game_pk,delta):
    prior={k:v for k,v in marker.items() if k not in {'clockAdmission','clockAdmissionSha256'}}
    fields=W.revalidate(prior,manifest,rdf,evidence,java,classpath,selected,game_pk,delta,
        shape_text=shapes,decisions=dict(decision=DECISION))
    output=evidence/'clock-admission.json';original=C.census
    C.census=lambda raw,pk:copy.deepcopy(selected)
    try:proof=C.prove(raw=b'',game_pk=game_pk,rdf_path=rdf,output=output,java=java,classpath=classpath)
    finally:C.census=original
    if not proof['graphConforms']:raise ValueError('Corrected clock census does not conform')
    proof['graphRevalidation']=dict(decision=DECISION,mode='current-clock-source-census',
        promotionSourceSha256=marker['rawSha256'],originalProofSha256=marker.get('clockAdmissionSha256'))
    W.atomic(output,proof)
    return dict(fields,clockAdmission=str(output),clockAdmissionSha256=W.sha(output))

def fingerprint():
    return hashlib.sha256(Path(__file__).read_bytes()+INVENTORY.read_bytes()+C.fingerprint().encode()+W.fingerprint().encode()).hexdigest()

def next_witness(state):
    inventory=W.read(INVENTORY)
    if not inventory.get('enabled'):return None
    for case in inventory['cases']:
        if not W.A.SCOPE.active(state,case['gamePk']):continue
        pk=case['gamePk'];control=state/'pipeline/control/mlb-game/clock-correction'/(pk+'.json')
        previous=W.read(control) if control.is_file() else {}
        if previous.get('status') in SUCCESS:continue
        if previous.get('implementationSha256')==fingerprint() and previous.get('attempts',0)>=2:continue
        return dict(gamePk=pk,path=str(state/case['path']),sha256=case['sha256'])

def tick(state,game_pk,witness,java,mapper,classpath):
    if not W.A.SCOPE.active(state,game_pk):return dict(gamePk=game_pk,status='outside-active-scope')
    control=state/'pipeline/control/mlb-game/clock-correction'/(game_pk+'.json')
    previous=W.read(control) if control.is_file() else {};version=fingerprint()
    if previous.get('status') in SUCCESS:return previous
    if previous.get('implementationSha256')==version and previous.get('attempts',0)>=2:return previous
    result=dict(gamePk=game_pk,implementationSha256=version,checkedAtUtc=W.TX.now(),
        attempts=previous.get('attempts',0)+1 if previous.get('implementationSha256')==version else 1)
    try:
        result.update(W.add_game(state,game_pk,witness,java,mapper,classpath,repair=dict(
            decisions=dict(decision=DECISION),select=select,execution_inputs=execution_inputs,
            removals=removals,revalidate=revalidate,validation_scope='corrected-clock-census-and-retained-unrelated-admissions')))
    except Exception as error:result.update(status='failed',error=str(error))
    W.atomic(control,result);return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-root',type=Path,required=True);parser.add_argument('--next',action='store_true')
    for key in ('java','mapper','jena-classpath','input'):parser.add_argument('--'+key,type=Path)
    parser.add_argument('--game-pk');parser.add_argument('--input-sha256');args=parser.parse_args()
    if args.next:print(json.dumps(next_witness(args.state_root)));raise SystemExit(0)
    if not all((args.java,args.mapper,args.jena_classpath,args.input,args.game_pk,args.input_sha256)):
        parser.error('Execution requires the retained witness and tool paths')
    result=tick(args.state_root,args.game_pk,dict(gamePk=args.game_pk,path=str(args.input),sha256=args.input_sha256),
        args.java,args.mapper,args.jena_classpath)
    print(json.dumps(result));raise SystemExit(result['status']=='failed')
