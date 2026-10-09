"""NiFi-owned EG1/BK1: bounded missing facts for still-excluded player-games."""
import argparse
import copy
from contextlib import closing
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import urllib.request

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('eg1_runner',HERE/'targeted-runner-addition.py')
R=importlib.util.module_from_spec(spec);spec.loader.exec_module(R)
W=R.W;ROOT=R.ROOT;C=R.CONTEXT
BK=W.module(HERE/'balk-runner-attribution.py','eg1_balk')
D2=W.module(HERE/'defensive-indifference-running.py','eg1_indifference')
E=W.module(HERE/'admission-evidence.py','eg1_evidence')
K=W.module(HERE/'targeted-compound-addition.py','eg1_compound')
CONTACT=W.module(HERE/'contact-continuation-admission.py','eg1_contact')
DECISION='archive/design-records/mlb-game-empty-game-completion/review.json'
BALK_DECISION='archive/design-records/mlb-game-balk-runner-attribution/review.json'
WALK_DECISION='archive/design-records/mlb-game-automatic-ball-walk-award/review.json'
INDEPENDENT_DECISION='archive/design-records/mlb-game-defensive-indifference-running/review.json'
REVIEW_WALK_DECISION='archive/design-records/mlb-game-walk-after-reconciled-review/review.json'
INVENTORY=ROOT/Path(DECISION).parent/'candidate-inventory.json'
SUCCESS=R.SUCCESS|{'resolved-by-reader','no-supported-addition'}
PA_MAPS=('PlateAppearanceMap','PlateAppearanceIntervalMap','BatterActMap',
    'PlateAppearanceCoreContainmentMap','PlateAppearanceResultMap','PlateAppearanceResultRecordMap',
    'PlateAppearanceResultJudgmentMap','PlateAppearanceResultDecisionMap',
    'PlateAppearanceResultRecordAdjudicationMap','PlateAppearanceResultContainmentMap','CompoundDoublePlayMap')
RESULT_MAPS=tuple('ResultType_'+kind for kind in ('home_run','field_out','double','walk','force_out',
    'strikeout','single','grounded_into_double_play','sac_fly','double_play','fielders_choice','triple',
    'sac_bunt','field_error','hit_by_pitch','balk','interference'))
RUNNER_MAPS=tuple('Runner'+kind+part+'Map' for kind in ('Out','ScoreOrigin','ScoreBase','Reach','Advance')
    for part in ('Act','Resolution','Record','Judgment','Decision','AdjudicationLinks','RecordAdjudication'))
MAPS=tuple(dict.fromkeys(R.MAPS+BK.MAPS+D2.MAPS+PA_MAPS+RESULT_MAPS+RUNNER_MAPS+
    ('ReachedBaseArtifactMap','AdvancedToBaseArtifactMap','HomePlateArtifactMap','SafeRuleMap','OutRuleMap')))


def approved_case(game_pk):
    for decision in (DECISION,BALK_DECISION,WALK_DECISION,INDEPENDENT_DECISION,REVIEW_WALK_DECISION):
        if W.read(ROOT/decision)['status']!='accepted':raise ValueError('EG1 selected repair is not accepted')
    case=next((g for g in W.read(INVENTORY)['games'] if g['gamePk']==game_pk),None)
    if case is None:raise ValueError('Game is outside the approved EG1 inventory')
    return case


