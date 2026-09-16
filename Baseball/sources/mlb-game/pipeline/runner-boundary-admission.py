"""NiFi's C1/C2 boundary coverage proof over the accepted graph contract.

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
SHAPE = HERE.parent/'shacl/runner-boundary-admission.ttl'
CONTEXT_PATH = ROOT/'scripts/pipeline/prepare-rml-context.py'
CONTEXT = B.module(CONTEXT_PATH, 'boundary_source_context')


def fingerprint():
    paths = [Path(__file__), SHAPE, CONTEXT_PATH, HERE/'batting-admission.py',
             HERE/'reconcile-metric-source.py', ROOT/'scripts/pipeline/validate-shacl.py']
    return B.sha('\n'.join(p.relative_to(ROOT).as_posix()+':'+B.sha(p.read_bytes()) for p in paths).encode())


def census(raw, game_pk):
    """Expected existing stases/out counts and C1 membership, never scores.

    The accepted source reconciler accounts for every event, replacement,
    review, movement and half ending before its history can certify coverage.
    These source-derived expectations are used ONLY as SHACL parameters.
    """
    game_pk = B.identity(int(game_pk))
    doc = json.loads(raw)
    if str(doc['gamePk']) != game_pk:
        raise ValueError('Boundary source game identity mismatch')
    history = CONTEXT.personal_runner_histories(raw)
    game = B.BASE+'data/game/'+game_pk
    issues = [dict(code='SOURCE_RECONCILIATION', detail=i) for i in history.get('sourceIssues', [])]
    issues += [dict(code='INCOMPLETE_PERSONAL_HISTORIES', detail=h) for h in history['halves'] if h['status']!='reconciled']
    if history['sourceConsistency']!='consistent' and not issues:
        issues.append(dict(code='SOURCE_RECONCILIATION'))
    boundaries, active, half, outs, awards = [], {}, None, 0, []
    for play in doc['liveData']['plays']['allPlays']:
        current = (play['about']['inning'], play['about']['halfInning'])
        if current != half:
            active, outs, half = {}, 0, current
        pa = str(play['atBatIndex'])
        if play.get('result',{}).get('eventType') in {'walk','intent_walk','hit_by_pitch'}:
            selected=CONTEXT.runner_metric_evidence(play,pa,str(doc['gameData']['game']['season']))['awardAdvances']
            # Check the accepted award selector's coverage independently of
            # the emitted graph. A missing forced-advance mapping is not an
            # independently caused movement merely because its edge is absent.
            expected={str(i) for i,row in enumerate(play['runners'])
                if row['details'].get('eventType') in {'walk','intent_walk','hit_by_pitch'}}
            if {row['runnerIndex'] for row in selected}!=expected or not expected:
                issues.append(dict(code='INCOMPLETE_AWARD_ATTRIBUTION',atBatIndex=pa))
            independent={'balk','wild_pitch','passed_ball','stolen_base_2b','stolen_base_3b','stolen_base_home'}
            for i,row in enumerate(play['runners']):
                movement=row['movement']
                held=movement.get('isOut') is False and movement.get('start')==movement.get('end') and movement.get('start') in {'1B','2B','3B'}
                if str(i) not in expected and not held and row['details'].get('eventType') not in independent:
                    issues.append(dict(code='UNRESOLVED_NONAWARD_MOVEMENT',atBatIndex=pa,runnerIndex=i))
            awards.extend(dict(award=game+'/plate-appearance/'+pa+'/result',
                act=game+'/runner-act/movement/'+pa+'/'+row['runnerIndex'],rule=row['ruleIri']) for row in selected)
        boundaries.append(dict(pa=game+'/plate-appearance/'+pa, outs=outs,
            occupants=[dict(player=B.BASE+'data/player/'+runner, base=base,
                stasis=game+'/plate-appearance/'+pa+'/start-state/base/'+base+'/stasis')
                for runner,base in sorted(active.items())]))
        # History membership is already source-verified above. Follow that
        # accepted chain, rather than treating omitted post-base fields as empty.
        for whole in history['histories']:
            runner = whole['runnerId']
            for episode in whole['episodes']:
                if episode['atBatIndex'] != pa: continue
                row = play['runners'][int(episode['runnerIndex'])]
                movement = row['movement']
                if movement['isOut'] or movement['end']=='score': active.pop(runner, None)
                else: active[runner] = movement['end']
        outs = play['count']['outs']
    return dict(gamePk=game_pk, game=game, sourceSha256=B.sha(raw), sourceRevision=history['sourceRevision'],
        status='withheld' if issues else 'reconciled', issues=issues, boundaries=boundaries,
        histories=history['histories'], awards=awards,
        venue=B.BASE+'data/venue/'+B.identity(doc['gameData']['venue']['id']))


def shape_text(source):
    missing, identities, out_counts, memberships, wholes, stases = [], [], [], [], [], []
    for boundary in source['boundaries']:
        pa = B.iri(boundary['pa'])
        out_counts.append('|'.join((boundary['pa'],str(boundary['outs']))))
        pattern = f"""?count a base:PlateAppearanceStartOutCountICE ; cco:ont00001808 {pa} ; cco:ont00001773 {boundary['outs']} .
{pa} a base:PlateAppearance ; obo:BFO_0000199 ?paInterval .
?paInterval a obo:BFO_0000038 ; obo:BFO_0000222 ?startInstant ."""
        missing.append('{ FILTER NOT EXISTS { '+pattern+' } }')
        for row in boundary['occupants']:
            stases.append(row['stasis'])
            player,stasis = B.iri(row['player']),B.iri(row['stasis'])
            base = B.iri(source['venue']+'/artifact/base/'+row['base'])
            site = B.iri(source['venue']+'/site/base/'+row['base'])
            pattern=f"""{stasis} a base:PlateAppearanceStartBaserunnerAtBaseStasis ;
  obo:BFO_0000132 {pa} ; obo:BFO_0000057 {player}, {base} ; cco:ont00001918 {site} ; obo:BFO_0000199 ?interval .
{player} a cco:ont00001262 . {base} a base:Base ; obo:BFO_0000171 {site} . {site} a base:BaseSite .
?identifier a cco:ont00000649 ; cco:ont00001916 {base} ; cco:ont00001765 {B.terms([row['base']])} .
{pa} obo:BFO_0000199 ?paInterval . ?paInterval obo:BFO_0000222 ?startInstant .
?interval a obo:BFO_0000038 ; obo:BFO_0000139 ?paInterval ; obo:BFO_0000222 ?startInstant ."""
            missing.append('{ FILTER NOT EXISTS { '+pattern+' } }')
            identities.append('|'.join((boundary['pa'],row['stasis'],row['player'],source['venue']+'/site/base/'+row['base'])))
    for whole in source['histories']:
        iri=source['game']+'/runner-trajectory/'+whole['lifetimeKey']
        half=source['game']+'/inning/'+whole['inning']+'/'+whole['half']
        player=B.BASE+'data/player/'+whole['runnerId']
        wholes.append('|'.join((iri,player,half)))
        for episode in whole['episodes']:
            member=source['game']+'/runner-episode/'+episode['atBatIndex']+'/'+episode['runnerIndex']
            memberships.append('|'.join((iri,member)))
            pattern=f"""{B.iri(iri)} a obo:BFO_0000015 ; obo:BFO_0000117 {B.iri(member)} ;
