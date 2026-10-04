"""NiFi's targeted runner additions over explicitly inventoried retained inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from rdflib import Graph, Namespace, URIRef

HERE=Path(__file__).resolve().parent
import importlib.util
spec=importlib.util.spec_from_file_location('r1_additive_transaction',HERE/'targeted-award-addition.py')
W=importlib.util.module_from_spec(spec);spec.loader.exec_module(W)
ROOT=W.ROOT
DECISION='archive/design-records/mlb-game-runner-pattern-completion/review.json'
INVENTORY=ROOT/Path(DECISION).parent/'candidate-inventory.json'
RECOVERY=HERE/'runner-history-recovery.json'
SHAPE=HERE.parent/'shacl/runner-pattern-addition.ttl'
P=W.module(HERE/'pa-resolution-admission.py','r1_resolution_shapes')
H=W.A.H
B=W.module(HERE/'runner-boundary-admission.py','r1_boundary_shapes')
CONTEXT=W.C.CONTEXT
MAPS=W.DEPENDENCY_MAPS+('SafeDestinationIdentifierMap','SegmentOriginDesignationMap',
    'SegmentOriginBaseMap','SegmentOriginBaseIdentifierMap','BattedBallRunnerResolutionContainmentMap',
    'PersonalRunnerProcessMap','PersonalRunnerIntervalMap','PersonalRunnerMembershipMap',
    'PersonalRunnerGameEndIntervalMap','RunnerPlacementJudgmentMap','RunnerPlacementMembershipMap',
    'RunnerPlacementDecisionMap','RunnerPlacementBaseMap','RunnerPlacementBaseIdentifierMap',
    'RunnerPlacementRuleMap','RunnerPlacementRecordMap')+W.MAPS
BOUNDARY_MAPS=('PlateAppearanceStartOutCountMap','PlateAppearanceStartRunnerParticipantMap',
    'BaserunnerAtBaseStasisMap','BaserunnerAtBaseStasisIntervalMap',
    'PlateAppearanceStartRunnerLocationMap','PlateAppearanceStartBaseArtifactMap',
    'PlateAppearanceStartBaseIdentifierMap','PlateAppearanceStartBaseSiteMap')
SUCCESS={'complete','already-complete','already-present'}


def repair_cases():
    # The later execution request does not amend R1's archived 26-game decision.
    return W.read(INVENTORY)['games']+W.read(RECOVERY)['games']


def approved_case(game_pk):
    if W.read(ROOT/DECISION)['status']!='accepted':raise ValueError('R1 is not accepted')
    case=next((g for g in repair_cases() if g['gamePk']==game_pk),None)
    if case is None:raise ValueError('Game is outside the approved R1 inventory')
    return case


def prepared_boundaries(raw):
    """Use the unchanged context owner, then discard all unselected products."""
    with tempfile.TemporaryDirectory(prefix='baseballo-runner-context-') as directory:
        source=Path(directory)/'input.json';output=Path(directory)/'context.json'
        source.write_bytes(raw)
        completed=subprocess.run([sys.executable,'-B',str(B.CONTEXT_PATH),str(source),str(output)],
            capture_output=True,text=True,encoding='utf-8',timeout=120)
        if completed.returncode:
            raise ValueError('Runner boundary context failed: '+completed.stderr[-4000:])
        document=W.read(output)
    return {str(play['atBatIndex']):dict(about=dict(atBatIndex=play['about']['atBatIndex']),
        **{CONTEXT.CONTEXT_KEY:{key:play[CONTEXT.CONTEXT_KEY][key]
            for key in ('outsBefore','startBaseOccupancies')}})
        for play in document['liveData']['plays']['allPlays']}


def select(raw,game_pk):
    case=approved_case(game_pk)
    if hashlib.sha256(raw).hexdigest() not in {w['sha256'] for w in case['retainedInputs']}:
        raise ValueError('Source is outside the approved retained R1 witnesses')
    doc=json.loads(raw)
    if str(doc.get('gamePk'))!=game_pk:raise ValueError('R1 source game differs')
    source=W.C.B.SOURCE.reconcile(raw,game_pk)
    if source['blockingIssues']:raise ValueError('R1 source census is not reconciled')
    history=CONTEXT.personal_runner_histories(raw)
    doc[CONTEXT.CONTEXT_KEY]={'runnerHistoryReconciliation':history}
    selected_pas=set(case['plateAppearances'])
    boundaries=None;prepared={}
    if case.get('includeBoundaryStates'):
        boundaries=B.census(raw,game_pk)
        if boundaries['status']!='reconciled':raise ValueError('Runner boundary source remains unresolved')
        if selected_pas!={str(p['atBatIndex']) for p in doc['liveData']['plays']['allPlays']}:
            raise ValueError('Complete boundary recovery requires the exact inventoried PA census')
        prepared=prepared_boundaries(raw)
    # Complete histories are existing dependencies of the selected episodes.
    # Retain every member; never turn a truncated history into a complete one.
    history_keys={r['lifetimeKey'] for r in history['episodeMembership'] if r['atBatIndex'] in selected_pas}
    histories=[h for h in history['histories'] if h['lifetimeKey'] in history_keys]
    membership=[r for r in history['episodeMembership'] if r['lifetimeKey'] in history_keys]
    dependencies={(r['atBatIndex'],r['runnerIndex']) for r in membership}
    plays=[];episodes=[]
    for play in doc['liveData']['plays']['allPlays']:
        pa=str(play['atBatIndex'])
        products=CONTEXT.runner_episode_evidence(play,pa)
        products.update(CONTEXT.runner_metric_evidence(play,pa,str(doc['gameData']['game']['season']),document=doc))
        products['battedRunnerResolutions']=CONTEXT.batted_runner_resolution_links(play,pa,history)
        products={key:[r for r in rows if pa in selected_pas or (pa,r['runnerIndex']) in dependencies]
                  for key,rows in products.items()}
        if products['runnerEpisodes'] or pa in prepared:
            item=prepared.get(pa,{CONTEXT.CONTEXT_KEY:{}})
            item[CONTEXT.CONTEXT_KEY].update(products)
            episodes.extend(products['runnerEpisodes']);plays.append(item)
    keys={(r['atBatIndex'],r['runnerIndex']) for r in episodes}
    if not dependencies<=keys:raise ValueError('R1 history dependency has no selected existing episode')
    if not episodes:raise ValueError('R1 has no supported runner rows')
    retained_history=dict(history,histories=histories,episodeMembership=membership,
        placementAdjudications=[r for r in history['placementAdjudications'] if r['lifetimeKey'] in history_keys])
    result=dict(context=dict(gamePk=int(game_pk),gameData=dict(venue=doc['gameData']['venue']),
        liveData=dict(plays=dict(allPlays=plays)),
        **{CONTEXT.CONTEXT_KEY:dict(runnerHistoryReconciliation=retained_history)}),
        episodes=episodes,resolutionCensus=P.R.census(raw,game_pk),history=retained_history)
    if boundaries is not None:
        result.update(boundaryCensus=boundaries,executionRequest=RECOVERY.relative_to(ROOT).as_posix())
    return result


def execution_inputs(raw,game_pk,selected,context,mapping):
    venue=str(selected['context']['gameData']['venue']['id'])
    if not venue.isdecimal():raise ValueError('R1 venue identity is invalid')
    W.atomic(context,selected['context'])
    W.A.subset_mapping(game_pk,mapping,MAPS+(BOUNDARY_MAPS if 'boundaryCensus' in selected else ()))
    mapping.write_text(mapping.read_text(encoding='utf-8').replace('{$.gameData.venue.id}',venue),
                       encoding='utf-8',newline='\n')


def shapes(game_pk,selected):
    """Reuse the exact source-owned PA and history checks at the selected grain."""
    source=selected['resolutionCensus'];game=source['game']
    keys={(r['atBatIndex'],r['runnerIndex']) for r in selected['episodes']}
    pas={game+'/plate-appearance/'+pa for pa,_ in keys}
    resolution=dict(source,resolutions=[r for r in source['resolutions'] if r['pa'] in pas],
        nonMovementRecords=[r for r in source.get('nonMovementRecords',[]) if r['pa'] in pas])
    text,members=P.shape_text(dict(resolution=resolution,
        batting=dict(game=game,sourceSha256=source['sourceSha256'],members=[dict(pa=p) for p in sorted(pas)])))
    if any(m['status']!='pending' for m in members):raise ValueError('R1 selected PA source remains unresolved')
    parts=[text]
    for row in source['resolutions']:
        suffix=tuple(row['act'].rsplit('/',2)[-2:])
        if suffix not in keys:continue
        identity=SHAPE.read_text(encoding='utf-8')
        for key in ('act','pa','player','resolution','outcome'):
            identity=identity.replace('__'+key.upper()+'__',row[key])
        parts.append(identity)
    # Keep exact history membership constraints but do not claim a whole-game
    # census from selected histories. Other promoted histories remain intact.
    history_shapes=Graph().parse(data=H.shape_text(dict(game=game,history=selected['history'])),format='turtle')
    history_shapes.remove((None,Namespace('http://www.w3.org/ns/shacl#').targetNode,URIRef(game)))
    parts.append(history_shapes.serialize(format='turtle'))
    if 'boundaryCensus' in selected:parts.append(B.shape_text(selected['boundaryCensus']))
    return '\n'.join(parts)


def revalidate(*args):
    return W.revalidate(*args,shape_text=shapes,decisions=dict(decision=DECISION))


def fingerprint():
    return hashlib.sha256(Path(__file__).read_bytes()+SHAPE.read_bytes()+W.fingerprint().encode()
        +P.fingerprint().encode()+H.fingerprint().encode()+B.fingerprint().encode()
        +(ROOT/DECISION).read_bytes()+INVENTORY.read_bytes()+RECOVERY.read_bytes()).hexdigest()


def tick(state,game_pk,witness,java,mapper,classpath):
    approved_case(game_pk)
    control=state/'pipeline/control/mlb-game/runner-addition'/(game_pk+'.json')
    version=fingerprint();previous=W.read(control) if control.is_file() else {}
    if previous.get('status') in SUCCESS:return previous
    if previous.get('implementationSha256')==version and previous.get('attempts',0)>=2:return previous
    result=dict(gamePk=game_pk,implementationSha256=version,checkedAtUtc=W.TX.now(),
        attempts=previous.get('attempts',0)+1 if previous.get('implementationSha256')==version else 1)
    try:
        result.update(W.add_game(state,game_pk,witness,java,mapper,classpath,repair=dict(
            decisions=dict(decision=DECISION),select=select,execution_inputs=execution_inputs,
            revalidate=revalidate,validation_scope='selected-r1-runner-patterns-and-retained-admissions')))
    except Exception as error:result.update(status='failed',error=str(error))
    W.atomic(control,result);return result


def next_witness(state):
    version=fingerprint();control=state/'pipeline/control/mlb-game/runner-addition'
    cases=sorted(repair_cases(),key=lambda g:(g['gamePk']!='823200',g['gamePk']))
    for index,case in enumerate(cases):
        approved_case(case['gamePk'])
        path=control/(case['gamePk']+'.json');previous=W.read(path) if path.is_file() else {}
        if previous.get('status') in SUCCESS:continue
        if previous.get('implementationSha256')==version and previous.get('attempts',0)>=2:
            if index==0:return None  # Reviewed first game must pass before widening.
            continue
        for witness in case['retainedInputs']:
            source=(state/witness['path']).resolve()
            if not source.is_relative_to(state.resolve()):raise ValueError('R1 witness leaves the state directory')
            if source.is_file():return dict(gamePk=case['gamePk'],path=str(source),sha256=witness['sha256'])
        raise ValueError('Approved R1 retained input is unavailable: '+case['gamePk'])
    return None


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-root',type=Path,required=True);parser.add_argument('--next',action='store_true')
    for key in ('java','mapper','jena-classpath','input'):parser.add_argument('--'+key,type=Path)
    parser.add_argument('--game-pk');parser.add_argument('--input-sha256')
    args=parser.parse_args()
    if args.next:
        print(json.dumps(next_witness(args.state_root)));raise SystemExit(0)
    if not all((args.java,args.mapper,args.jena_classpath,args.input,args.game_pk,args.input_sha256)):
        parser.error('Execution requires game, retained input/hash, Java, mapper and Jena classpath')
    result=tick(args.state_root,args.game_pk,dict(path=str(args.input),sha256=args.input_sha256),
                args.java,args.mapper,args.jena_classpath)
    print(json.dumps(result));raise SystemExit(result['status']=='failed')