def outstanding(state,case,connection=None):
    """Read the latest publication; never turn an older diagnostic into work."""
    if connection is None:
        pointer=state/'serving/dashboard-current.json'
        if not pointer.is_file():return None
        publication=W.read(pointer)
        if publication['buildId']<=W.read(INVENTORY)['publicationId']:return None
        with closing(sqlite3.connect(Path(publication['databasePath']).as_uri()+'?mode=ro&immutable=1',uri=True)) as db:
            return outstanding(state,case,db)
    proof=connection.execute('SELECT proof_json FROM dashboard_player_admission WHERE graph_iri=?',
            (case['graph'],)).fetchone()
    counts=dict(connection.execute('SELECT player,plate_appearances FROM dashboard_player_game WHERE graph_iri=?',
            (case['graph'],)).fetchall())
    unknown={p['player'] for p in case['excludedPlayerGames'] if counts.get(p['player']) is None}
    # Complete whole-game B1 admission needs no individual-player proof.
    # Only selected players with unknown PA counts need the newer reader.
    if unknown:
        if not proof:return None
        individual=json.loads(proof[0])
        individual=dict(individual,players=[p for p in individual.get('players',[]) if p.get('player') in unknown])
        if E.PLAYER_PARTICIPATION.needs_compound_refresh(individual):return None
    rows=connection.execute("SELECT player,complete FROM dashboard_player_metric WHERE graph_iri=? AND metric_id='empty-game-rate'",
            (case['graph'],)).fetchall()
    current=dict(rows)
    if any(p['player'] not in current for p in case['excludedPlayerGames']):return None
    return [p['player'] for p in case['excludedPlayerGames'] if not current[p['player']]]


def prepare(raw):
    with tempfile.TemporaryDirectory(prefix='baseballo-eg1-context-') as directory:
        source=Path(directory)/'input.json';output=Path(directory)/'context.json'
        source.write_bytes(raw)
        command=subprocess.run([sys.executable,'-B',str(BK.CONTEXT_PATH),str(source),str(output)],
            capture_output=True,text=True,encoding='utf-8',timeout=120)
        if command.returncode:raise ValueError('EG1 context failed: '+command.stderr[-4000:])
        return W.read(output)


def select(raw,game_pk,players):
    case=approved_case(game_pk)
    if not set(players)<={p['player'] for p in case['excludedPlayerGames']}:
        raise ValueError('EG1 selection exceeds approved player-games')
    document=prepare(raw)
    if str(document.get('gamePk'))!=game_pk:raise ValueError('EG1 source game differs')
    player_ids={p.rsplit('/',1)[-1] for p in players}
    plays=document['liveData']['plays']['allPlays']
    pas={str(p['atBatIndex']) for p in plays if str(p.get('matchup',{}).get('batter',{}).get('id')) in player_ids
        or any(b['playerId'] in player_ids for b in p[C.CONTEXT_KEY].get('batterParticipations',[]))
        or any(r['runnerId'] in player_ids for r in p[C.CONTEXT_KEY].get('defensiveIndifferenceActs',[]))}
    if not pas:return None
    # SHACL's existing source selector distinguishes unsupported PAs. Keep them
    # as explicit gaps while repairing independent, supported PA patterns.
    census=R.P.R.census(raw,game_pk);game=census['game']
    _,members=R.P.shape_text(dict(resolution=dict(census,
        resolutions=[r for r in census['resolutions'] if r['pa'].rsplit('/',1)[-1] in pas],
        nonMovementRecords=[r for r in census.get('nonMovementRecords',[]) if r['pa'].rsplit('/',1)[-1] in pas]),
        batting=dict(game=game,sourceSha256=census['sourceSha256'],members=[dict(pa=game+'/plate-appearance/'+p) for p in sorted(pas)])))
    unsupported=[m for m in members if m['status']!='pending']
    pas={m['plateAppearance'].rsplit('/',1)[-1] for m in members if m['status']=='pending'}
    if not pas:return dict(noSupportedAddition=True,unresolved=unsupported)
    selected=R.select_case(raw,game_pk,dict(plateAppearances=sorted(pas),allowEmptyRunnerSelection=True))
    episode_keys={(r['atBatIndex'],r['runnerIndex']) for r in selected['episodes']}
    scoped={str(p['atBatIndex']):p for p in plays if str(p['atBatIndex']) in pas}
    for item in selected['context']['liveData']['plays']['allPlays']:
        rows=item[C.CONTEXT_KEY]['runnerEpisodes']
        if rows:scoped.setdefault(rows[0]['atBatIndex'],item)
    products={rows[0]['atBatIndex']:p[C.CONTEXT_KEY] for p in selected['context']['liveData']['plays']['allPlays']
        if (rows:=p[C.CONTEXT_KEY]['runnerEpisodes'])}
    originals={str(p['atBatIndex']):p for p in plays}
    balks=[];independent=[]
    for pa,play in scoped.items():
        original=originals[pa]
        play['runners']=[r for r in original.get('runners',[])
            if (pa,str(r[C.CONTEXT_KEY]['runnerIndex'])) in episode_keys]
        play[C.CONTEXT_KEY].update(products.get(pa,{}))
        rows=[r for r in original[C.CONTEXT_KEY].get('balkAdvances',[])
            if (pa,r['runnerIndex']) in episode_keys]
        play[C.CONTEXT_KEY]['balkAdvances']=rows;balks.extend(rows)
        # A selected history may continue in a later PA. Its existing complete
        # resolution check includes every runner there, so retain the approved
        # D2 type dependencies for that PA too. Only the type overlay expands;
        # runner facts and histories remain limited to the selected episodes.
        rows=original[C.CONTEXT_KEY].get('defensiveIndifferenceActs',[])
        play[C.CONTEXT_KEY]['defensiveIndifferenceActs']=rows;independent.extend(rows)
    selected['context']['liveData']['plays']['allPlays']=list(scoped.values())
    parts=[p for p in document[C.CONTEXT_KEY].get('compoundDoublePlayParts',[]) if p['atBatIndex'] in pas]
    selected['context'][C.CONTEXT_KEY]['compoundDoublePlayParts']=parts
    selected.update(balks=balks,independent=independent,plateAppearances=sorted(pas),unresolved=unsupported,players=players,
        contactCensus=CONTACT.census(raw,game_pk))
    return selected


