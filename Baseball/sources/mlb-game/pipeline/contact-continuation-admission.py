"""NiFi's source-owned B2 membership proof; no scores or domain RDF are minted."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

from rdflib import Graph, URIRef

ROOT = Path(__file__).resolve().parents[3]
SHAPE = ROOT/'sources/mlb-game/shacl/contact-continuation.ttl'
CONTEXT_PATH = ROOT/'scripts/pipeline/prepare-rml-context.py'


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


CONTEXT = module(CONTEXT_PATH, 'b2_context')
SOURCE = module(ROOT/'sources/mlb-game/pipeline/reconcile-metric-source.py', 'b2_source')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def census(raw, game_pk):
    document = json.loads(raw)
    if str(document.get('gamePk')) != str(game_pk):
        raise ValueError('B2 game identity differs from source')
    histories = CONTEXT.personal_runner_histories(raw)
    plays = []
    for play in document['liveData']['plays']['allPlays']:
        if play.get('result', {}).get('eventType') not in CONTEXT.BATTED_RUNNER_RESULT_TYPES:
            continue
        if not any(r.get('details', {}).get('eventType') == 'other_out' for r in play.get('runners', [])):
            continue
        pa = str(play['about']['atBatIndex'])
        links = CONTEXT.batted_runner_resolution_links(play, pa, histories)
        contacts = [e for e in play['playEvents'] if e.get('isPitch') is True and e.get('details', {}).get('isInPlay') is True]
        play_id = contacts[-1].get('playId') if contacts else None
        # An absent stable identity cannot license an invented target node.
        if not isinstance(play_id, str) or not CONTEXT.SAFE_IRI_SEGMENT.fullmatch(play_id):
            plays.append(dict(atBatIndex=pa, status='withheld', links=[], memberships=[]))
            continue
        plays.append(dict(atBatIndex=pa, playId=play_id, status='admitted' if links else 'withheld', links=links,
            memberships=[m for m in histories.get('episodeMembership', []) if m['atBatIndex']==pa] if links else []))
    return dict(gamePk=str(game_pk), sourceSha256=sha(raw), plays=plays)


def shape_text(source):
    shapes = []
    root = 'https://baseballontology.org/data/game/'+source['gamePk']
    def term(value): return URIRef(value).n3()
    for play in source['plays']:
        if 'playId' not in play:
            continue
        target = root+'/process/batted-ball-play/'+play['playId']
        properties = [f'''sh:property [ sh:path obo:BFO_0000117 ;
          sh:qualifiedValueShape [ sh:class base:RunnerResolutionProcess ] ;
          sh:qualifiedMinCount {len(play['links'])} ; sh:qualifiedMaxCount {len(play['links'])} ]''']
        for row in play['links']:
            # Reuse exactly the existing Runner*Source resolution IRI templates.
            resolution = root+'/runner-resolution/'+row['resolutionKind']+'/'+row['atBatIndex']+'/'+row['runnerIndex']
            properties.append('sh:property [ sh:path obo:BFO_0000117 ; sh:hasValue '+term(resolution)+' ]')
        shapes.append('[] a sh:NodeShape ; sh:targetNode '+term(target)+' ; '+ ' ;\n'.join(properties)+' .')
        for item in play['memberships']:
            whole = root+'/runner-trajectory/'+item['lifetimeKey']
            episode = root+'/runner-episode/'+item['atBatIndex']+'/'+item['runnerIndex']
            shapes.append('[] a sh:NodeShape ; sh:targetNode '+term(whole)+' ; sh:property [ sh:path obo:BFO_0000117 ; sh:hasValue '+term(episode)+' ] .')
    text = SHAPE.read_text(encoding='utf-8').replace('# __CONTINUATION_SHAPES__', '\n'.join(shapes))
    Graph().parse(data=text, format='turtle')
    return text


def prove(raw, game_pk, rdf_path, output, java=None, classpath=None):
    source = census(raw, game_pk)
    paths = [Path(__file__), CONTEXT_PATH, SHAPE]
    implementation = sha(b''.join(p.read_bytes() for p in paths))
    rdf_sha = sha(rdf_path.read_bytes())
    output.parent.mkdir(parents=True, exist_ok=True)
    shapes = output.with_suffix('.shapes.ttl')
    shapes.write_text(shape_text(source), encoding='utf-8', newline='\n')
    SOURCE.write_atomic(output.with_suffix('.source.json'), source)
    if java:
        validator = module(ROOT/'scripts/pipeline/validate-shacl.py', 'b2_validator')
        conforms, report, _ = validator.validate_with_jena(data_path=rdf_path.resolve(), shape_path=shapes.resolve(),
            java=java, classpath=classpath, max_heap='384m')
    else:
        from pyshacl import validate
        conforms, report, _ = validate(Graph().parse(rdf_path), shacl_graph=Graph().parse(shapes), inference='none', advanced=True)
    report_path = output.with_suffix('.report.ttl')
    report.serialize(destination=report_path, format='turtle')
    if rdf_sha != sha(rdf_path.read_bytes()) or implementation != sha(b''.join(p.read_bytes() for p in paths)):
        raise ValueError('B2 inputs changed during validation')
    proof = dict(artifactType='baseballo-contact-continuation-admission', contractVersion=1, gamePk=str(game_pk),
        sourceSha256=source['sourceSha256'], authoritativeRdfSha256=rdf_sha, implementationSha256=implementation,
        status='validated' if conforms else 'failed', conforms=bool(conforms),
        admittedPlays=sum(p['status']=='admitted' for p in source['plays']), withheldPlays=sum(p['status']=='withheld' for p in source['plays']),
        shapeSha256=sha(shapes.read_bytes()), reportSha256=sha(report_path.read_bytes()),
        sourceCensusSha256=sha(output.with_suffix('.source.json').read_bytes()))
    SOURCE.write_atomic(output, proof)
    return proof


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ('input','rdf','output'): parser.add_argument('--'+arg, type=Path, required=True)
    parser.add_argument('--game-pk', required=True)
    parser.add_argument('--java', type=Path)
    parser.add_argument('--jena-classpath', type=Path)
    args = parser.parse_args()
    if args.java and not args.jena_classpath:
        parser.error('--java requires --jena-classpath')
    proof = prove(args.input.read_bytes(), args.game_pk, args.rdf, args.output, args.java, args.jena_classpath)
    print(json.dumps(proof))
    raise SystemExit(0 if proof['conforms'] else 1)
