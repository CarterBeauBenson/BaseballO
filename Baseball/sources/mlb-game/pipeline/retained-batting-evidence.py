"""Finish B1 from retained source censuses and reviewed batting participation.

The old event-position heuristic can reject a turn with only one actual batter.
Use the already serialized Q4 participation inventory to resolve that mechanical
disagreement, then run the unchanged B1 SHACL over the existing promoted graph.
No statistical-credit rule, source acquisition or RDF mutation belongs here.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import urllib.request

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


B=module(HERE/'batting-admission.py','retained_b1_contract')


def fingerprint():
    return hashlib.sha256(Path(__file__).read_bytes()+B.fingerprint().encode()).hexdigest()


def source_census(evidence,state,promotion):
    marker=evidence.checked_marker(promotion)
    path=Path(marker.get('battingAdmission',''))
    owner=(Path(state)/'pipeline/evidence/mlb-game'/promotion['gamePk']).resolve()
    if not path.is_file() or not path.resolve().is_relative_to(owner):return None
    if evidence.sha(path)!=marker.get('battingAdmissionSha256'):raise ValueError('Retained B1 proof changed')
    proof=evidence.read(path)
    supported={B.fingerprint(),evidence.read(evidence.COMPATIBILITY_PATH)['priorClockIsolation']['families']['batting']['previousImplementationSha256']}
    expected=dict(artifactType='baseballo-batting-admission',contractVersion=1,status='withheld',
        gamePk=promotion['gamePk'],sourceSha256=promotion['rawSha256'],
        authoritativeRdfSha256=promotion['authoritativeRdfSha256'],graph=promotion['authoritativeGraph'])
    if any(proof.get(k)!=v for k,v in expected.items()) or proof.get('implementationSha256') not in supported:return None
    if not proof.get('issues') or any(i.get('code')!='OFFENSIVE_REPLACEMENT_WITHIN_TURN' for i in proof['issues']):return None
    census_path=path.with_suffix('.source.json')
    if evidence.sha(census_path)!=proof.get('sourceCensusSha256'):raise ValueError('Retained B1 census changed')
    census=evidence.read(census_path)
    if (census.get('sourceConsistency')!='consistent' or census.get('issues')!=proof['issues']
            or census.get('sourceSha256')!=promotion['rawSha256'] or census.get('gamePk')!=promotion['gamePk']):return None
    manifest_path=evidence.retained_manifest(state,marker,promotion['gamePk'])
    if not manifest_path.is_file() or evidence.sha(manifest_path)!=marker['rmlManifestSha256']:return None
    manifest=evidence.read(manifest_path);compatibility=evidence.read(evidence.COMPATIBILITY_PATH)
    if (manifest.get('inputSha256')!=promotion['rawSha256'] or manifest.get('outputSha256')!=promotion['authoritativeRdfSha256']
            or manifest.get('metricMappingMembershipVerified') is not True
            or manifest.get('contextBuilderSha256') not in {compatibility['previousContextSha256'],compatibility['currentContextSha256']}):return None
    # Compare two independently retained source projections. Every turn must
    # have exactly the existing single-Batter-Act identity and the census's
    # player. Multiple actual batters cannot be resolved by matching totals.
    members=census.get('members',[]);participations=manifest.get('batterParticipationEvidence',[])
    expected_members={(str(r['atBatIndex']),r['player'],r['pa']+'/batter-act') for r in members}
    actual_members={(r['atBatIndex'],B.BASE+'data/player/'+r['playerId'],r['actIri']) for r in participations}
    if (not members or len(expected_members)!=len(members) or len(participations)!=len(members)
            or len(actual_members)!=len(participations) or actual_members!=expected_members):return None
    result=copy.deepcopy(census)
    result.update(status='reconciled',issues=[],implementationSha256=fingerprint(),
        retainedSourceEvidence=dict(originalProofSha256=evidence.sha(path),
            originalCensusSha256=evidence.sha(census_path),rmlManifestSha256=marker['rmlManifestSha256'],
            resolvedIssues=proof['issues'],basis='complete-single-batter-membership-and-reconciled-player-totals'))
    return result


def prove(evidence,state,promotion,source,java,classpath,endpoint):
    implementation=fingerprint()
    if source['implementationSha256']!=implementation:raise ValueError('B1 source adapter changed before validation')
    inventory=module(ROOT/'scripts/pipeline/game_promotion_inventory.py','retained_b1_inventory')
    marker_path=Path(promotion['promotionManifest'])
    def current():
        paths=list(marker_path.parent.glob('*.json'))
        latest=max(paths,key=lambda p:(evidence.read(p).get('promotedAtUtc',''),p.name))
        if latest!=marker_path or evidence.sha(latest)!=promotion['promotionManifestSha256']:
            raise ValueError('Promotion changed during retained B1 validation')
        return inventory.validated_promotion_record(Path(state),latest,promotion['gamePk'],inventory.query_index_contract_admission())
    record=current()
    if any(record[k]!=promotion[k] for k in ('rawSha256','authoritativeRdfSha256','authoritativeGraph')):
        raise ValueError('Retained B1 validation belongs to another promotion')
    output=evidence.refresh_path(state,promotion,'batting',fingerprint())
    output.parent.mkdir(parents=True,exist_ok=True)
    shapes=output.with_suffix('.shapes.ttl')
    shapes.write_text(B.shape_text(source),encoding='utf-8',newline='\n')
    query='CONSTRUCT { ?s ?p ?o } WHERE { GRAPH <'+record['authoritativeGraph']+'> { ?s ?p ?o } }'
    request=urllib.request.Request(endpoint,data=query.encode(),headers={
        'Content-Type':'application/sparql-query','Accept':'text/turtle'})
    session_module=module(ROOT/'scripts/pipeline/jena_session.py','retained_b1_jena')
    with tempfile.TemporaryDirectory(prefix='b1-existing-graph-') as temporary:
        rdf=Path(temporary)/'graph.ttl'
        with urllib.request.urlopen(request,timeout=120) as response,rdf.open('wb') as stream:
            size=0
            while chunk:=response.read(1024*1024):
                size+=len(chunk)
                if size>128*1024*1024:raise ValueError('Single-game B1 graph exceeds its read bound')
                stream.write(chunk)
        with session_module.Session(rdf,java,classpath) as session:
            if session.data_count!=record['authoritativeTripleCount']:
                raise ValueError('Existing graph count differs from its promotion')
            conforms,report,_=session.validate_with_jena(data_path=rdf,shape_path=shapes,
                java=java,classpath=classpath,max_heap='384m')
        export_sha=evidence.sha(rdf)
    current()
    if fingerprint()!=implementation:raise ValueError('B1 source adapter changed during validation')
    evidence.atomic(output.with_suffix('.source.json'),source)
    report_path=output.with_suffix('.report.ttl');report.serialize(destination=report_path,format='turtle')
    proof=dict(artifactType='baseballo-batting-admission',contractVersion=1,gamePk=promotion['gamePk'],
        graph=promotion['authoritativeGraph'],sourceSha256=promotion['rawSha256'],sourceRevision=source['sourceRevision'],
        authoritativeRdfSha256=promotion['authoritativeRdfSha256'],validationExportSha256=export_sha,
        implementationSha256=implementation,status='admitted' if conforms else 'withheld',sourceReconciled=True,
        graphConforms=conforms,issues=[] if conforms else [dict(code='SOURCE_GRAPH_CONFORMANCE')],engine='jena',
        sourceCensusSha256=evidence.sha(output.with_suffix('.source.json')),shapeSha256=evidence.sha(shapes),
        reportSha256=evidence.sha(report_path),retainedSourceEvidence=source['retainedSourceEvidence'])
    evidence.atomic(output,proof)
    evidence.atomic(output.with_suffix('.receipt.json'),dict(artifactType='baseballo-admission-evidence-refresh',
        promotionManifestSha256=promotion['promotionManifestSha256'],proofSha256=evidence.sha(output),rdfChanged=False))
    return proof