def execution_inputs(raw,game_pk,selected,context,mapping):
    W.atomic(context,selected['context'])
    # RootSource supplies only existing constant rule/artifact dependencies.
    (context.parent/'game.json').write_bytes(raw)
    W.A.subset_mapping(game_pk,mapping,MAPS)
    venue=str(selected['context']['gameData']['venue']['id'])
    if not venue.isdecimal():raise ValueError('EG1 venue identity is invalid')
    mapping.write_text(mapping.read_text(encoding='utf-8').replace('{$.gameData.venue.id}',venue),encoding='utf-8',newline='\n')


def shapes(game_pk,selected):
    parts=[R.shapes(game_pk,selected),BK.shapes(game_pk,selected['balks']),
        D2.shapes(game_pk,selected.get('independent',[]))]
    game='https://baseballontology.org/data/game/'+game_pk
    compounds=selected['context'][C.CONTEXT_KEY]['compoundDoublePlayParts']
    for pa in {p['atBatIndex'] for p in compounds}:
        parts.append(K.shapes(game_pk,dict(pa=game+'/plate-appearance/'+pa,result=game+'/plate-appearance/'+pa+'/result',
            parts=[p for p in compounds if p['atBatIndex']==pa])))
    return '\n'.join(parts)


def project_census(field,source,selected):
    """Extend only the exact accepted selection; keep every old obligation.

    A later source may support additional histories beyond EG1's selected
    dependencies. Those are not mapped, added to the check or called complete.
    An overlapping history retains its original constraints; the addition's
    own SHACL also checks the selected source, so conflicts still fail.
    """
    updated=copy.deepcopy(source)
    provenance=dict(decision=DECISION,sourceWitness=selected['sourceWitness'],
        projectionImplementationSha256=W.sha(Path(__file__)))
    if field=='runnerResolutionAdmission':
        acts={source['game']+'/runner-act/movement/'+r['atBatIndex']+'/'+r['runnerIndex']
              for r in selected.get('independent',[])}
        changed=[]
        for row in updated['resolutions']:
            if row['act'] in acts and not row.get('stealAttempt'):
                row['stealAttempt']=True;changed.append(row['act'])
        if not changed:return None
        provenance.update(independentRunningDecision=INDEPENDENT_DECISION,updatedActTypes=sorted(changed))
        return updated,R.P.R.shape_text(updated),provenance
    if field=='runnerHistoryAdmission':
        previous={h['lifetimeKey'] for h in source['history']['histories']}
        additions=[h for h in selected['history']['histories'] if h['lifetimeKey'] not in previous]
        if not additions:return None
        keys={h['lifetimeKey'] for h in additions}
        updated['history']['histories'].extend(copy.deepcopy(additions))
        for name in ('episodeMembership','placementAdjudications'):
            updated['history'].setdefault(name,[]).extend(copy.deepcopy([
                r for r in selected['history'].get(name,[]) if r['lifetimeKey'] in keys]))
        provenance['addedHistoryKeys']=sorted(keys)
        return updated,R.H.shape_text(updated),provenance
    if field=='contactContinuationAdmission':
        selected_pas=set(selected['plateAppearances'])
        current={p['atBatIndex']:p for p in selected['contactCensus']['plays'] if p['atBatIndex'] in selected_pas}
        # A selected runner history can continue in a later PA. Its accepted
        # dependency mappings add contact links there too; project those exact
        # obligations, without requiring other runners from the later play.
        prior={p['atBatIndex']:p for p in source['plays']}
        full={p['atBatIndex']:p for p in selected['contactCensus']['plays']}
        dependencies={}
        for play in selected.get('context',{}).get('liveData',{}).get('plays',{}).get('allPlays',[]):
            for link in play.get(C.CONTEXT_KEY,{}).get('battedRunnerResolutions',[]):
                pa=link['atBatIndex']
                if pa not in selected_pas and pa in full:
                    dependencies.setdefault(pa,[]).append(link)
        for pa,links in dependencies.items():
            original=prior.get(pa,dict(links=[],memberships=[]))
            projected=copy.deepcopy(full[pa])
            for key,additions in (
                    ('links',links),
                    ('memberships',[m for m in selected['history'].get('episodeMembership',[]) if m['atBatIndex']==pa])):
                rows=copy.deepcopy(original.get(key,[]))
                for row in additions:
                    if row not in full[pa].get(key,[]):
                        raise ValueError('EG1 contact dependency differs from its source census')
                    if row not in rows:rows.append(copy.deepcopy(row))
                projected[key]=rows
            if any(any(row not in projected[key] for row in full[pa].get(key,[])) for key in ('links','memberships')):
                projected['status']='withheld'
            current[pa]=projected
        changed=[]
        for number,old in enumerate(source['plays']):
            new=current.get(old['atBatIndex'])
            if new is None or old==new:continue
            # An addition must retain all previous links and memberships.
            # Its current source census, not this projection, selects new ones.
            if any(any(r not in new.get(key,[]) for r in old.get(key,[])) for key in ('links','memberships')):
                raise ValueError('EG1 contact census would remove an existing source obligation')
            if old.get('playId')!=new.get('playId'):
                raise ValueError('EG1 contact census would change an existing contact identity')
            updated['plays'][number]=copy.deepcopy(new);changed.append(old['atBatIndex'])
        previous_pas={p['atBatIndex'] for p in source['plays']}
        for pa,new in current.items():
            if pa not in previous_pas:
                updated['plays'].append(copy.deepcopy(new));changed.append(pa)
        if not changed:return None
        provenance['updatedContactPlateAppearances']=sorted(changed)
        return updated,CONTACT.shape_text(updated),provenance
    return None