obo:BFO_0000057 {B.iri(player)} ; obo:BFO_0000132 {B.iri(half)} ; obo:BFO_0000199 ?interval .
{B.iri(half)} a base:HalfInning ; obo:BFO_0000132/obo:BFO_0000132 $this .
?interval a obo:BFO_0000038 . {B.iri(member)} a base:RunnerResolutionEpisode ."""
            missing.append('{ FILTER NOT EXISTS { '+pattern+' } }')
    for award in source.get('awards',[]):
        pattern=f"""{B.iri(award['award'])} cco:ont00001803 {B.iri(award['act'])} .
{B.iri(award['rule'])} a base:BaseballRule ; cco:ont00001974 {B.iri(award['act'])} ."""
        missing.append('{ FILTER NOT EXISTS { '+pattern+' } }')
    text=SHAPE.read_text(encoding='utf-8')
    values=dict(GAME=source['game'], PREFIXES=B.PREFIXES, MISSING=' UNION '.join(missing) or 'FILTER(1=0)',
        OCCUPANTS=B.terms(identities), OUT_COUNTS=B.terms(out_counts), MEMBERSHIPS=B.terms(memberships),
        WHOLES=B.terms(wholes), AWARDS=B.terms(['|'.join(a[k] for k in ('award','act','rule')) for a in source.get('awards',[])]),
        STASES=', '.join(B.iri(s) for s in stases) or '<urn:baseballo:no-start-stases>')
    for key,value in values.items(): text=text.replace('__'+key+'__',value)
    Graph().parse(data=text,format='turtle')
    return text


def prove(*, raw, game_pk, rdf_path, output, java=None, classpath=None):
    source = census(raw, game_pk)
    implementation, rdf_sha = fingerprint(), B.sha(rdf_path.read_bytes())
    proof = dict(artifactType='baseballo-runner-boundary-admission', contractVersion=1,
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
        raise ValueError('Runner-boundary admission inputs changed during validation')
    if proof['sourceReconciled'] and proof['graphConforms']:
        proof['status'] = 'admitted'
        proof['awardAttributionComplete'] = True
    B.SOURCE.write_atomic(output, proof)
    return proof


def promoted_admission(state_root, promotion):
    withheld = dict(status='withheld', issues=[dict(code='RUNNER_BOUNDARY_PROOF_MISSING_OR_STALE')])
    marker_path = Path(promotion['promotionManifest'])
    if B.sha(marker_path.read_bytes()) != promotion['promotionManifestSha256']:
        raise ValueError('Promotion marker changed while loading run admission')
    marker = json.loads(marker_path.read_text(encoding='utf-8-sig'))
    path = Path(marker.get('runnerBoundaryAdmission', ''))
    if not path.is_file():
        return withheld
    if not path.resolve().is_relative_to((state_root/'pipeline/evidence/mlb-game'/promotion['gamePk']).resolve()):
        raise ValueError('Runner-boundary proof escaped its owning game evidence directory')
    if B.sha(path.read_bytes()) != marker.get('runnerBoundaryAdmissionSha256'):
        raise ValueError('Runner-boundary proof hash differs from promotion')
    proof = json.loads(path.read_text(encoding='utf-8'))
    if (proof.get('artifactType') != 'baseballo-runner-boundary-admission' or proof.get('contractVersion') != 1
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
            raise ValueError('Runner-boundary proof validation artifact changed: '+key)
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
        raise ValueError('Runner-boundary proof cannot overwrite source or RDF')
    raw = args.input.read_bytes()
    result = prove(raw=raw, game_pk=args.game_pk, rdf_path=args.rdf, output=args.output,
                   java=args.java, classpath=args.jena_classpath)
    if raw != args.input.read_bytes():
        raise ValueError('Runner-boundary proof source changed during validation')
    print(json.dumps(result))
