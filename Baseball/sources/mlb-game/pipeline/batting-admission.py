"""B1 source reconciliation and owning SHACL qualification proof for NiFi.

Raw expectations are proof inputs only. Serving counts must be queried from
the independently promoted graph. This component never mints domain RDF.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import re

from rdflib import Graph, Literal, URIRef

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
SHAPE = HERE.parent / 'shacl/batting-admission.ttl'
BASE = 'https://baseballontology.org/'
PREFIXES = '''PREFIX base: <https://baseballontology.org/>
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX cco: <https://www.commoncoreontologies.org/>
'''
RESULTS = {
    'single': 'SingleProcess', 'double': 'DoubleProcess', 'triple': 'TripleProcess',
    'home_run': 'HomeRunProcess', 'field_out': 'BattedBallOutProcess',
    'force_out': 'ForceOutProcess', 'grounded_into_double_play': 'GroundedIntoDoublePlayProcess',
    'double_play': 'DoublePlayProcess', 'sac_fly': 'SacrificeFlyProcess',
    'sac_bunt': 'SacrificeBuntProcess', 'strikeout': 'StrikeoutProcess',
    'strikeout_double_play': 'StrikeoutProcess', 'walk': 'WalkProcess',
    'intent_walk': 'WalkProcess', 'hit_by_pitch': 'HitByPitchProcess',
    'fielders_choice': 'FieldersChoiceProcess', 'fielders_choice_out': 'FieldersChoiceProcess',
    'field_error': 'ErrorProcess', 'catcher_interf': 'InterferenceProcess',
}
INTERRUPTIONS = {'caught_stealing_2b', 'caught_stealing_3b', 'caught_stealing_home',
                 'pickoff_1b', 'pickoff_2b', 'pickoff_3b', 'pickoff_caught_stealing_2b',
                 'pickoff_caught_stealing_3b', 'pickoff_caught_stealing_home'}


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


SOURCE = module(HERE / 'reconcile-metric-source.py', 'b1_source_census')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def fingerprint():
    paths = [Path(__file__), SHAPE, HERE / 'reconcile-metric-source.py',
             ROOT / 'scripts/pipeline/validate-shacl.py']
    return sha('\n'.join(p.relative_to(ROOT).as_posix()+':'+sha(p.read_bytes())
                         for p in paths).encode())


def integer(value):
    return type(value) is int and value >= 0


def identity(value):
    if not integer(value) or value == 0:
        raise ValueError('Missing or invalid source identity')
    return str(value)


def census(raw, game_pk):
    if not re.fullmatch(r'[0-9]+', game_pk):
        raise ValueError('Invalid game identity')
    doc = json.loads(raw)
    source = SOURCE.reconcile(raw, game_pk)
    issues = [dict(code='SOURCE_RECONCILIATION', detail=i) for i in source['issues']]
    game = BASE+'data/game/'+game_pk
    roster, members, interrupted = [], [], []
    counts = Counter()
    team_totals = {}
    for side in ('away', 'home'):
        team = doc.get('liveData', {}).get('boxscore', {}).get('teams', {}).get(side, {})
        team_id = identity(team.get('team', {}).get('id'))
        total = team.get('teamStats', {}).get('batting', {}).get('plateAppearances')
        if not integer(total):
            issues.append(dict(code='MISSING_TEAM_PA_TOTAL', side=side))
        people = team.get('players')
        if not isinstance(people, dict) or not people:
            raise ValueError('Missing final boxscore roster')
        known, missing = 0, []
        for key, person in people.items():
            player_id = identity(person.get('person', {}).get('id'))
            if key != 'ID'+player_id:
                issues.append(dict(code='ROSTER_IDENTITY_MISMATCH', player=player_id))
            stats = person.get('stats', {}).get('batting')
            official = stats.get('plateAppearances') if isinstance(stats, dict) else None
            row = dict(player=BASE+'data/player/'+player_id, team=BASE+'data/team/'+team_id,
                       side=side, officialPA=official)
            roster.append(row)
            if integer(official):
                known += official
            elif stats == {}:
                missing.append(row)
            else:
                issues.append(dict(code='MISSING_PLAYER_PA_TOTAL', player=player_id))
        # Nonnegative PA totals: a zero residual independently proves zero for
        # ALL empty blocks together. Empty JSON alone does not imply zero.
        if integer(total) and known == total:
            for row in missing:
                row.update(officialPA=0, zeroBasis='reconciled-team-total-zero-residual')
        else:
            issues.append(dict(code='UNRECONCILED_TEAM_PA_TOTAL', side=side, reported=total, known=known))
        team_totals[side] = total
    owners = {r['player']: r for r in roster}
    if len(owners) != len(roster):
        issues.append(dict(code='AMBIGUOUS_PLAYER_TEAM'))
    for play in doc['liveData']['plays']['allPlays']:
        index = play['atBatIndex']
        player = BASE+'data/player/'+identity(play.get('matchup', {}).get('batter', {}).get('id'))
        pa = game+'/plate-appearance/'+str(index)
        event_type = play.get('result', {}).get('eventType')
        result_type = RESULTS.get(event_type)
        if player not in owners or owners[player]['side'] != ('away' if play['about']['halfInning']=='top' else 'home'):
            issues.append(dict(code='BATTER_ROSTER_MISMATCH', atBatIndex=index))
        events = play.get('playEvents', [])
        # A PH event at the untouched 0-0 boundary can be reconciled. An
        # explicit PR change between two other rostered people leaves this
        # batter unchanged. Counts and the exact single-Batter-Act graph census
        # still reconcile independently; no multi-batter credit is guessed.
        for position, event in enumerate(events):
            if event.get('details', {}).get('eventType') != 'offensive_substitution':
                continue
            prior = events[:position]
            new_id=event.get('player',{}).get('id')
            old_id=event.get('replacedPlayer',{}).get('id')
            runner_only=(event.get('position',{}).get('abbreviation')=='PR'
                and event.get('isPitch') is False and event.get('isSubstitution') is True
                and type(event.get('base')) is int and event['base'] in (1,2,3)
                and integer(new_id) and integer(old_id) and min(new_id,old_id)>0
                and len({new_id,old_id,play['matchup']['batter']['id']})==3
                and player in owners
                and all(owners.get(BASE+'data/player/'+str(v),{}).get('side')==owners[player]['side']
                        for v in (new_id,old_id)))
            # A pitching change or mound visit can precede a PH in the feed
            # without a pitch or count award having begun batting. Array
            # position is not evidence of prior batting participation.
            neutral_prefix = all(
                e.get('index') == i and e.get('type') == 'action' and e.get('isPitch') is False
                and e.get('details', {}).get('eventType') in {'pitching_substitution', 'mound_visit'}
                and e.get('details', {}).get('isInPlay') is not True
                and e.get('details', {}).get('isBall') is not True
                and e.get('details', {}).get('isStrike') is not True
                and e.get('details', {}).get('isScoringPlay') is False
                and e.get('details', {}).get('isOut') is False
                and e.get('count', {}).get('balls') == 0
                and e.get('count', {}).get('strikes') == 0
                and e.get('count', {}).get('outs') == event.get('count', {}).get('outs')
                and not any(r.get('details', {}).get('playIndex') == e.get('index') for r in play.get('runners', []))
                for i, e in enumerate(prior))
            pristine = (event.get('index') == position and neutral_prefix
                        and event.get('isPitch') is False and event.get('isSubstitution') is True
                        and event.get('position', {}).get('abbreviation') == 'PH'
                        and event.get('player', {}).get('id') == play['matchup']['batter']['id']
                        and integer(event.get('replacedPlayer', {}).get('id'))
                        and event.get('count', {}).get('balls') == 0
                        and event.get('count', {}).get('strikes') == 0
                        and old_id > 0 and old_id != new_id
                        and owners.get(BASE+'data/player/'+str(old_id), {}).get('side') == owners.get(player, {}).get('side'))
            if not (pristine or runner_only):
                issues.append(dict(code='OFFENSIVE_REPLACEMENT_WITHIN_TURN', atBatIndex=index,
                                   eventIndex=event.get('index')))
        row = dict(pa=pa, player=player, resultType=BASE+result_type if result_type else None,
                   atBatIndex=index, eventType=event_type)
        if result_type:
            counts[player] += 1
        else:
            runners = play.get('runners', [])
            interruption = (event_type in INTERRUPTIONS and play.get('count', {}).get('outs') == 3
                            and play.get('count', {}).get('strikes', 3) < 3
                            and play.get('count', {}).get('balls', 4) < 4
                            and runners and all(r.get('details', {}).get('runner', {}).get('id')
                                != play['matchup']['batter']['id'] for r in runners)
                            and any(r.get('movement', {}).get('isOut') is True
                                and r.get('movement', {}).get('outNumber') == 3 for r in runners)
                            and not any(e.get('details', {}).get('isInPlay') is True for e in events))
            if interruption:
                interrupted.append(pa)
            else:
                issues.append(dict(code='UNRESOLVED_COMPLETED_RESULT', atBatIndex=index, eventType=event_type))
        members.append(row)
    for row in roster:
        if row['officialPA'] != counts[row['player']]:
            issues.append(dict(code='PLAYER_PA_MISMATCH', player=row['player'],
                               reported=row['officialPA'], observed=counts[row['player']]))
    return dict(gamePk=game_pk, game=game, sourceSha256=sha(raw), sourceRevision=source['sourceRevision'],
                sourceConsistency=source['status'], status='reconciled' if not issues else 'withheld',
                issues=issues, members=members, roster=roster, interrupted=interrupted,
                teamTotals=team_totals, implementationSha256=fingerprint())


def iri(value):
    return URIRef(value).n3()


def terms(values):
    return ', '.join(Literal(v).n3() for v in sorted(set(values))) or '""'


def shape_text(source):
    """Bind expected source identities/counts into the owning SHACL profile."""
    game = source['game']
    missing, batters, results, roster, missing_roster, counts = [], [], [], [], [], []
    result_types = ', '.join(iri(BASE+t) for t in sorted(set(RESULTS.values())))
    for row in source['members']:
        pa, player = row['pa'], row['player']
        act, role = pa+'/batter-act', player+'/role/batter'
        pattern = f'''{iri(pa)} a base:PlateAppearance ; obo:BFO_0000132/obo:BFO_0000132/obo:BFO_0000132 $this .
{iri(act)} a base:BatterAct ; obo:BFO_0000132 {iri(pa)} ; obo:BFO_0000055 {iri(role)} .
{iri(role)} a base:BatterRole ; obo:BFO_0000197 {iri(player)} .'''
        batters.append('|'.join((pa, act, role, player)))
        if row['resultType']:
            result, judgment, decision, record = (pa+s for s in ('/result','/judgment/result','/decision/result','/event-record/result'))
            pattern += f'''\n{iri(result)} a base:BaseballInstitutionalProcess, {iri(row['resultType'])} ; obo:BFO_0000132 {iri(pa)} .
{iri(judgment)} a base:BaseballAdjudicationAct ; obo:BFO_0000132 {iri(result)} ; cco:ont00001986 {iri(decision)} .
{iri(decision)} a base:BaseballDecisionICE ; cco:ont00001808 {iri(result)} .
{iri(record)} a base:BaseballEventRecord ; cco:ont00001808 {iri(result)}, {iri(judgment)}, {iri(decision)} .'''
            results.append('|'.join((pa, result, row['resultType'])))
        missing.append('{ FILTER NOT EXISTS { '+pattern+' } }')
    for row in source['roster']:
        player, team = row['player'], row['team']
        role = player+'/team/'+team.rsplit('/',1)[-1]+'/role/player'
        roster.append('|'.join((role,player,team)))
        missing_roster.append('''{ FILTER NOT EXISTS { $this obo:BFO_0000055 %s .
%s a base:PlayerRole ; obo:BFO_0000197 %s ; cco:ont00001992 %s .
?teamRole a base:%sTeamRole ; obo:BFO_0000197 %s ; obo:BFO_0000054 $this . } }''' %
            (iri(role), iri(role), iri(player), iri(team), row['side'].title(), iri(team)))
        query = PREFIXES+'''SELECT $this WHERE {
{ SELECT $this (COUNT(DISTINCT ?pa) AS ?actual) WHERE {
$this a base:BaseballGame .
OPTIONAL {
?pa a base:PlateAppearance ; obo:BFO_0000132/obo:BFO_0000132/obo:BFO_0000132 $this .
?act a base:BatterAct ; obo:BFO_0000132 ?pa ; obo:BFO_0000055 ?role .
?role a base:BatterRole ; obo:BFO_0000197 %s .
?result a base:BaseballInstitutionalProcess, ?type ; obo:BFO_0000132 ?pa .
FILTER(?type IN (%s))
?judgment a base:BaseballAdjudicationAct ; obo:BFO_0000132 ?result ; cco:ont00001986 ?decision .
?decision a base:BaseballDecisionICE ; cco:ont00001808 ?result .
?record a base:BaseballEventRecord ; cco:ont00001808 ?result, ?judgment, ?decision .
} } GROUP BY $this } FILTER(?actual != %d) }''' % (iri(player), result_types, row['officialPA'])
        counts.append('[] a sh:NodeShape ; sh:targetNode '+iri(game)+' ; sh:sparql [ sh:message '+
                      Literal('B1 player PA count differs: '+player).n3()+' ; sh:select '+Literal(query).n3()+' ] .')
    substitutions = dict(GAME=game, PREFIXES=PREFIXES, MISSING_PA=' UNION '.join(missing),
        PAS=', '.join(iri(r['pa']) for r in source['members']), BATTERS=terms(batters),
        RESULT_TYPES=result_types, RESULTS=terms(results), MISSING_ROSTER=' UNION '.join(missing_roster),
        ROSTER=terms(roster), PLAYER_COUNT_SHAPES='\n'.join(counts))
    text = SHAPE.read_text(encoding='utf-8')
    text = text.replace('# __PLAYER_COUNT_SHAPES__', substitutions.pop('PLAYER_COUNT_SHAPES'))
    for key,value in substitutions.items():
        text = text.replace('__'+key+'__',value)
    Graph().parse(data=text,format='turtle')  # Serialization only, not graph conformance.
    return text


def prove(*, raw, game_pk, rdf_path, output, java=None, classpath=None):
    source = census(raw, game_pk)
    initial_rdf_sha = sha(rdf_path.read_bytes())
    proof = dict(artifactType='baseballo-batting-admission', contractVersion=1,
                 gamePk=game_pk, graph='https://w3id.org/baseball/graph/game/'+game_pk,
                 sourceSha256=source['sourceSha256'], sourceRevision=source['sourceRevision'],
                 authoritativeRdfSha256=initial_rdf_sha, implementationSha256=fingerprint(),
                 status='withheld', sourceReconciled=source['status']=='reconciled',
                 graphConforms=False, issues=source['issues'], selectedPopulationComplete=False)
    output.parent.mkdir(parents=True,exist_ok=True)
    source_path=output.with_suffix('.source.json')
    SOURCE.write_atomic(source_path, source)
    proof['sourceCensusSha256']=sha(source_path.read_bytes())
    if source['status']=='reconciled':
        shapes=output.with_suffix('.shapes.ttl')
        shapes.write_text(shape_text(source),encoding='utf-8',newline='\n')
        if java:
            validator=module(ROOT/'scripts/pipeline/validate-shacl.py','b1_shacl')
            conforms, report, _=validator.validate_with_jena(data_path=rdf_path.resolve(),
                shape_path=shapes.resolve(), java=java, classpath=classpath, max_heap='384m')
        else:
            from pyshacl import validate
            conforms, report, _=validate(Graph().parse(rdf_path), shacl_graph=Graph().parse(shapes),
                                         inference='none', advanced=True)
        report_path=output.with_suffix('.report.ttl')
        report.serialize(destination=report_path,format='turtle')
        proof.update(graphConforms=bool(conforms), shapeSha256=sha(shapes.read_bytes()),
                     reportSha256=sha(report_path.read_bytes()), engine='jena' if java else 'pyshacl')
        if not conforms:
            proof['issues'].append(dict(code='SOURCE_GRAPH_CONFORMANCE'))
    if sha(rdf_path.read_bytes()) != initial_rdf_sha or fingerprint()!=source['implementationSha256']:
        raise ValueError('Source admission inputs changed during validation')
    if proof['sourceReconciled'] and proof['graphConforms']:
        proof['status']='admitted'
    SOURCE.write_atomic(output, proof)
    return proof


def promoted_admission(state_root, promotion):
    """Read hash-bound proof provenance, never raw expectations as metric facts."""
    withheld = dict(status='withheld', issues=[dict(code='B1_PROOF_MISSING_OR_STALE')])
    marker_path = Path(promotion['promotionManifest'])
    if sha(marker_path.read_bytes()) != promotion['promotionManifestSha256']:
        raise ValueError('Promotion marker changed while loading B1 provenance')
    marker = json.loads(marker_path.read_text(encoding='utf-8-sig'))
    path = Path(marker.get('battingAdmission', ''))
    if not path.is_file():
        return withheld
    expected_root = (state_root/'pipeline/evidence/mlb-game'/promotion['gamePk']).resolve()
    if not path.resolve().is_relative_to(expected_root):
        raise ValueError('B1 proof is outside its owning game evidence directory')
    if sha(path.read_bytes()) != marker.get('battingAdmissionSha256'):
        raise ValueError('B1 proof hash differs from promotion')
    proof = json.loads(path.read_text(encoding='utf-8'))
    if (proof.get('artifactType') != 'baseballo-batting-admission'
            or proof.get('contractVersion') != 1
            or proof.get('implementationSha256') != fingerprint()
            or proof.get('sourceSha256') != promotion['rawSha256']
            or proof.get('authoritativeRdfSha256') != promotion['authoritativeRdfSha256']
            or proof.get('graph') != promotion['authoritativeGraph']):
        return withheld
    for suffix, field in (('.source.json','sourceCensusSha256'),
                          ('.shapes.ttl','shapeSha256'),('.report.ttl','reportSha256')):
        if field in proof and sha(path.with_suffix(suffix).read_bytes()) != proof[field]:
            raise ValueError('B1 retained validation artifact changed: '+field)
    # Import only the proof, not the source-census player totals or membership.
    return {**proof, 'proofSha256': sha(path.read_bytes())}


def schedule_coverage(state_root):
    """Latest retained full-response schedule provenance for each date.

    An older complete snapshot cannot mask a newer incomplete snapshot.
    Retained coverage is an upstream completeness check, never a score input.
    """
    days = {}
    root=state_root/'pipeline/control/mlb-game/batches'
    batches=[]
    for path in root.glob('*.json'):
        value=json.loads(path.read_text(encoding='utf-8-sig'))
        if value.get('artifactType')=='baseballo-mlb-game-schedule-batch':
            batches.append((value.get('createdAtUtc',''),path,value))
    for _,path,batch in sorted(batches):
        coverage=batch.get('qualificationCoverage',{})
        if coverage.get('contractVersion') != 1:
            continue
        for day,games in coverage['days'].items():
            days[day]=dict(completeResponse=coverage['completeResponse'] is True,
                games=games, scheduleSha256=batch['scheduleSha256'], batchId=batch['batchId'],
                observedAt=batch['createdAtUtc'], provenanceSha256=sha(path.read_bytes()))
    return days


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--rdf',type=Path,required=True)
    parser.add_argument('--game-pk',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--java',type=Path)
    parser.add_argument('--jena-classpath',type=Path)
    args=parser.parse_args()
    outputs={args.output.resolve(), *(args.output.with_suffix(s).resolve()
               for s in ('.source.json','.shapes.ttl','.report.ttl'))}
    if outputs & {args.input.resolve(),args.rdf.resolve()}:
        raise ValueError('Proof cannot overwrite its source or RDF')
    raw=args.input.read_bytes()
    result=prove(raw=raw,game_pk=args.game_pk,rdf_path=args.rdf,output=args.output,
                 java=args.java,classpath=args.jena_classpath)
    if args.input.read_bytes()!=raw:
        raise ValueError('Source changed during admission')
    print(json.dumps(result))
    # Withheld batting admission must not disable an unrelated accepted graph.
    # Its report prevents qualification; execution errors fail the NiFi stage.


if __name__=='__main__':
    main()