def revalidate(*args):
    return W.revalidate(*args,shape_text=shapes,decisions=dict(decision=DECISION,balkDecision=BALK_DECISION,
        automaticWalkDecision=WALK_DECISION,independentRunningDecision=INDEPENDENT_DECISION,
        reviewedWalkDecision=REVIEW_WALK_DECISION),
        project_census=project_census)


def acquire(state,game_pk,*,reopen=False):
    approved_case(game_pk)
    directory=state/'pipeline/quarantine/mlb-game'/game_pk/'targeted-eg1'
    source=directory/'input.json';manifest=directory/'acquisition.json'
    if manifest.is_file() and source.is_file():
        witness=W.read(manifest)
        if W.sha(source)!=witness['sha256']:raise ValueError('EG1 acquisition changed')
        return witness
    # Prefer any retained game response; its distinct provenance stays explicit.
    marker_root=state/'pipeline/evidence/nifi/game-promotion'/game_pk
    marker=W.read(max(marker_root.glob('*.json'),key=lambda p:W.read(p)['promotedAtUtc']))
    witness=E.retained_raw_witness(state,dict(gamePk=game_pk,rawSha256=marker['rawSha256']))
    if witness:return witness
    if manifest.is_file():
        if not reopen:raise ValueError('EG1 successful input was retired; do not reacquire it implicitly')
        # D2/W5 permit recovery only after their exact successful-case retry
        # predicate matches. Preserve the earlier source receipt unchanged.
        archive=manifest.with_name('acquisition-'+W.sha(manifest)+'.json')
        if not archive.exists():archive.write_bytes(manifest.read_bytes())
    url=f'https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live'
    with urllib.request.urlopen(urllib.request.Request(url,headers={'Accept':'application/json'}),timeout=60) as response:raw=response.read()
    if str(json.loads(raw).get('gamePk'))!=game_pk:raise ValueError('EG1 acquired game differs')
    directory.mkdir(parents=True,exist_ok=True)
    if source.exists():
        if source.read_bytes()!=raw:raise ValueError('EG1 interrupted acquisition has different bytes')
    else:
        temporary=source.with_suffix('.pending');temporary.write_bytes(raw);temporary.replace(source)
    witness=dict(kind='targeted-reacquisition',path=str(source),sha256=W.sha(source),gamePk=game_pk,
        url=url,decision=DECISION,acquiredAtUtc=W.TX.now())
    W.atomic(manifest,witness);return witness


