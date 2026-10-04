"""P1's one approved graph correction, through the existing game transaction."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from rdflib import Graph, Namespace, URIRef

HERE=Path(__file__).resolve().parent
def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
W=module(HERE/'targeted-award-addition.py','pitcher_transaction')
P=module(HERE/'pitcher-participation.py','pitcher_source')
ROOT=W.ROOT
DECISION='archive/design-records/mlb-game-actual-pitcher-participation/review.json'
EVIDENCE=ROOT/'archive/design-records/mlb-game-actual-pitcher-participation/evidence.json'
MAPS=('PitchActMap','PlateAppearancePitcherParticipantMap','PitcherRoleMap',
      'PitcherRoleStasisMap','PitcherRoleStasisIntervalMap')
SUCCESS={'complete','already-complete','already-present'}


def select(raw,game_pk):
    case=W.read(EVIDENCE)
    if game_pk!=case['gamePk'] or hashlib.sha256(raw).hexdigest()!=case['sourceWitness']['sha256']:
        raise ValueError('P1 correction leaves its approved game/source scope')
    census=P.census(raw,game_pk);change=case['correction'];pa=str(case['atBatIndex'])
    rows=[r for r in census['pitches'] if r['playId']==change['earlierPitch'] and r['atBatIndex']==pa]
    if (len(rows)!=1 or rows[0]['playerId']!=change['outgoingPitcher']
            or any(r['atBatIndex']==pa for r in census['issues'])):
        raise ValueError('P1 exact physical pitcher is not reconciled')
    return dict(gamePk=game_pk,pitches=rows,issues=[])


def execution_inputs(raw,game_pk,selected,context,mapping):
    doc=json.loads(raw);venue=str(doc['gameData']['venue']['id'])
    if not venue.isdecimal():raise ValueError('P1 venue identity is invalid')
    row=selected['pitches'][0]
    event=next(e for p in doc['liveData']['plays']['allPlays'] for e in p['playEvents']
        if e.get('playId')==row['playId'])
    event=dict(event,_baseballO=dict(atBatIndex=row['atBatIndex'],pitcherId=row['playerId']))
    W.atomic(context,dict(gamePk=int(game_pk),_baseballO=dict(pitcherRoleBearers=[dict(playerId=row['playerId'])]),
        liveData=dict(plays=dict(allPlays=[dict(playEvents=[event],_baseballO=dict(
            pitcherParticipations=[dict(atBatIndex=row['atBatIndex'],playerId=row['playerId'])]))]))))
    W.A.subset_mapping(game_pk,mapping,MAPS)
    mapping.write_text(mapping.read_text(encoding='utf-8').replace('{$.gameData.venue.id}',venue),
        encoding='utf-8',newline='\n')


def approved_delta():
    case=W.read(EVIDENCE);change=case['correction'];base=P.BASE+'game/'+case['gamePk']
    pitch=URIRef(base+'/pitch/'+change['earlierPitch']);pa=URIRef(base+'/plate-appearance/'+str(case['atBatIndex']))
    old=URIRef(P.BASE+'player/'+change['incomingPitcher']);new=URIRef(P.BASE+'player/'+change['outgoingPitcher'])
    obo=Namespace('http://purl.obolibrary.org/obo/');removed=Graph();added=Graph()
    for graph,person in ((removed,old),(added,new)):
        graph.add((pitch,obo.BFO_0000057,person))
        graph.add((pitch,obo.BFO_0000055,URIRef(str(person)+'/role/pitcher')))
    added.add((pa,obo.BFO_0000057,new))
    return removed,added


def removals(base,delta,game_pk,selected):
    """Mechanical scope check: only the approved two removals/three additions."""
    if game_pk!=W.read(EVIDENCE)['gamePk']:raise ValueError('P1 game differs')
    old,new=approved_delta()
    if len(delta-base-new) or len(new-delta):raise ValueError('P1 RML delta exceeds or omits the approved correction')
    present=old & base
    if len(present)==0 and len(new-base)==0:return Graph()  # Already corrected.
    if len(present)!=2 or len(new-base)!=3:raise ValueError('P1 live graph differs from the approved correction inventory')
    return old


def revalidate(*args):
    return W.revalidate(*args,shape_text=P.shapes,decisions=dict(decision=DECISION))


def fingerprint():
    return hashlib.sha256(Path(__file__).read_bytes()+Path(P.__file__).read_bytes()+P.SHAPE.read_bytes()
        +W.fingerprint().encode()+(ROOT/DECISION).read_bytes()+EVIDENCE.read_bytes()).hexdigest()


def next_witness(state):
    case=W.read(EVIDENCE);pk=case['gamePk']
    if not W.A.SCOPE.active(state,pk):return None
    path=state/'pipeline/control/mlb-game/pitcher-correction'/(pk+'.json')
    previous=W.read(path) if path.is_file() else {}
    if previous.get('status') in SUCCESS:return None
    if previous.get('implementationSha256')==fingerprint() and previous.get('attempts',0)>=2:return None
    if not (state/'pipeline/evidence/nifi/game-promotion'/pk).is_dir():return None
    return dict(case['sourceWitness'],repairKind='pitcher-correction')


def tick(state,game_pk,witness,java,mapper,classpath):
    if not W.A.SCOPE.active(state,game_pk):return dict(gamePk=game_pk,status='outside-active-scope')
    control=state/'pipeline/control/mlb-game/pitcher-correction'/(game_pk+'.json')
    version=fingerprint();previous=W.read(control) if control.is_file() else {}
    if previous.get('status') in SUCCESS:return previous
    if previous.get('implementationSha256')==version and previous.get('attempts',0)>=2:return previous
    result=dict(gamePk=game_pk,implementationSha256=version,checkedAtUtc=W.TX.now(),
        attempts=previous.get('attempts',0)+1 if previous.get('implementationSha256')==version else 1)
    try:
        result.update(W.add_game(state,game_pk,witness,java,mapper,classpath,repair=dict(
            decisions=dict(decision=DECISION),select=select,execution_inputs=execution_inputs,removals=removals,
            revalidate=revalidate,validation_scope='p1-actual-pitcher-and-retained-admissions')))
    except Exception as error:result.update(status='failed',error=str(error))
    W.atomic(control,result);return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-root',type=Path,required=True);parser.add_argument('--next',action='store_true')
    for key in ('java','mapper','jena-classpath','input'):parser.add_argument('--'+key,type=Path)
    parser.add_argument('--game-pk');parser.add_argument('--input-sha256');args=parser.parse_args()
    if args.next:
        print(json.dumps(next_witness(args.state_root)));raise SystemExit(0)
    if not all((args.java,args.mapper,args.jena_classpath,args.input,args.game_pk,args.input_sha256)):
        parser.error('Execution requires game, retained input/hash, Java, mapper and Jena classpath')
    result=tick(args.state_root,args.game_pk,dict(path=str(args.input),sha256=args.input_sha256),
        args.java,args.mapper,args.jena_classpath)
    print(json.dumps(result));raise SystemExit(result['status']=='failed')
