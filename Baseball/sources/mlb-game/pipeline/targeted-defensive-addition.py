"""NiFi-owned D1 additions from retained responses, using four existing maps."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import importlib.util

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('defensive_transaction',HERE/'targeted-award-addition.py')
W=importlib.util.module_from_spec(spec);spec.loader.exec_module(W)
ROOT=W.ROOT
D=W.module(HERE/'defensive-admission.py','defensive_addition_contract')
DECISION='archive/design-records/mlb-game-defensive-acts/review.json'
MAPS=('DefensiveActMap','DefensiveCatchFieldingMap','DefensiveRoleMap','DefensiveRecordMap')
SUCCESS={'complete','already-complete','already-present','not-applicable'}


def select(raw,game_pk):
    if W.read(ROOT/DECISION)['status']!='accepted':raise ValueError('D1 is not accepted')
    source=D.census(raw,game_pk)
    if source['status']!='reconciled':raise ValueError('D1 source membership is unresolved')
    return source if source['acts'] else None


def execution_inputs(raw,game_pk,selected,context,mapping):
    W.atomic(context,dict(gamePk=int(game_pk),**{D.CONTEXT.CONTEXT_KEY:dict(defensiveActs=selected['acts'])}))
    W.A.subset_mapping(game_pk,mapping,MAPS)


def shapes(game_pk,selected):
    if selected['gamePk']!=game_pk:raise ValueError('D1 selected game differs')
    return D.shape_text(selected)


def revalidate(marker,manifest,rdf,evidence,java,classpath,selected,game_pk,delta):
    # The old incomplete defensive census intentionally lacks these acts.
    # Replace only that census with the current, independently sourced D1
    # census; all unrelated admission reports retain their exact expectations.
    proof_path=marker.get('defensiveAdmission');proof_hash=marker.get('defensiveAdmissionSha256')
    if bool(proof_path)!=bool(proof_hash):raise ValueError('Retained D1 proof reference is incomplete')
    if proof_path:
        original_proof=Path(proof_path)
        if W.sha(original_proof)!=proof_hash:raise ValueError('Retained D1 proof changed')
        if W.read(original_proof)['status']=='admitted' and not selected['populationComplete']:
            raise ValueError('D1 addition would regress a complete admitted population')
    # Legacy promotions predate D1's census. Absence is not a failed proof:
    # the selected current census and unchanged SHACL below still have to pass.
    prior={k:v for k,v in marker.items() if k not in {'defensiveAdmission','defensiveAdmissionSha256'}}
    fields=W.revalidate(prior,manifest,rdf,evidence,java,classpath,selected,game_pk,delta,
        shape_text=shapes,decisions=dict(decision=DECISION))
    output=evidence/'defensive-admission.json';original=D.census
    D.census=lambda raw,game_pk:copy.deepcopy(selected)
    try:proof=D.prove(raw=b'',game_pk=game_pk,rdf_path=rdf,output=output,java=java,classpath=classpath)
    finally:D.census=original
    if not proof['graphConforms']:raise ValueError('D1 current census does not conform')
    # Preserve the witness's actual source hash, even if it differs from the
    # original promotion. Ordinary admission refresh owns independent-witness
    # receipts; this addition never grants a complete metric population.
    proof['graphRevalidation']=dict(decision=DECISION,mode='current-defensive-source-census',
        promotionSourceSha256=marker['rawSha256'],originalProofSha256=marker.get('defensiveAdmissionSha256'))
    W.atomic(output,proof)
    return dict(fields,defensiveAdmission=str(output),defensiveAdmissionSha256=W.sha(output))


def fingerprint():
    return hashlib.sha256(Path(__file__).read_bytes()+D.fingerprint().encode()+W.fingerprint().encode()).hexdigest()


def next_witness(state,limit=25):
    control=state/'pipeline/control/mlb-game/defensive-addition';path=control/'inventory.json'
    inventory=W.read(path) if path.is_file() else dict(inputs={})
    fixture=ROOT/'data/raw/samples/2026-08-25/822693.json'
    paths=[fixture,*sorted((state/'pipeline/quarantine/mlb-game').glob('*/*/input.json')),
           *sorted((ROOT/'data/raw').rglob('*.json'))]
    version=fingerprint();inspected=0;seen=set()
    for source in paths:
        if source in seen:continue
        seen.add(source)
        try:metadata=source.stat()
        except FileNotFoundError:continue
        cached=inventory['inputs'].get(str(source),{})
        promoted=state/'pipeline/evidence/nifi/game-promotion';prior_pk=cached.get('gamePk','')
        identity=[metadata.st_size,metadata.st_mtime_ns,version,bool(prior_pk.isdecimal() and (promoted/prior_pk).is_dir())]
        if cached.get('identity')==identity and cached.get('status')!='selected':continue
        try:raw=source.read_bytes()
        except FileNotFoundError:continue
        try:doc=json.loads(raw)
        except (ValueError,UnicodeError) as error:
            inventory['inputs'][str(source)]=dict(identity=identity,sha256=hashlib.sha256(raw).hexdigest(),
                gamePk='',status='invalid-input',error=str(error))
            inspected+=1
            if inspected>=limit:break
            continue
        pk=str(doc.get('gamePk','')) if isinstance(doc,dict) else ''
        identity[-1]=bool(pk.isdecimal() and (promoted/pk).is_dir())
        record=dict(identity=identity,sha256=hashlib.sha256(raw).hexdigest(),gamePk=pk,status='not-applicable')
        if identity[-1]:
            checkpoint=control/(pk+'.json');previous=W.read(checkpoint) if checkpoint.is_file() else {}
            if previous.get('status') in SUCCESS and previous.get('implementationSha256')==version and previous.get('sourceSha256')==record['sha256']:record['status']='complete'
            elif previous.get('implementationSha256')==version and previous.get('sourceSha256')==record['sha256'] and previous.get('attempts',0)>=2:record['status']='retry-exhausted'
            else:
                try:
                    selected=select(raw,pk)
                    if selected:record.update(status='selected',actCount=len(selected['acts']))
                except (KeyError,ValueError,TypeError) as error:record.update(status='unresolved-source',error=str(error))
        inventory['inputs'][str(source)]=record;inspected+=1
        if record['status']=='selected':
            W.atomic(path,inventory)
            return dict(kind='retained-response',gamePk=pk,path=str(source),sha256=record['sha256'])
        if inspected>=limit:break
    W.atomic(path,inventory);return None


def tick(state,witness,java,mapper,classpath):
    pk=witness['gamePk'];control=state/'pipeline/control/mlb-game/defensive-addition'/(pk+'.json')
    previous=W.read(control) if control.is_file() else {};version=fingerprint()
    if previous.get('status') in SUCCESS and previous.get('implementationSha256')==version and previous.get('sourceSha256')==witness['sha256']:return previous
    if previous.get('implementationSha256')==version and previous.get('sourceSha256')==witness['sha256'] and previous.get('attempts',0)>=2:return previous
    result=dict(gamePk=pk,implementationSha256=version,sourceSha256=witness['sha256'],checkedAtUtc=W.TX.now(),
        attempts=previous.get('attempts',0)+1 if previous.get('implementationSha256')==version and previous.get('sourceSha256')==witness['sha256'] else 1)
    try:result.update(W.add_game(state,pk,witness,java,mapper,classpath,repair=dict(
        decisions=dict(decision=DECISION),select=select,execution_inputs=execution_inputs,
        revalidate=revalidate,validation_scope='selected-d1-acts-current-census-and-retained-unrelated-admissions')))
    except Exception as error:result.update(status='failed',error=str(error))
    W.atomic(control,result);return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-root',type=Path,required=True);parser.add_argument('--next',action='store_true')
    for key in ('java','mapper','jena-classpath'):parser.add_argument('--'+key,type=Path)
    parser.add_argument('--source',type=Path);parser.add_argument('--game-pk');parser.add_argument('--source-sha256');args=parser.parse_args()
    if args.next:print(json.dumps(next_witness(args.state_root)));raise SystemExit(0)
    if not all((args.java,args.mapper,args.jena_classpath,args.source,args.game_pk,args.source_sha256)):parser.error('Execution arguments required')
    witness=dict(kind='retained-response',gamePk=args.game_pk,path=str(args.source),sha256=args.source_sha256)
    result=tick(args.state_root,witness,args.java,args.mapper,args.jena_classpath)
    print(json.dumps(result));raise SystemExit(result['status']=='failed')