def retire_input(state,result):
    """Only EG1-owned raw copies, and only after an exact successful promotion."""
    if not result.get('promotionEvidence'):return
    marker_path=Path(result['promotionEvidence']);marker=W.read(marker_path)
    addition=marker.get('targetedAddition',{});witness=addition.get('sourceWitness',{})
    if (addition.get('decision')!=DECISION or marker['gamePk']!=result['gamePk']
            or addition.get('sourceWitness')!=result.get('sourceWitness')):return
    owned=state/'pipeline/quarantine/mlb-game'/result['gamePk']/'targeted-eg1/input.json'
    candidates=[Path(addition['deltaPath']).parent/'game.json']
    if Path(witness['path']).resolve()==owned.resolve():candidates.append(owned)
    for source in candidates:
        if not source.exists():continue
        if W.sha(source)!=witness['sha256']:raise ValueError('EG1 raw copy changed before retirement')
        W.atomic(source.with_suffix('.retirement.json'),dict(sourceSha256=witness['sha256'],
            promotionEvidence=str(marker_path),promotionSha256=W.sha(marker_path),retiredAtUtc=W.TX.now()))
        source.unlink()


def fingerprint():
    return hashlib.sha256(Path(__file__).read_bytes()+Path(BK.__file__).read_bytes()+BK.SHAPE.read_bytes()
        +Path(D2.__file__).read_bytes()+D2.SHAPE.read_bytes()
        +R.fingerprint().encode()+INVENTORY.read_bytes()).hexdigest()


