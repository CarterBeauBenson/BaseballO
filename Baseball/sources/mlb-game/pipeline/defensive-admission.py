"""D1 source-owned selected-act conformance and independent population gate."""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
from rdflib import Graph, Literal

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('d1_batting_support',HERE/'batting-admission.py')
B=importlib.util.module_from_spec(spec);spec.loader.exec_module(B)
CONTEXT=B.module(ROOT/'scripts/pipeline/prepare-rml-context.py','d1_context')
SHAPE=HERE.parent/'shacl/defensive-admission.ttl'


def fingerprint():
    paths=[Path(__file__),SHAPE,HERE/'batting-admission.py',HERE/'reconcile-metric-source.py',
           ROOT/'scripts/pipeline/prepare-rml-context.py',ROOT/'scripts/pipeline/validate-shacl.py']
    return B.sha('\n'.join(p.relative_to(ROOT).as_posix()+':'+B.sha(p.read_bytes()) for p in paths).encode())


def census(raw,game_pk):
    game_pk=B.identity(int(game_pk));doc=json.loads(raw);source=B.SOURCE.reconcile(raw,game_pk)
    issues=[dict(code='SOURCE_RECONCILIATION',detail=i) for i in source['blockingIssues']]
    doc[CONTEXT.CONTEXT_KEY]={'runnerHistoryReconciliation':dict(inputSha256=B.sha(raw),
        sourceRevision=source['sourceRevision'],sourceConsistency='inconsistent' if issues else 'consistent')}
    selected=CONTEXT.defensive_act_context(doc)
    return dict(gamePk=game_pk,game=B.BASE+'data/game/'+game_pk,sourceSha256=B.sha(raw),
        sourceRevision=source['sourceRevision'],status='withheld' if issues else 'reconciled',issues=issues,
        **{k:selected[k] for k in ('acts','plays','precedence','populationComplete','orderComplete')})


def shape_text(source):
    shapes=[]
    prop=lambda path,value:'sh:property [ sh:path '+path+' ; sh:hasValue '+B.iri(value)+' ; sh:minCount 1 ; sh:maxCount 1 ]'
    def node(target,parts):shapes.append('[] a sh:NodeShape ; sh:targetNode '+B.iri(target)+' ; '+' ;\n'.join(parts)+' .')
    for row in source['acts']:
        types=[row['classIri']]+([B.BASE+'FieldingAttemptAct'] if row['catch'] else [])
        node(row['actIri'],['sh:class <'+t+'>' for t in types]+[
            'sh:property [ sh:path rdf:type ; sh:in ('+' '.join(B.iri(t) for t in types)+') ; sh:minCount '+str(len(types))+' ; sh:maxCount '+str(len(types))+' ]',
            prop('cco:ont00001833',row['agentIri']),prop('obo:BFO_0000055',row['roleIri']),
            prop('obo:BFO_0000132',row['playIri']),
            'sh:property [ sh:path obo:BFO_0000063 ; sh:maxCount 0 ]'])
        node(row['roleIri'],['sh:class base:FielderRole',prop('obo:BFO_0000197',row['agentIri'])])
        node(row['agentIri'],['sh:class cco:ont00001262'])
        node(row['recordIri'],['sh:class base:BaseballEventRecord',
            'sh:property [ sh:path cco:ont00001808 ; sh:hasValue '+B.iri(row['actIri'])+' ]'])
    for play in source['plays']:
        node(play['resolution'],['sh:class base:BattedBallPlayProcess',
             prop('obo:BFO_0000132',source['game']+'/plate-appearance/'+play['atBatIndex'])])
    members=lambda xs:', '.join(B.iri(v) for v in xs) or '<urn:baseballo:no-defensive-members>'
    query=B.PREFIXES+'''SELECT $this WHERE {
      { ?act a ?kind . FILTER(?kind IN (base:FieldingAttemptAct, base:CatchAttemptAct, base:ThrowAct, base:TagAttemptAct))
        FILTER(?act NOT IN ('''+members(r['actIri'] for r in source['acts'])+''')) }
      UNION { ?play a base:BattedBallPlayProcess .
        FILTER(?play NOT IN ('''+members(r['resolution'] for r in source['plays'])+''')) }
    }'''
    node(source['game'],['sh:sparql [ sh:message "D1 act or contact-play census differs from the source" ; sh:select '+Literal(query).n3()+' ]'])
    text=SHAPE.read_text(encoding='utf-8').replace('# __DEFENSIVE_SHAPES__','\n'.join(shapes))
    Graph().parse(data=text,format='turtle')
    return text


