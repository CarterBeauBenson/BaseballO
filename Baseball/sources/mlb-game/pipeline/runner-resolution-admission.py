"""NiFi's E1 complete runner-resolution census, separate from attribution.

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
spec = importlib.util.spec_from_file_location('resolution_admission_support', HERE/'batting-admission.py')
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)
SHAPE = HERE.parent/'shacl/runner-resolution-admission.ttl'
STEAL_TYPES={'stolen_base_2b','stolen_base_3b','stolen_base_home',
             'caught_stealing_2b','caught_stealing_3b','caught_stealing_home'}


def fingerprint():
    paths = [Path(__file__), SHAPE, HERE/'batting-admission.py',
             HERE/'reconcile-metric-source.py', ROOT/'scripts/pipeline/validate-shacl.py']
    return B.sha('\n'.join(p.relative_to(ROOT).as_posix()+':'+B.sha(p.read_bytes()) for p in paths).encode())


def nonmovement_strikeout_records(play):
    """Recognize an empty K record beside an explicit safe WP/PB movement.

    The complete positive companion and post-state establish the boundary;
    the null fields alone establish neither an out nor a safe advancement.
    Preserve the distinct source records without inventing a second running act.
    """
    if (play.get('result', {}).get('eventType') != 'strikeout'
            or play['result'].get('isOut') is not False or play.get('count', {}).get('strikes') != 3
            or play.get('about', {}).get('hasReview') is not False):
        return {}
    batter = play.get('matchup', {}).get('batter', {}).get('id')
    if not B.integer(batter) or batter == 0 or play['matchup'].get('postOnFirst', {}).get('id') != batter:
        return {}
    records = [(i,r) for i,r in enumerate(play.get('runners', [])) if r.get('details', {}).get('runner', {}).get('id') == batter]
    if len(records) != 2:
        return {}
    empty = [(i,r) for i,r in records if r.get('details', {}).get('eventType') == 'strikeout'
             and set(r.get('movement', {})) == {'originBase','start','end','outBase','isOut','outNumber'}
             and all(v is None for v in r['movement'].values())
             and r['details'].get('isScoringEvent') is False and not r.get('credits')]
    safe = [(i,r) for i,r in records if r.get('details', {}).get('eventType') in {'wild_pitch','passed_ball'}
            and r.get('movement') == dict(originBase=None,start=None,end='1B',outBase=None,isOut=False,outNumber=None)
            and r['details'].get('isScoringEvent') is False]
    if len(empty) != 1 or len(safe) != 1:
        return {}
    index = empty[0][1]['details'].get('playIndex')
    events = [e for e in play.get('playEvents', []) if e.get('index') == index]
    if (safe[0][1]['details'].get('playIndex') != index or len(events) != 1
            or events[0].get('isPitch') is not True or events[0].get('count', {}).get('strikes') != 3
            or events[0].get('details', {}).get('isInPlay') is not False):
        return {}
    return {empty[0][0]: safe[0][0]}


def census(raw, game_pk):
    game_pk = B.identity(int(game_pk))
    source = B.SOURCE.reconcile(raw, game_pk)
    doc = json.loads(raw)
    game = B.BASE+'data/game/'+game_pk
    issues = [dict(code='SOURCE_RECONCILIATION', detail=i) for i in source['issues']]
    resolutions, nonmovements = [], []
    for play in doc['liveData']['plays']['allPlays']:
        pa = str(play['atBatIndex'])
        empty_records = nonmovement_strikeout_records(play)
        for index, row in enumerate(play['runners']):
            if index in empty_records:
                nonmovements.append(dict(pa=game+'/plate-appearance/'+pa,runnerIndex=index,
                    companionRunnerIndex=empty_records[index],sourceRecordSha256=B.sha(json.dumps(row,sort_keys=True,separators=(',',':')).encode()),
                    absentAct=game+'/runner-act/movement/'+pa+'/'+str(index)))
                continue
            movement = row['movement']
            start, end, out = movement.get('start'), movement.get('end'), movement.get('isOut')
            if type(out) is not bool or start not in (None,'1B','2B','3B') or (not out and end not in ('1B','2B','3B','score')):
                issues.append(dict(code='UNRESOLVED_RUNNER_BOUNDARY',atBatIndex=pa,runnerIndex=index))
                continue
            # Exact existing RML subject selection; these are SHACL expectations,
            # not additional authoritative nodes or source-derived scores.
            kind = 'out' if out else 'score' if end=='score' else 'advance' if start else 'reach'
            suffix=pa+'/'+str(index)
            resolutions.append(dict(resolution=game+'/runner-resolution/'+kind+'/'+suffix,
                act=game+'/runner-act/movement/'+suffix,
                episode=game+'/runner-episode/'+suffix,pa=game+'/plate-appearance/'+pa,
                player=B.BASE+'data/player/'+B.identity(row['details']['runner']['id']),
                outcome='OutProcess' if out else 'RunProcess' if end=='score' else 'SafeProcess',
                stealAttempt=row['details'].get('eventType') in STEAL_TYPES,
                origin=start,
                destination=end if not out and end!='score' else None))
    return dict(gamePk=game_pk,game=game,sourceSha256=B.sha(raw),sourceRevision=source['sourceRevision'],
                status='withheld' if issues else 'reconciled',issues=issues,resolutions=resolutions,
                nonMovementRecords=nonmovements)


def shape_text(source):
    missing, identities = [], []
    for row in source.get('nonMovementRecords', []):
        pa=B.iri(row['pa']); process=B.iri(row['pa']+'/uncaught-third-strike')
        missing.append('''{ FILTER NOT EXISTS {
          %s a base:UncaughtThirdStrikeProcess ; obo:BFO_0000132 %s ; obo:BFO_0000117 ?judgment .
          ?judgment a base:UmpireJudgmentAct ; cco:ont00001986 ?decision .
          ?decision a base:BaseballDecisionICE ; cco:ont00001808 %s .
        } }''' % (process,pa,process))
        missing.append('{ %s a base:BaserunningAct . }' % B.iri(row['absentAct']))
    for row in source['resolutions']:
        fields={key:B.iri(row[key]) for key in ('resolution','act','episode','pa','player')}
        pattern="""%(resolution)s a base:RunnerResolutionProcess, base:%(outcome)s ;
          obo:BFO_0000132 %(pa)s ; obo:BFO_0000062 %(act)s .
        %(pa)s a base:PlateAppearance ; obo:BFO_0000132/obo:BFO_0000132/obo:BFO_0000132 $this .
        %(act)s a base:BaserunningAct ; obo:BFO_0000132 %(pa)s ; cco:ont00001833 %(player)s .
        %(episode)s a base:RunnerResolutionEpisode ; obo:BFO_0000132 %(pa)s ;
          obo:BFO_0000117 %(resolution)s, %(act)s .""" % dict(fields,outcome=row['outcome'])
        if row.get('stealAttempt'):
            pattern+='\n%s a base:StealAttemptAct .' % fields['act']
        else:
            pattern+='\nFILTER NOT EXISTS { %s a base:StealAttemptAct }' % fields['act']
        if row['destination']:
            pattern+='\n%s obo:BFO_0000117 ?judgment . ?judgment a base:SafeJudgmentAct ; cco:ont00001986 ?decision .\n?decision a base:SafeDecisionICE ; cco:ont00001808 %s, ?base . ?base a base:Base .\n?identifier a cco:ont00000649 ; cco:ont00001916 ?base ; cco:ont00001765 %s .' % (fields['resolution'],fields['resolution'],B.terms([row['destination']]))
        if row.get('origin'):
            pattern+='''
?origin a base:BaserunningSegmentOriginDesignation ; cco:ont00001808 %s ; cco:ont00001916 ?startBase .
?startBase a base:Base . ?startIdentifier a cco:ont00000649 ; cco:ont00001916 ?startBase ; cco:ont00001765 %s .''' % (fields['act'],B.terms([row['origin']]))
        missing.append('{ FILTER NOT EXISTS { '+pattern+' } }')
        identities.append('|'.join(row[k] for k in ('resolution','act','player','pa')))
    values=dict(GAME=source['game'],PREFIXES=B.PREFIXES,
        MISSING=' UNION '.join(missing) or 'FILTER(1 = 0)',
        RESOLUTIONS=', '.join(B.iri(r['resolution']) for r in source['resolutions']) or '<urn:baseballo:no-runner-resolutions>',
        IDENTITIES=B.terms(identities))
    text=SHAPE.read_text(encoding='utf-8')
    for key,value in values.items():text=text.replace('__'+key+'__',value)
    Graph().parse(data=text,format='turtle')
    return text


def prove(*, raw, game_pk, rdf_path, output, java=None, classpath=None):
    source = census(raw, game_pk)
    implementation, rdf_sha = fingerprint(), B.sha(rdf_path.read_bytes())
    proof = dict(artifactType='baseballo-runner-resolution-admission', contractVersion=1,
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
            validator = B.module(ROOT/'scripts/pipeline/validate-shacl.py', 'resolution_admission_shacl')
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
        raise ValueError('Runner-resolution admission inputs changed during validation')
    if proof['sourceReconciled'] and proof['graphConforms']:
        proof['status'] = 'admitted'
    B.SOURCE.write_atomic(output, proof)
    return proof


def promoted_admission(state_root, promotion):
    withheld = dict(status='withheld', issues=[dict(code='RUNNER_RESOLUTION_PROOF_MISSING_OR_STALE')])
    marker_path = Path(promotion['promotionManifest'])
    if B.sha(marker_path.read_bytes()) != promotion['promotionManifestSha256']:
        raise ValueError('Promotion marker changed while loading run admission')
    marker = json.loads(marker_path.read_text(encoding='utf-8-sig'))
    path = Path(marker.get('runnerResolutionAdmission', ''))
    if not path.is_file():
        return withheld
    if not path.resolve().is_relative_to((state_root/'pipeline/evidence/mlb-game'/promotion['gamePk']).resolve()):
        raise ValueError('Runner-resolution proof escaped its owning game evidence directory')
    if B.sha(path.read_bytes()) != marker.get('runnerResolutionAdmissionSha256'):
        raise ValueError('Runner-resolution proof hash differs from promotion')
    proof = json.loads(path.read_text(encoding='utf-8'))
    if (proof.get('artifactType') != 'baseballo-runner-resolution-admission' or proof.get('contractVersion') != 1
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
            raise ValueError('Runner-resolution proof validation artifact changed: '+key)
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
        raise ValueError('Runner-resolution proof cannot overwrite source or RDF')
    raw = args.input.read_bytes()
    result = prove(raw=raw, game_pk=args.game_pk, rdf_path=args.rdf, output=args.output,
                   java=args.java, classpath=args.jena_classpath)
    if raw != args.input.read_bytes():
        raise ValueError('Runner-resolution proof source changed during validation')
    print(json.dumps(result))