def automatic_walk_retry(state,case,previous):
    """Reopen only W4 matches in retained EG1 inputs, never every old success."""
    if previous.get('status') not in SUCCESS or previous.get('automaticWalkDecision')==WALK_DECISION:
        return False
    manifest=state/'pipeline/quarantine/mlb-game'/case['gamePk']/'targeted-eg1/acquisition.json'
    witness=(previous.get('sourceWitness') or previous.get('selected',{}).get('sourceWitness')
             or (W.read(manifest) if manifest.is_file() else {}))
    source=Path(witness.get('path',''))
    if not source.is_file():return False
    if W.sha(source)!=witness['sha256']:raise ValueError('W4 retained source changed')
    doc=W.read(source);players={p['player'].rsplit('/',1)[-1] for p in case['excludedPlayerGames']}
    candidates=[p for p in doc['liveData']['plays']['allPlays']
        if p.get('result',{}).get('eventType')=='walk'
        and str(p.get('matchup',{}).get('batter',{}).get('id')) in players
        and p.get('playEvents') and p['playEvents'][-1].get('isPitch') is False
        and p['playEvents'][-1].get('count',{}).get('balls')==4]
    if not candidates:return False
    doc[C.CONTEXT_KEY]={'runnerHistoryReconciliation':C.personal_runner_histories(source.read_bytes())}
    return any(C.runner_metric_evidence(p,str(p['atBatIndex']),str(doc['gameData']['game']['season']),
        document=doc)['awardAdvances'] for p in candidates)


def selection_repair_families(state,case,previous,players=None):
    """D2/W5: exact new selection plus a still-excluded approved player.

    A retained selection can diagnose D2 after raw retirement, but is never an
    ingestion input. The repair uses an independently checked original response.
    """
    if previous.get('status') not in SUCCESS:return []
    d2=previous.get('independentRunningDecision')!=INDEPENDENT_DECISION
    w5=previous.get('reviewedWalkDecision')!=REVIEW_WALK_DECISION
    if not (d2 or w5):return []
    manifest=state/'pipeline/quarantine/mlb-game'/case['gamePk']/'targeted-eg1/acquisition.json'
    witness=(previous.get('sourceWitness') or previous.get('selected',{}).get('sourceWitness')
             or (W.read(manifest) if manifest.is_file() else {}))
    source=Path(witness.get('path',''));raw=None
    if source.is_file():
        if W.sha(source)!=witness['sha256']:raise ValueError('D2/W5 retained source changed')
        raw=source.read_bytes();doc=json.loads(raw)
    else:
        doc=previous.get('selected',{}).get('context',{})
        if not doc and previous.get('deltaPath') and previous.get('executionContextSha256'):
            context=Path(previous['deltaPath']).parent/'game-context.json'
            owner=(state/'pipeline/evidence/mlb-game'/case['gamePk']).resolve()
            if not context.resolve().is_relative_to(owner):raise ValueError('D2/W5 context is outside its game owner')
            if context.is_file():
                if W.sha(context)!=previous['executionContextSha256']:raise ValueError('D2/W5 retained context changed')
                doc=W.read(context)
    plays=doc.get('liveData',{}).get('plays',{}).get('allPlays',[])
    if not any(p.get('result',{}).get('eventType') in {'walk','intent_walk'} or
               any(r.get('details',{}).get('eventType')=='defensive_indiff' for r in p.get('runners',[])) for p in plays):return []
    if players is None:players=outstanding(state,case)
    if not players:return []
    ids={p.rsplit('/',1)[-1] for p in players}
    families=set()
    for play in plays:
        batter=str(play.get('matchup',{}).get('batter',{}).get('id'))
        if d2:
            selected=C.defensive_indifference_evidence(play)
            if selected and (batter in ids or any(r['runnerId'] in ids for r in selected)):families.add('D2-defensive-indifference')
        if (w5 and batter in ids
                and play.get('result',{}).get('eventType') in {'walk','intent_walk'}
                and C.accounted_runner_count_reviews(play)['issues']):
            if C.accounted_runner_history_reviews(play)['issues']:continue
            if raw is not None:doc[C.CONTEXT_KEY]={'runnerHistoryReconciliation':C.personal_runner_histories(raw)}
            season=doc.get('gameData',{}).get('game',{}).get('season')
            if season is None:
                pointer=W.read(state/'serving/dashboard-current.json')
                with closing(sqlite3.connect(Path(pointer['databasePath']).as_uri()+'?mode=ro&immutable=1',uri=True)) as db:
                    dimension=db.execute('SELECT season FROM game_dimension WHERE game_pk=?',(case['gamePk'],)).fetchone()
                if not dimension:continue
                season=dimension[0]  # Diagnostic only; execution rereads the original source season.
            if C.runner_metric_evidence(play,str(play['atBatIndex']),str(season),
                    document=doc)['awardAdvances']:families.add('W5-reviewed-walk')
    return sorted(families)