def prove(*, raw, game_pk, rdf_path, output, java=None, classpath=None):
    source = census(raw, game_pk)
    implementation, rdf_sha = fingerprint(), B.sha(rdf_path.read_bytes())
    proof = dict(artifactType='baseballo-defensive-admission', contractVersion=1,
        gamePk=source['gamePk'], graph='https://w3id.org/baseball/graph/game/'+source['gamePk'],
        sourceSha256=source['sourceSha256'], sourceRevision=source['sourceRevision'],
        authoritativeRdfSha256=rdf_sha, implementationSha256=implementation,
        status='withheld', sourceReconciled=source['status']=='reconciled', graphConforms=False,
        issues=source['issues'], populationComplete=source['populationComplete'],
        orderComplete=source['orderComplete'], selectedActCount=len(source['acts']),
        contactPlayCount=len(source['plays']),completePlayCount=sum(p['complete'] for p in source['plays']))
    output.parent.mkdir(parents=True, exist_ok=True)
    source_path = output.with_suffix('.source.json')
    B.SOURCE.write_atomic(source_path, source)
    proof['sourceCensusSha256'] = B.sha(source_path.read_bytes())
    if proof['sourceReconciled']:
        shapes = output.with_suffix('.shapes.ttl')
        shapes.write_text(shape_text(source), encoding='utf-8', newline='\n')
        if java:
            validator = B.module(ROOT/'scripts/pipeline/validate-shacl.py', 'd1_admission_shacl')
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
        raise ValueError('Defensive admission inputs changed during validation')
    if proof['sourceReconciled'] and proof['graphConforms'] and proof['populationComplete']:
        proof['status'] = 'admitted'
    if not proof['populationComplete']:
        proof['issues'].append(dict(code='INCOMPLETE_DEFENSIVE_POPULATION'))
    B.SOURCE.write_atomic(output, proof)
    return proof


def promoted_admission(state_root, promotion):
    withheld = dict(status='withheld', issues=[dict(code='DEFENSIVE_PROOF_MISSING_OR_STALE')])
    marker_path = Path(promotion['promotionManifest'])
    if B.sha(marker_path.read_bytes()) != promotion['promotionManifestSha256']:
        raise ValueError('Promotion marker changed while loading defensive admission')
    marker = json.loads(marker_path.read_text(encoding='utf-8-sig'))
    path = Path(marker.get('defensiveAdmission', ''))
    if not path.is_file():
        return withheld
    if not path.resolve().is_relative_to((state_root/'pipeline/evidence/mlb-game'/promotion['gamePk']).resolve()):
        raise ValueError('Defensive proof escaped its owning game evidence directory')
    if B.sha(path.read_bytes()) != marker.get('defensiveAdmissionSha256'):
        raise ValueError('Defensive proof hash differs from promotion')
    proof = json.loads(path.read_text(encoding='utf-8'))
    if (proof.get('artifactType') != 'baseballo-defensive-admission' or proof.get('contractVersion') != 1
            or proof.get('gamePk') != promotion['gamePk'] or proof.get('implementationSha256') != fingerprint()
            or proof.get('sourceSha256') != promotion['rawSha256']
            or proof.get('authoritativeRdfSha256') != promotion['authoritativeRdfSha256']
            or proof.get('graph') != promotion['authoritativeGraph']):
        return withheld
    if proof.get('status') == 'admitted' and any(not proof.get(key) for key in
            ('sourceCensusSha256','shapeSha256','reportSha256','populationComplete','sourceReconciled','graphConforms')):
        raise ValueError('Admitted defensive proof lacks retained validation artifact hashes')
    for suffix, key in (('.source.json','sourceCensusSha256'), ('.shapes.ttl','shapeSha256'), ('.report.ttl','reportSha256')):
        if key in proof and B.sha(path.with_suffix(suffix).read_bytes()) != proof[key]:
            raise ValueError('Defensive proof validation artifact changed: '+key)
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
        raise ValueError('Defensive proof cannot overwrite source or RDF')
    raw = args.input.read_bytes()
    result = prove(raw=raw, game_pk=args.game_pk, rdf_path=args.rdf, output=args.output,
                   java=args.java, classpath=args.jena_classpath)
    if raw != args.input.read_bytes():
        raise ValueError('Defensive proof source changed during validation')
    print(json.dumps(result))
    if result['sourceReconciled'] and not result['graphConforms']:
        raise SystemExit('D1 selected-act SHACL failed; promotion must stop')
