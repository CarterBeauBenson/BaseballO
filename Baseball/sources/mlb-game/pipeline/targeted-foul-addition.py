"""NiFi repairs recorded missing second-foul strikes with unchanged mappings."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import urllib.request

from rdflib import Graph, Namespace

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('foul_transaction',HERE/'targeted-award-addition.py')
W=importlib.util.module_from_spec(spec);spec.loader.exec_module(W)
C=W.C;ROOT=W.ROOT
DECISION='archive/design-records/mlb-game-counted-foul-completion/review.json'
SCOPE='archive/design-records/metric-repair-scope-2026-09-30/answers.md'
MAPS=('FoulStrikeProcessMap','FoulStrikeProcessMapRecordAboutMap',
      'CountedFoulStrikeAdjudicationMap','CountedFoulStrikeDecisionMap','CountedFoulStrikeProcessPartMap')
SUCCESS={'complete','already-complete','already-present','not-applicable'}
SH=Namespace('http://www.w3.org/ns/shacl#')


def recorded_fouls(source,report):
    """Read concrete missing-class failures; this is routing, not validation."""
    missing={str(report.value(result,SH.focusNode)) for result in report.subjects(
        SH.sourceConstraintComponent,SH.ClassConstraintComponent)}
    return [dict(atBatIndex=pa['pa'].rsplit('/',1)[1],playId=event['playId'])
        for pa in source['plateAppearances'] for event in pa['events']
        if event.get('kind')=='pitch' and event.get('call')=='F' and event.get('strike') is True
        and event.get('strikesAfter')==2
        and source['game']+'/process/strike/'+event['playId'] in missing]


def fingerprint():
    return hashlib.sha256(Path(__file__).read_bytes()+C.fingerprint().encode()+W.fingerprint().encode()).hexdigest()


def next_case(state,limit=25):
    control=state/'pipeline/control/mlb-game/foul-addition';path=control/'inventory.json'
    inventory=W.read(path) if path.is_file() else dict(games={})
    version=fingerprint();inspected=0
    directories=sorted((state/'pipeline/evidence/nifi/game-promotion').glob('*'),
        key=lambda p:(p.name!='822678',p.name))
    for directory in directories:
        if not directory.is_dir() or not directory.name.isdecimal():continue
        pk=directory.name
        previous=W.read(control/(pk+'.json')) if (control/(pk+'.json')).is_file() else {}
        if previous.get('status') in SUCCESS:continue
        if previous.get('implementationSha256')==version and previous.get('attempts',0)>=2:
            if pk=='822678':return None
            continue
        paths=list(directory.glob('*.json'))
        if not paths:continue
        marker_path=max(paths,key=lambda p:(W.read(p)['promotedAtUtc'],p.name));marker=W.read(marker_path)
        identity=[W.sha(marker_path),version];cached=inventory['games'].get(pk,{})
        if cached.get('identity')==identity:
            if cached.get('status')=='selected':return cached['case']
            continue
        record=dict(identity=identity,status='not-applicable');inspected+=1
        proof_path=Path(marker.get('pitchCountAdmission',''))
        if proof_path.is_file() and W.sha(proof_path)==marker.get('pitchCountAdmissionSha256'):
            proof=W.read(proof_path)
            if (proof.get('sourceReconciled') is True and proof.get('graphConforms') is False
                    and proof.get('sourceSha256')==marker['rawSha256']):
                source_path=proof_path.with_suffix('.source.json');report_path=proof_path.with_suffix('.report.ttl')
                if W.sha(source_path)!=proof['sourceCensusSha256'] or W.sha(report_path)!=proof['reportSha256']:
                    raise ValueError('Count repair evidence changed')
                source=W.read(source_path);selected=recorded_fouls(source,Graph().parse(report_path))
                if selected:
                    case=dict(gamePk=pk,selected=selected,sourceCensus=str(source_path),
                        sourceCensusSha256=W.sha(source_path),report=str(report_path),reportSha256=W.sha(report_path),
                        promotionManifestSha256=identity[0],acquisitionDecision=SCOPE)
                    record.update(status='selected',case=case)
        inventory['games'][pk]=record
        W.atomic(path,inventory)
        if record['status']=='selected':return record['case']
        if inspected>=limit:break
    return None


def acquire(state,case):
    """Prefer retained bytes, otherwise fetch only the named manifest game."""
    pk=case['gamePk'];directory=state/'pipeline/quarantine/mlb-game'/pk/'targeted-foul'
    manifest=directory/'acquisition.json';source=directory/'input.json'
    if manifest.is_file():
        witness=W.read(manifest)
        if not source.is_file() or W.sha(source)!=witness['sha256']:raise ValueError('Count repair input changed')
        return witness
    candidates=[*sorted((ROOT/'data/raw').rglob(pk+'.json')),
        *sorted((state/'pipeline/quarantine/mlb-game'/pk).glob('*/input.json'))]
    if candidates:
        retained=candidates[0]
        return dict(kind='retained-response',gamePk=pk,path=str(retained),sha256=W.sha(retained))
    url=f'https://statsapi.mlb.com/api/v1.1/game/{pk}/feed/live'
    with urllib.request.urlopen(urllib.request.Request(url,headers={'Accept':'application/json'}),timeout=60) as response:
        raw=response.read()
    if str(json.loads(raw).get('gamePk'))!=pk:raise ValueError('Acquired game identity differs')
    directory.mkdir(parents=True,exist_ok=True)
    if source.exists():
        if source.read_bytes()!=raw:raise ValueError('Interrupted acquisition retained different bytes')
    else:
        temporary=directory/'input.pending';temporary.write_bytes(raw);temporary.replace(source)
    witness=dict(kind='targeted-reacquisition',gamePk=pk,path=str(source),sha256=W.sha(source),url=url,
        acquisitionDecision=SCOPE,acquiredAtUtc=W.TX.now())
    W.atomic(manifest,witness);return witness


def select(raw,game_pk,case):
    if W.read(ROOT/DECISION)['status']!='accepted':raise ValueError('Counted foul mapping is not accepted')
    if case['gamePk']!=game_pk or str(json.loads(raw).get('gamePk'))!=game_pk:raise ValueError('Count repair game differs')
    old_path=Path(case['sourceCensus'])
    if W.sha(old_path)!=case['sourceCensusSha256']:raise ValueError('Count repair census changed')
    old=W.read(old_path);current=C.census(raw,game_pk)
    if current['status']!='reconciled':raise ValueError('Current count source is unresolved')
    wanted={(r['atBatIndex'],r['playId']) for r in case['selected']}
    if len(wanted)!=len(case['selected']) or not wanted:raise ValueError('Count repair selection is empty or duplicated')
    def members(census):
        return {(pa['pa'].rsplit('/',1)[1],e['playId']):e for pa in census['plateAppearances']
            for e in pa['events'] if e.get('kind')=='pitch'}
    original,latest=members(old),members(current)
    if any(key not in original or original[key]!=latest.get(key) for key in wanted):
        raise ValueError('Selected count identity, clocks or outcome changed')
    with tempfile.TemporaryDirectory(prefix='foul-context-') as temp:
        path=Path(temp);source=path/'input.json';output=path/'context.json';source.write_bytes(raw)
        subprocess.run([sys.executable,str(ROOT/'scripts/pipeline/prepare-rml-context.py'),str(source),str(output)],
            check=True,capture_output=True,timeout=120)
        document=W.read(output)
    selected=[]
    for play in document['liveData']['plays']['allPlays']:
        for event in play['playEvents']:
            if (str(play['atBatIndex']),event.get('playId')) not in wanted:continue
            if event.get('_baseballO',{}).get('isSecondCountedFoul') is not True:
                raise ValueError('Existing counted-foul mapping does not select '+event['playId'])
            selected.append(event)
    if len(selected)!=len(wanted):raise ValueError('Selected mapping input membership changed')
    pas={pa for pa,pid in wanted}
    return dict(gamePk=game_pk,venue=str(document['gameData']['venue']['id']),events=selected,
        source=dict(current,plateAppearances=[pa for pa in current['plateAppearances'] if pa['pa'].rsplit('/',1)[1] in pas]))


def execution_inputs(raw,game_pk,selected,context,mapping):
    W.atomic(context,dict(gamePk=int(game_pk),gameData=dict(venue=dict(id=int(selected['venue']))),
        liveData=dict(plays=dict(allPlays=[dict(playEvents=selected['events'])]))))
    W.A.subset_mapping(game_pk,mapping,MAPS)
    mapping.write_text(mapping.read_text(encoding='utf-8').replace('{$.gameData.venue.id}',selected['venue']),
        encoding='utf-8',newline='\n')


def shapes(game_pk,selected):
    return C.shape_text(selected['source'])


def revalidate(*args):
    return W.revalidate(*args,shape_text=shapes,decisions=dict(decision=DECISION))


def finish(state,game_pk,witness,java,classpath):
    # Reuse the admission owner's existing stage. Preserve the new response's
    # census before retiring only this repair's successfully promoted input.
    E=W.module(HERE/'admission-evidence.py','foul_admission_owner')
    directory=state/'pipeline/evidence/nifi/game-promotion'/game_pk
    marker=max(directory.glob('*.json'),key=lambda p:(W.read(p)['promotedAtUtc'],p.name))
    promotion=W.I.validated_promotion_record(state,marker,game_pk,W.I.query_index_contract_admission())
    results=E.refresh_existing_graph(state,promotion,witness,java,classpath,'http://127.0.0.1:3031/baseball-dev/query')
    if witness['kind']=='targeted-reacquisition':
        source=Path(witness['path']);owned=state/'pipeline/quarantine/mlb-game'/game_pk/'targeted-foul/input.json'
        if source.resolve()!=owned.resolve() or W.sha(source)!=witness['sha256']:
            raise ValueError('Source retirement differs from this repair input')
        W.atomic(source.with_name('retirement.json'),dict(sourceSha256=witness['sha256'],
            promotionManifestSha256=W.sha(marker),retiredAtUtc=W.TX.now()))
        source.unlink()
    return {family:status for _,family,status in results}


def tick(state,case,java,mapper,classpath):
    pk=case['gamePk'];control=state/'pipeline/control/mlb-game/foul-addition'/(pk+'.json')
    previous=W.read(control) if control.is_file() else {};version=fingerprint()
    if previous.get('status') in SUCCESS:return previous
    if previous.get('implementationSha256')==version and previous.get('attempts',0)>=2:return previous
    result=dict(gamePk=pk,case=case,checkedAtUtc=W.TX.now(),implementationSha256=version,
        attempts=previous.get('attempts',0)+1 if previous.get('implementationSha256')==version else 1)
    try:
        witness=acquire(state,case)
        result.update(W.add_game(state,pk,witness,java,mapper,classpath,repair=dict(decisions=dict(decision=DECISION),
            select=lambda raw,game:select(raw,game,case),execution_inputs=execution_inputs,revalidate=revalidate,
            validation_scope='selected-counted-foul-pas-and-retained-admissions')))
        if result['status'] in SUCCESS:result['admissionOutcomes']=finish(state,pk,witness,java,classpath)
    except Exception as error:result.update(status='failed',error=str(error))
    W.atomic(control,result);return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-root',type=Path,required=True);parser.add_argument('--next',action='store_true')
    for key in ('java','mapper','jena-classpath'):parser.add_argument('--'+key,type=Path)
    parser.add_argument('--game-pk');args=parser.parse_args()
    if args.next:print(json.dumps(next_case(args.state_root)));raise SystemExit(0)
    if not all((args.java,args.mapper,args.jena_classpath,args.game_pk)):parser.error('Execution arguments required')
    case=W.read(args.state_root/'pipeline/control/mlb-game/foul-addition/inventory.json')['games'][args.game_pk]['case']
    result=tick(args.state_root,case,args.java,args.mapper,args.jena_classpath)
    print(json.dumps(result));raise SystemExit(result['status']=='failed')