def selection_repair_retry(state,case,previous):
    return bool(selection_repair_families(state,case,previous))


def repair_plan(state,publication,version,excluded=None):
    """Discover all matching approved repairs once per published remainder.

    Group by shared selector, retain the exact EG1 authorization boundary,
    and never turn a successful receipt into proof of metric completion.
    This is an execution work list, not another semantic admission gate.
    """
    groups={};held=[];resolved=[]
    inventory=W.read(INVENTORY)
    excluded=W.A.SCOPE.excluded_games(state) if excluded is None else excluded
    with closing(sqlite3.connect(Path(publication['databasePath']).as_uri()+'?mode=ro&immutable=1',uri=True)) as db:
        for number,case in enumerate(inventory['games']):
            game_pk=case['gamePk']
            if game_pk in excluded:continue
            path=state/'pipeline/control/mlb-game/empty-game-addition'/(game_pk+'.json')
            previous=W.read(path) if path.is_file() else {}
            players=outstanding(state,case,db)
            if players is None:
                held.append(dict(gamePk=game_pk,reason='waiting-for-reader'));continue
            if not players:
                resolved.append(game_pk);continue
            families=selection_repair_families(state,case,previous,players)
            current_case=dict(case,excludedPlayerGames=[p for p in case['excludedPlayerGames'] if p['player'] in players])
            if automatic_walk_retry(state,current_case,previous):families.append('W4-automatic-walk')
            if previous.get('status') in SUCCESS and not families:
                held.append(dict(gamePk=game_pk,players=players,reason='no-unapplied-approved-selection'));continue
            if previous.get('implementationSha256')==version and previous.get('attempts',0)>=2:
                held.append(dict(gamePk=game_pk,players=players,reason='retry-exhausted'))
                if number==0:return dict(publicationId=publication['buildId'],implementationSha256=version,
                    families=[],held=held,resolvedGames=resolved,firstRouteFailed=True)
                continue
            family='+'.join(sorted(families)) if families else 'EG1-existing-runner-patterns'
            groups.setdefault(family,[]).append(dict(gamePk=game_pk,players=players,firstRoute=number==0))
    families=[dict(family=name,players=len({p for item in games for p in item['players']}),
                   playerGames=sum(len(item['players']) for item in games),games=games)
              for name,games in groups.items()]
    families.sort(key=lambda g:(not any(item['firstRoute'] for item in g['games']),-g['players'],-g['playerGames'],g['family']))
    return dict(publicationId=publication['buildId'],implementationSha256=version,
                families=families,held=held,resolvedGames=resolved)


