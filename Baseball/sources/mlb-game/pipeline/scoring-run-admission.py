"""NiFi's E1 counted-run census and roster proof, separate from C1 coverage.

Source numbers and identities bind SHACL only. Serving receives validation
provenance and calculates from promoted RDF, never from this source census.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

from rdflib import Graph

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('run_admission_support', HERE/'batting-admission.py')
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)
SHAPE = HERE.parent/'shacl/scoring-run-admission.ttl'


def fingerprint():
    paths = [Path(__file__), SHAPE, HERE/'batting-admission.py',
             HERE/'reconcile-metric-source.py', ROOT/'scripts/pipeline/validate-shacl.py']
    return B.sha('\n'.join(p.relative_to(ROOT).as_posix()+':'+B.sha(p.read_bytes()) for p in paths).encode())


def census(raw, game_pk):
    game_pk = B.identity(int(game_pk))
    source = B.SOURCE.reconcile(raw, game_pk)
    doc = json.loads(raw)
    game = B.BASE+'data/game/'+game_pk
    issues = [dict(code='SOURCE_RECONCILIATION', detail=i) for i in source['blockingIssues']]
    roster, runs = [], []
    for side in ('away', 'home'):
        team = doc['liveData']['boxscore']['teams'][side]
        team_id = B.identity(team['team']['id'])
        if not isinstance(team.get('players'), dict) or not team['players']:
            issues.append(dict(code='MISSING_TEAM_ROSTER', side=side))
            continue
        for key, person in team['players'].items():
            player_id = B.identity(person['person']['id'])
            if key != 'ID'+player_id:
                issues.append(dict(code='ROSTER_IDENTITY_MISMATCH', player=player_id))
            roster.append(dict(player=B.BASE+'data/player/'+player_id,
                               team=B.BASE+'data/team/'+team_id, side=side))
    owners = {r['player']: r for r in roster}
    if not roster or len(owners) != len(roster):
        issues.append(dict(code='AMBIGUOUS_GAME_ROSTER'))
    for play in doc['liveData']['plays']['allPlays']:
        pa = str(play['atBatIndex'])
        for index, row in enumerate(play['runners']):
            if row['details'].get('isScoringEvent') is not True:
                continue
            player = B.BASE+'data/player/'+B.identity(row['details']['runner']['id'])
            if (row['movement'].get('end') != 'score' or row['movement'].get('isOut') is not False
                    or player not in owners or owners[player]['side'] !=
                    ('away' if play['about']['halfInning']=='top' else 'home')):
                issues.append(dict(code='INCONSISTENT_COUNTED_RUN', atBatIndex=pa, runnerIndex=index))
            runs.append(dict(run=game+'/runner-resolution/score/'+pa+'/'+str(index),
                             act=game+'/runner-act/movement/'+pa+'/'+str(index), player=player))
    return dict(gamePk=game_pk, game=game, sourceSha256=B.sha(raw), sourceRevision=source['sourceRevision'],
                status='withheld' if issues else 'reconciled', issues=issues, roster=roster, runs=runs)


def shape_text(source):
    missing, missing_roster, roster = [], [], []
    for row in source['runs']:
        missing.append('''{ FILTER NOT EXISTS {
%s a base:RunProcess ; obo:BFO_0000132+ $this ; obo:BFO_0000062 %s .
%s a base:BaserunningAct ; cco:ont00001833 %s . } }''' %
            tuple(B.iri(row[k]) for k in ('run','act','act','player')))
    for row in source['roster']:
        player, team = row['player'], row['team']
        role = player+'/team/'+team.rsplit('/',1)[-1]+'/role/player'
        roster.append('|'.join((role,player,team)))
        missing_roster.append('''{ FILTER NOT EXISTS {
$this obo:BFO_0000055 %s . %s a base:PlayerRole ; obo:BFO_0000197 %s ; cco:ont00001992 %s .
?teamRole a base:%sTeamRole ; obo:BFO_0000197 %s ; obo:BFO_0000054 $this . } }''' %
            (B.iri(role), B.iri(role), B.iri(player), B.iri(team), row['side'].title(), B.iri(team)))
    replacements = dict(GAME=source['game'], PREFIXES=B.PREFIXES,
        MISSING_RUNS=' UNION '.join(missing) or 'FILTER(1 = 0)',
        RUNS=', '.join(B.iri(r['run']) for r in source['runs']) or '<urn:baseballo:no-counted-runs>',
        SCORERS=B.terms('|'.join(r[k] for k in ('run','act','player')) for r in source['runs']),
        MISSING_ROSTER=' UNION '.join(missing_roster) or 'FILTER(true)', ROSTER=B.terms(roster))
    text = SHAPE.read_text(encoding='utf-8')
    for key, value in replacements.items():
        text = text.replace('__'+key+'__', value)
    Graph().parse(data=text, format='turtle')
    return text


def prove(*, raw, game_pk, rdf_path, output, java=None, classpath=None):
    source = census(raw, game_pk)
    implementation, rdf_sha = fingerprint(), B.sha(rdf_path.read_bytes())
    proof = dict(artifactType='baseballo-scoring-run-admission', contractVersion=1,
        gamePk=source['gamePk'], graph='https://w3id.org/baseball/graph/game/'+source['gamePk'],
        sourceSha256=source['sourceSha256'], sourceRevision=source['sourceRevision'],
        authoritativeRdfSha256=rdf_sha, implementationSha256=implementation,
        status='withheld', sourceReconciled=source['status']=='reconciled', graphConforms=False,
        issues=source['issues'])
    output.parent.mkdir(parents=True, exist_ok=True)
    source_path = output.with_suffix('.source.json')
    B.SOURCE.write_atomic(source_path, source)
    proof['sourceCensusSha256'] = B.sha(source_path.read_bytes())
    if proof['sourceReconciled']:
        shapes = output.with_suffix('.shapes.ttl')
        shapes.write_text(shape_text(source), encoding='utf-8', newline='\n')
        if java:
            validator = B.module(ROOT/'scripts/pipeline/validate-shacl.py', 'run_admission_shacl')
            conforms, report, _ = validator.validate_with_jena(data_path=rdf_path.resolve(),
                shape_path=shapes.resolve(), java=java, classpath=classpath, max_heap='384m')
        else:
            from pyshacl import validate
            conforms, report, _ = validate(Graph().parse(rdf_path), shacl_graph=Graph().parse(shapes),
                                           inference='none', advanced=True)
        report_path = output.with_suffix('.report.ttl')
        report.serialize(destination=report_path, format='turtle')
        proof.update(graphConforms=bool(conforms), shapeSha256=B.sha(shapes.read_bytes()),
                     reportSha256=B.sha(report_path.read_bytes()), engine='jena' if java else 'pyshacl')
        if not conforms:
            proof['issues'].append(dict(code='SOURCE_GRAPH_CONFORMANCE'))
    if rdf_sha != B.sha(rdf_path.read_bytes()) or implementation != fingerprint():
        raise ValueError('Run admission inputs changed during validation')
    if proof['sourceReconciled'] and proof['graphConforms']:
        proof['status'] = 'admitted'
    B.SOURCE.write_atomic(output, proof)
    return proof


def promoted_admission(state_root, promotion):
    withheld = dict(status='withheld', issues=[dict(code='RUN_PROOF_MISSING_OR_STALE')])
    marker_path = Path(promotion['promotionManifest'])
    if B.sha(marker_path.read_bytes()) != promotion['promotionManifestSha256']:
        raise ValueError('Promotion marker changed while loading run admission')
    marker = json.loads(marker_path.read_text(encoding='utf-8-sig'))
    path = Path(marker.get('scoringRunAdmission', ''))
    if not path.is_file():
        return withheld
    if not path.resolve().is_relative_to((state_root/'pipeline/evidence/mlb-game'/promotion['gamePk']).resolve()):
        raise ValueError('Run proof escaped its owning game evidence directory')
    if B.sha(path.read_bytes()) != marker.get('scoringRunAdmissionSha256'):
        raise ValueError('Run proof hash differs from promotion')
    proof = json.loads(path.read_text(encoding='utf-8'))
    if (proof.get('artifactType') != 'baseballo-scoring-run-admission' or proof.get('contractVersion') != 1
            or proof.get('gamePk') != promotion['gamePk'] or proof.get('implementationSha256') != fingerprint()
            or proof.get('sourceSha256') != promotion['rawSha256']
            or proof.get('authoritativeRdfSha256') != promotion['authoritativeRdfSha256']
            or proof.get('graph') != promotion['authoritativeGraph']):
        return withheld
    if proof.get('status') == 'admitted' and any(not proof.get(key) for key in
            ('sourceCensusSha256','shapeSha256','reportSha256')):
        raise ValueError('Admitted run proof lacks retained validation artifact hashes')
    for suffix, key in (('.source.json','sourceCensusSha256'), ('.shapes.ttl','shapeSha256'), ('.report.ttl','reportSha256')):
        if key in proof and B.sha(path.with_suffix(suffix).read_bytes()) != proof[key]:
            raise ValueError('Run proof validation artifact changed: '+key)
    return {**proof, 'proofSha256':B.sha(path.read_bytes())}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('input','rdf','output'):
        parser.add_argument('--'+key, type=Path, required=True)
    parser.add_argument('--game-pk', required=True)
    parser.add_argument('--java', type=Path)
    parser.add_argument('--jena-classpath', type=Path)
    args = parser.parse_args()
    if args.java and not args.jena_classpath:
        parser.error('--java requires --jena-classpath')
    outputs = {args.output.resolve(), *(args.output.with_suffix(s).resolve()
               for s in ('.source.json','.shapes.ttl','.report.ttl'))}
    if outputs & {args.input.resolve(), args.rdf.resolve()}:
        raise ValueError('Run proof cannot overwrite source or RDF')
    raw = args.input.read_bytes()
    result = prove(raw=raw, game_pk=args.game_pk, rdf_path=args.rdf, output=args.output,
                   java=args.java, classpath=args.jena_classpath)
    if raw != args.input.read_bytes():
        raise ValueError('Run proof source changed during validation')
    print(json.dumps(result))
