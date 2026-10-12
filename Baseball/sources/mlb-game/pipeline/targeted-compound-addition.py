"""NiFi-owned K1: recorded bounded responses and additive compound-result facts."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request

import importlib.util
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('compound_transaction',HERE/'targeted-award-addition.py')
W=importlib.util.module_from_spec(spec);spec.loader.exec_module(W)
ROOT=W.ROOT
DECISION='archive/design-records/mlb-game-strikeout-double-play/review.json'
CASES={'823327':(46,802139),'823489':(6,641355),'824301':(40,672695),
       '824302':(17,694249),'824866':(42,663886)}
FOLLOWUP=HERE/'compound-repair-candidates.json'
SUCCESS={'complete','already-complete','already-present'}
SHAPE=HERE.parent/'shacl/compound-result-addition.ttl'
C=W.C.CONTEXT


def cases():
    recorded=W.read(FOLLOWUP)
    selected={pk:[value] for pk,value in CASES.items()}
    for row in recorded['cases']:
        value=(row['atBatIndex'],row['batterId'])
        members=selected.setdefault(row['gamePk'],[])
        if value not in members:members.append(value)
    return {pk:sorted(values) for pk,values in selected.items()}


def completed(previous,game_pk):
    if previous.get('status') not in SUCCESS:return False
    expected=[list(value) for value in cases()[game_pk]]
    if previous.get('selectedTurns') is not None:return previous['selectedTurns']==expected
    # These exact single-turn jobs predate the multi-turn receipt. Preserve
    # their successful result, without letting it hide a later distinct scope.
    legacy=dict(CASES,**{'824385':(35,701678)})
    return game_pk in legacy and expected==[list(legacy[game_pk])]


def decisions(game_pk):
    result=dict(decision=DECISION)
    if game_pk not in CASES:result['scopeDecision']=W.read(FOLLOWUP)['scopeDecision']
    return result


def approved(game_pk):
    if game_pk not in cases() or any(W.read(ROOT/path)['status']!='accepted' for path in decisions(game_pk).values()):
        raise ValueError('Game is outside accepted K1 scope')


def select(raw,game_pk):
    approved(game_pk)
    doc=json.loads(raw)
    if str(doc.get('gamePk'))!=game_pk:raise ValueError('K1 response game differs')
    source=W.C.B.SOURCE.reconcile(raw,game_pk)
    if source['blockingIssues']:raise ValueError('K1 source membership is not reconciled')
    game='https://baseballontology.org/data/game/'+game_pk
    selections=[]
    for pa,batter in cases()[game_pk]:
        plays=[p for p in doc['liveData']['plays']['allPlays'] if p['atBatIndex']==pa]
        if len(plays)!=1 or plays[0]['matchup']['batter']['id']!=batter:
            raise ValueError('K1 selected participant or PA changed')
        parts=C.compound_double_play_parts(plays[0])
        if len(parts)!=2:raise ValueError('K1 selected compound play is unsupported: '+str(pa))
        selections.append(dict(pa=game+'/plate-appearance/'+str(pa),
            result=game+'/plate-appearance/'+str(pa)+'/result',parts=parts))
    return dict(gamePk=game_pk,plateAppearances=selections,
        parts=[part for selection in selections for part in selection['parts']],
        sourceSha256=hashlib.sha256(raw).hexdigest())


def execution_inputs(raw,game_pk,selected,context,mapping):
    W.atomic(context,dict(gamePk=int(game_pk),**{C.CONTEXT_KEY:dict(compoundDoublePlayParts=selected['parts'])}))
    W.A.subset_mapping(game_pk,mapping,('CompoundDoublePlayMap',))


def shapes(game_pk,selected):
    if 'plateAppearances' in selected:
        return '\n'.join(shapes(game_pk,entry).replace('<urn:baseballo:compound-result-addition>',
            '<urn:baseballo:compound-result-addition/'+entry['pa'].rsplit('/',1)[-1]+'>')
            for entry in selected['plateAppearances'])
    text=SHAPE.read_text(encoding='utf-8')
    for key in ('pa','result'):text=text.replace('__'+key.upper()+'__',selected[key])
    values=[]
    for part in selected['parts']:
        outcome=f"https://baseballontology.org/data/game/{game_pk}/runner-resolution/out/{part['atBatIndex']}/{part['runnerIndex']}"
        person='https://baseballontology.org/data/player/'+part['runnerId']
        values.append(f'{{ BIND(<{outcome}> AS ?out) BIND(<{person}> AS ?player) }}')
    return text.replace('__PARTS__',' UNION '.join(values))


def revalidate(marker,manifest,rdf,evidence,java,classpath,selected,game_pk,delta):
    return W.revalidate(marker,manifest,rdf,evidence,java,classpath,selected,game_pk,delta,
        shape_text=shapes,decisions=decisions(game_pk))


def input_directory(state,game_pk):
    scope=hashlib.sha256(json.dumps(cases()[game_pk]).encode()).hexdigest()[:16]
    return state/'pipeline/quarantine/mlb-game'/game_pk/('targeted-k1-'+scope)


def needs_retirement(state,result):
    if not result.get('promotionEvidence') or result.get('rawRetiredAfterPromotion'):return False
    return Path(result.get('sourceWitness',{}).get('path','')).resolve()==(input_directory(state,result['gamePk'])/'input.json').resolve()


def retire_input(state,result):
    if not needs_retirement(state,result):return result
    witness=result['sourceWitness'];source=input_directory(state,result['gamePk'])/'input.json'
    promoted=Path(result['promotionEvidence']);marker=W.read(promoted)
    if str(marker.get('gamePk'))!=result['gamePk'] or marker.get('targetedAddition',{}).get('sourceWitness')!=witness:
        raise ValueError('Compound input retirement differs from its promotion')
    path=source.with_name('retirement.json')
    identity=dict(sourceSha256=witness['sha256'],promotionEvidence=str(promoted),promotionManifestSha256=W.sha(promoted))
    if path.is_file():
        if any(W.read(path).get(k)!=v for k,v in identity.items()):raise ValueError('Compound retirement evidence changed')
    elif not source.is_file():raise ValueError('Compound input vanished before retirement')
    W.atomic(path,dict(identity,rawRetiredAfterPromotion=False))
    if source.is_file():
        if W.sha(source)!=witness['sha256']:raise ValueError('Compound retirement input changed')
        source.unlink()  # The exact owned file above, never the retained source copy.
    W.atomic(path,dict(identity,rawRetiredAfterPromotion=True,retiredAtUtc=W.TX.now()))
    return dict(result,rawRetiredAfterPromotion=True)


def acquire(state,game_pk):
    """The existing game endpoint, bounded to the accepted repair manifest.

    Keep failed/unresolved inputs for the existing source-owned admission retry.
    An acquired witness is never relabeled as the original promotion source.
    """
    approved(game_pk)
    directory=input_directory(state,game_pk)
    manifest=directory/'acquisition.json';source=directory/'input.json'
    if manifest.is_file():
        witness=W.read(manifest)
        if not source.is_file() or W.sha(source)!=witness['sha256']:
            raise ValueError('K1 retained acquisition changed')
        return witness
    retained=None;url=f'https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live'
    if source.is_file():
        raw=source.read_bytes()  # Resume an interrupted copy/acquisition.
        retained=dict(path=str(source),sha256=W.sha(source))
    else:
        candidates=sorted((state/'pipeline/quarantine/mlb-game'/game_pk).glob('*/input.json'))
        candidates.extend(sorted((ROOT/'data/raw/samples').rglob(game_pk+'.json')))
        original={r['originalSourceSha256'] for r in W.read(FOLLOWUP)['cases'] if r['gamePk']==game_pk}
        candidates.sort(key=lambda p:(W.sha(p) not in original,str(p)))
        if candidates:
            raw=candidates[0].read_bytes();retained=dict(path=str(candidates[0]),sha256=hashlib.sha256(raw).hexdigest())
        else:
            request=urllib.request.Request(url,headers={'Accept':'application/json'})
            with urllib.request.urlopen(request,timeout=60) as response:raw=response.read()
    doc=json.loads(raw)
    if str(doc.get('gamePk'))!=game_pk:raise ValueError('Acquired source identity differs')
    directory.mkdir(parents=True,exist_ok=True)
    # A hash-named temporary file is replaced atomically; no existing raw bytes
    # are rewritten, including an acquisition interrupted before its manifest.
    if source.exists():
        if source.read_bytes()!=raw:raise ValueError('K1 interrupted acquisition retained different source bytes')
    else:
        temporary=directory/'input.pending';temporary.write_bytes(raw);temporary.replace(source)
    witness=dict(kind='retained-response-copy' if retained else 'targeted-reacquisition',path=str(source),sha256=W.sha(source),
        url=url,gamePk=game_pk,**decisions(game_pk),acquiredAtUtc=W.TX.now())
    if retained:witness['retainedSource']=retained
    if game_pk not in CASES:witness['repairManifestSha256']=W.sha(FOLLOWUP)
    W.atomic(manifest,witness);return witness


def fingerprint():
    return hashlib.sha256(Path(__file__).read_bytes()+FOLLOWUP.read_bytes()+SHAPE.read_bytes()+W.fingerprint().encode()
        +(ROOT/DECISION).read_bytes()).hexdigest()


def next_game(state):
    version=fingerprint()
    for number,game_pk in enumerate(cases()):
        if not W.A.SCOPE.active(state,game_pk):continue
        approved(game_pk)
        path=state/'pipeline/control/mlb-game/compound-addition'/(game_pk+'.json')
        previous=W.read(path) if path.is_file() else {}
        if completed(previous,game_pk):
            if needs_retirement(state,previous):return game_pk
            continue
        if previous.get('implementationSha256')==version and previous.get('attempts',0)>=2:
            if number==0:return None
            continue
        return game_pk
    return None


def tick(state,game_pk,java,mapper,classpath):
    if not W.A.SCOPE.active(state,game_pk):return dict(gamePk=game_pk,status='outside-active-scope')
    approved(game_pk)
    control=state/'pipeline/control/mlb-game/compound-addition'/(game_pk+'.json')
    previous=W.read(control) if control.is_file() else {};version=fingerprint()
    if completed(previous,game_pk):
        result=retire_input(state,previous);W.atomic(control,result);return result
    if previous.get('implementationSha256')==version and previous.get('attempts',0)>=2:return previous
    result=dict(gamePk=game_pk,checkedAtUtc=W.TX.now(),implementationSha256=version,
        selectedTurns=[list(value) for value in cases()[game_pk]],
        attempts=previous.get('attempts',0)+1 if previous.get('implementationSha256')==version else 1)
    try:
        witness=acquire(state,game_pk)
        result.update(W.add_game(state,game_pk,witness,java,mapper,classpath,repair=dict(
            decisions=decisions(game_pk),select=select,execution_inputs=execution_inputs,
            revalidate=revalidate,validation_scope='selected-k1-compound-result-and-retained-admissions')))
        result['acquiredInputs']=int(witness['kind']=='targeted-reacquisition')
    except Exception as error:result.update(status='failed',error=str(error))
    W.atomic(control,result)  # Preserve promotion before cleanup; a crash resumes cleanup only.
    if completed(result,game_pk):
        result=retire_input(state,result);W.atomic(control,result)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-root',type=Path,required=True);parser.add_argument('--next',action='store_true')
    for key in ('java','mapper','jena-classpath'):parser.add_argument('--'+key,type=Path)
    parser.add_argument('--game-pk');args=parser.parse_args()
    if args.next:print(json.dumps(next_game(args.state_root)));raise SystemExit(0)
    if not all((args.java,args.mapper,args.jena_classpath,args.game_pk)):parser.error('Execution arguments required')
    result=tick(args.state_root,args.game_pk,args.java,args.mapper,args.jena_classpath)
    print(json.dumps(result));raise SystemExit(result['status']=='failed')