def next_game(state):
    version=fingerprint()
    pointer=state/'serving/dashboard-current.json'
    if not pointer.is_file():return None
    publication=W.read(pointer)
    if publication['buildId']<=W.read(INVENTORY)['publicationId']:return None
    path=state/'pipeline/control/mlb-game/empty-game-repair-plan.json'
    plan=W.read(path) if path.is_file() else {}
    excluded=W.A.SCOPE.excluded_games(state)
    scope_sha=hashlib.sha256(json.dumps(excluded,sort_keys=True).encode()).hexdigest()
    if (plan.get('publicationId'),plan.get('implementationSha256'),plan.get('activeScopeSha256'))!=(publication['buildId'],version,scope_sha):
        plan=repair_plan(state,publication,version,excluded);plan['activeScopeSha256']=scope_sha;W.atomic(path,plan)
    for group in plan['families']:
        for item in group['games']:
            game_pk=item['gamePk']
            if game_pk in excluded:continue
            receipt=state/'pipeline/control/mlb-game/empty-game-addition'/(game_pk+'.json')
            previous=W.read(receipt) if receipt.is_file() else {}
            if previous.get('implementationSha256')==version:
                if previous.get('status') in SUCCESS:continue
                if previous.get('attempts',0)>=2:
                    if item['firstRoute']:return None
                    continue
            return dict(gamePk=game_pk,family=group['family'],publicationId=plan['publicationId'])
    return None


def tick(state,game_pk,java,mapper,classpath):
    case=approved_case(game_pk)
    if not W.A.SCOPE.active(state,game_pk):return dict(gamePk=game_pk,status='outside-active-scope')
    path=state/'pipeline/control/mlb-game/empty-game-addition'/(game_pk+'.json')
    previous=W.read(path) if path.is_file() else {};version=fingerprint()
    reopening=selection_repair_retry(state,case,previous)
    if ((previous.get('status') in SUCCESS and not (reopening or automatic_walk_retry(state,case,previous)))
            or (previous.get('implementationSha256')==version and previous.get('attempts',0)>=2)):return previous
    result=dict(gamePk=game_pk,implementationSha256=version,checkedAtUtc=W.TX.now(),
        automaticWalkDecision=WALK_DECISION,independentRunningDecision=INDEPENDENT_DECISION,
        reviewedWalkDecision=REVIEW_WALK_DECISION,
        attempts=previous.get('attempts',0)+1 if previous.get('implementationSha256')==version else 1)
    try:
        players=outstanding(state,case)
        if players is None:return dict(gamePk=game_pk,status='waiting-for-reader')
        if not players:result.update(status='resolved-by-reader')
        else:
            witness=acquire(state,game_pk,reopen=reopening);selected=select(Path(witness['path']).read_bytes(),game_pk,players)
            if selected is None or selected.get('noSupportedAddition'):
                result.update(status='no-supported-addition',selected=selected,sourceWitness=witness)
            else:
                selected['sourceWitness']=witness
                result.update(W.add_game(state,game_pk,witness,java,mapper,classpath,repair=dict(
                    decisions=dict(decision=DECISION,balkDecision=BALK_DECISION,automaticWalkDecision=WALK_DECISION,
                        independentRunningDecision=INDEPENDENT_DECISION,reviewedWalkDecision=REVIEW_WALK_DECISION),select=lambda raw,pk:selected,
                    execution_inputs=execution_inputs,revalidate=revalidate,
                    validation_scope='eg1-selected-pa-runner-patterns-and-retained-admissions')))
                result['unresolved']=selected['unresolved']
    except Exception as error:result.update(status='failed',error=str(error))
    W.atomic(path,result)
    if result.get('status') in R.SUCCESS:retire_input(state,result)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-root',type=Path,required=True);parser.add_argument('--next',action='store_true')
    parser.add_argument('--game-pk')
    for name in ('java','mapper','jena-classpath'):parser.add_argument('--'+name,type=Path)
    args=parser.parse_args()
    if args.next:print(json.dumps(next_game(args.state_root)));raise SystemExit(0)
    if not all((args.game_pk,args.java,args.mapper,args.jena_classpath)):parser.error('Execution requires game, Java, mapper and Jena')
    result=tick(args.state_root,args.game_pk,args.java,args.mapper,args.jena_classpath)
    print(json.dumps(result));raise SystemExit(result['status']=='failed')
