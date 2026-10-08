"""Scope the existing runner-resolution SHACL to individual batting turns.

No source selection, RDF assertion or metric formula changes. Failed and
unknown turns stay separate from turns whose entire resolution census passes.
"""
from pathlib import Path
import importlib.util
import json
import re
import tempfile
import urllib.request
from rdflib import Namespace

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('scoped_resolution_contract',HERE/'runner-resolution-admission.py')
R=importlib.util.module_from_spec(spec);spec.loader.exec_module(R)
SHAPE=HERE.parent/'shacl/pa-resolution-admission.ttl'
SH=Namespace('http://www.w3.org/ns/shacl#')
PREVIOUS_SCOPE_IMPLEMENTATION='b641f925ecda8d47e75e3cd0089b88f93b74a615ab8d63fecf7f14ca8924be4a'


def with_reconciliation_scope(source, raw):
    """Retain source locations, not replacement totals or inferred outcomes."""
    doc=json.loads(raw);resolution=source['resolution'];batting=source['batting']
    if (R.B.sha(raw)!=resolution['sourceSha256'] or
            resolution['sourceSha256']!=batting['sourceSha256']):
        raise ValueError('Scoped reconciliation witness differs from census')
    plays=doc['liveData']['plays']['allPlays'];game=resolution['game']
    pas=[game+'/plate-appearance/'+str(p.get('atBatIndex')) for p in plays]
    if pas!=[m['pa'] for m in batting['members']] or len(set(pas))!=len(pas):
        raise ValueError('Scoped reconciliation PA inventory differs from census')
    scopes=[]
    for issue in resolution.get('issues',[]):
        if issue.get('code')!='SOURCE_RECONCILIATION':continue
        detail=issue.get('detail',{});path=detail.get('path','');affected=None
        if detail.get('code')=='INCOMPLETE_SOURCE_PLAY':
            match=re.fullmatch(r'/liveData/plays/allPlays/(\d+)/about/isComplete',path)
            if match and int(match[1])<len(plays):
                position=int(match[1])
                if plays[position].get('about',{}).get('isComplete') is not True:
                    affected=[pas[position]]
        elif detail.get('code')=='INNING_RUN_TOTAL_MISMATCH' and detail.get('reported') is None:
            match=re.fullmatch(r'/liveData/linescore/innings/(\d+)/(away|home)',path)
            innings=doc.get('liveData',{}).get('linescore',{}).get('innings',[])
            if match and int(match[1])<len(innings):
                row=innings[int(match[1])];number=row.get('num');side=match[2]
                if (type(number) is int and number>0 and row.get(side,{}).get('runs') is None
                        and sum(i.get('num')==number for i in innings)==1):
                    half='top' if side=='away' else 'bottom'
                    affected=[pa for pa,p in zip(pas,plays)
                        if p.get('about',{}).get('inning')==number
                        and p.get('about',{}).get('halfInning')==half]
        if affected:scopes.append(dict(issue=issue,plateAppearances=affected))
    return dict(source,reconciliationScopes=scopes)


def fingerprint():
    return R.B.sha(Path(__file__).read_bytes()+SHAPE.read_bytes()+R.fingerprint().encode())


def proof_path(evidence,state,promotion):
    return evidence.refresh_path(state,promotion,'c2pa',fingerprint())


def retained_source(evidence,state,promotion):
    marker=evidence.checked_marker(promotion)
    independent=evidence.EXISTING_GRAPH.load(evidence,state,promotion,'runner-resolution',R)
    if independent is not None:
        path=evidence.refresh_path(state,promotion,'c2',independent['implementationSha256'])
        census=path.with_suffix('.source.json');witness=independent['retainedSourceEvidence']
        if not Path(witness['path']).is_file():
            retained=evidence.retained_raw_witness(state,dict(promotion,rawSha256=independent['sourceSha256']))
            if retained and retained['sha256']==independent['sourceSha256']:
                witness=dict(retained,originalWitness=witness)
        if not Path(witness['path']).is_file():
            # Successful promotion retires transient JSON. The independent
            # B1 check already retained the same response's PA census; reuse
            # its verified artifact instead of requiring those raw bytes.
            batting=evidence.EXISTING_GRAPH.load(evidence,state,promotion,'batting',R.B)
            if batting is None or batting.get('sourceSha256')!=independent['sourceSha256']:
                return None
            batting_path=evidence.refresh_path(state,promotion,'b1',batting['implementationSha256']).with_suffix('.source.json')
            if evidence.sha(batting_path)!=batting.get('sourceCensusSha256'):
                raise ValueError('Retained independent batting census changed')
            source=evidence.read(batting_path)
            if source.get('sourceSha256')!=independent['sourceSha256'] or source.get('gamePk')!=promotion['gamePk']:
                raise ValueError('Retained independent batting census belongs to another source')
            return dict(resolution=evidence.read(census),batting=source),[
                dict(path=str(census),sha256=evidence.sha(census)),
                dict(path=str(batting_path),sha256=evidence.sha(batting_path))]
        raw=Path(witness['path']).read_bytes()
        if R.B.sha(raw)!=witness['sha256'] or witness['sha256']!=independent['sourceSha256']:
            raise ValueError('Scoped resolution validation witness changed')
        # Keep the later witness's identity; it is never called the original
        # promotion input. Its PA inventory uses the existing B1 census code.
        return with_reconciliation_scope(dict(resolution=evidence.read(census),
            batting=R.B.census(raw,promotion['gamePk'])),raw),[
            dict(path=str(census),sha256=evidence.sha(census)),witness]
    path=Path(marker.get('runnerResolutionAdmission',''))
    owner=(Path(state)/'pipeline/evidence/mlb-game'/promotion['gamePk']).resolve()
    if not path.is_file():return None
    if not path.resolve().is_relative_to(owner) or evidence.sha(path)!=marker.get('runnerResolutionAdmissionSha256'):
        raise ValueError('Retained resolution proof changed')
    proof=evidence.read(path)
    if any(proof.get(k)!=v for k,v in dict(gamePk=promotion['gamePk'],sourceSha256=promotion['rawSha256'],
            authoritativeRdfSha256=promotion['authoritativeRdfSha256'],graph=promotion['authoritativeGraph']).items()):return None
    version=proof.get('implementationSha256')
    if version!=R.fingerprint() and evidence.code_equivalence('runner-resolution',version,R.fingerprint()) is None:return None
    census=path.with_suffix('.source.json')
    if evidence.sha(census)!=proof.get('sourceCensusSha256'):raise ValueError('Retained resolution census changed')
    batting=evidence.PLAYER_PARTICIPATION.retained_source(evidence,state,promotion)
    if batting is None or batting[0].get('sourceSha256')!=promotion['rawSha256']:return None
    source=evidence.read(census)
    if source.get('gamePk')!=promotion['gamePk'] or source.get('sourceSha256')!=promotion['rawSha256']:
        raise ValueError('Resolution census belongs to another source')
    return dict(resolution=source,batting=batting[0]),[
        dict(path=str(census),sha256=evidence.sha(census)),batting[1]]


def shape_text(source):
    resolution=source['resolution'];batting=source['batting']
    if (resolution['game']!=batting['game'] or resolution['sourceSha256']!=batting['sourceSha256']):
        raise ValueError('Scoped resolution source identities differ')
    pas=[r['pa'] for r in batting['members']]
    if len(set(pas))!=len(pas):raise ValueError('Ambiguous source PA inventory')
    unknown={r['pa'] for r in resolution['resolutions']+resolution.get('nonMovementRecords',[])}-set(pas)
    texts=['@prefix sh: <http://www.w3.org/ns/shacl#> .'];members=[]
    for pa in pas:
        issues=[]
        for issue in resolution.get('issues',[]):
            index=issue.get('atBatIndex')
            if issue.get('code')=='UNRESOLVED_RUNNER_BOUNDARY' and index is not None:
                if resolution['game']+'/plate-appearance/'+str(index)==pa:issues.append(issue)
                continue
            scope=next((s['plateAppearances'] for s in source.get('reconciliationScopes',[])
                if s['issue']==issue),None)
            # Q6 completeness diagnostics remain in the whole-game census.
            # An unaffected PA still must pass its complete existing C2 shape.
            # Unknown issues, absent scope and identity/membership faults stay global.
            if scope is None or pa in scope:issues.append(issue)
        if unknown:issues.append(dict(code='SOURCE_PA_INVENTORY'))
        member=dict(plateAppearance=pa,status='withheld' if issues else 'pending',issues=issues)
        members.append(member)
        if issues:continue
        selected=dict(resolution,resolutions=[r for r in resolution['resolutions'] if r['pa']==pa],
            nonMovementRecords=[r for r in resolution.get('nonMovementRecords',[]) if r['pa']==pa])
        original=R.SHAPE
        try:
            R.SHAPE=SHAPE
            text=R.shape_text(selected)
        finally:R.SHAPE=original
        shape='urn:baseballo:validation:pa-resolution:'+pa.rsplit('/',1)[-1]
        text=text.replace('__SHAPE__',shape).replace('__PA__',pa)
        texts.append(text);member['shape']=shape
    return '\n'.join(texts),members


def outcome(members,report):
    failures={str(n) for n in report.objects(None,SH.sourceShape)}
    for member in members:
        if member['status']!='pending':continue
        member['status']='withheld' if member.pop('shape') in failures else 'admitted'
        if member['status']=='withheld':member['issues'].append(dict(code='PA_RESOLUTION_GRAPH_CONFORMANCE'))
    return members


def load(evidence,state,promotion):
    path=proof_path(evidence,state,promotion);receipt=path.with_suffix('.receipt.json')
    version=fingerprint()
    for prior in evidence.prior_versions('c2pa',version):
        if receipt.is_file():break
        path=evidence.refresh_path(state,promotion,'c2pa',prior);receipt=path.with_suffix('.receipt.json');version=prior
    if not receipt.is_file():return None
    record=evidence.read(receipt)
    if record.get('promotionManifestSha256')!=promotion['promotionManifestSha256'] or record.get('proofSha256')!=evidence.sha(path):
        raise ValueError('Scoped resolution receipt changed')
    proof=evidence.read(path)
    expected=dict(artifactType='baseballo-pa-resolution-admission',contractVersion=1,
        gamePk=promotion['gamePk'],graph=promotion['authoritativeGraph'],
        promotionSourceSha256=promotion['rawSha256'],authoritativeRdfSha256=promotion['authoritativeRdfSha256'],
        implementationSha256=version)
    if any(proof.get(k)!=v for k,v in expected.items()):raise ValueError('Scoped resolution belongs to another input')
    for suffix,key in (('.source.json','sourceCensusSha256'),('.shapes.ttl','shapeSha256'),('.report.ttl','reportSha256')):
        if evidence.sha(path.with_suffix(suffix))!=proof.get(key):raise ValueError('Scoped resolution artifact changed')
    source=evidence.read(path.with_suffix('.source.json'))
    if any(source[k].get('sourceSha256')!=proof.get('sourceSha256') or source[k].get('gamePk')!=promotion['gamePk']
            for k in ('resolution','batting')):raise ValueError('Scoped resolution source identities changed')
    evidence.checked_marker(promotion)
    if version!=fingerprint() and any(i.get('code')=='SOURCE_RECONCILIATION' and
            (i.get('detail',{}).get('code')=='INCOMPLETE_SOURCE_PLAY' or
             i.get('detail',{}).get('code')=='INNING_RUN_TOTAL_MISMATCH' and
             i.get('detail',{}).get('reported') is None)
            for i in source['resolution'].get('issues',[])):
        return None
    return dict(proof,proofSha256=record['proofSha256'])


def prove(evidence,state,promotion,retained,java,classpath,endpoint):
    source,witnesses=retained;version=fingerprint()
    inventory=evidence.module(evidence.ROOT/'scripts/pipeline/game_promotion_inventory.py','scoped_resolution_inventory')
    marker=Path(promotion['promotionManifest'])
    def current():
        latest=max(marker.parent.glob('*.json'),key=lambda p:(evidence.read(p).get('promotedAtUtc',''),p.name))
        if latest!=marker or evidence.sha(latest)!=promotion['promotionManifestSha256']:
            raise ValueError('Promotion changed during scoped resolution validation')
        record=inventory.validated_promotion_record(Path(state),latest,promotion['gamePk'],inventory.query_index_contract_admission())
        if any(record[k]!=promotion[k] for k in ('rawSha256','authoritativeRdfSha256','authoritativeGraph')):
            raise ValueError('Scoped resolution graph identity changed')
        return record
    record=current();text,members=shape_text(source)
    output=proof_path(evidence,state,promotion);output.parent.mkdir(parents=True,exist_ok=True)
    shapes=output.with_suffix('.shapes.ttl');shapes.write_text(text,encoding='utf-8',newline='\n')
    query='CONSTRUCT { ?s ?p ?o } WHERE { GRAPH <'+record['authoritativeGraph']+'> { ?s ?p ?o } }'
    request=urllib.request.Request(endpoint,data=query.encode(),headers={'Content-Type':'application/sparql-query','Accept':'text/turtle'})
    jena=evidence.module(evidence.ROOT/'scripts/pipeline/jena_session.py','scoped_resolution_jena')
    with tempfile.TemporaryDirectory(prefix='pa-resolution-') as temporary:
        rdf=Path(temporary)/'graph.ttl'
        with urllib.request.urlopen(request,timeout=120) as response,rdf.open('wb') as stream:
            size=0
            while chunk:=response.read(1024*1024):
                size+=len(chunk)
                if size>128*1024*1024:raise ValueError('Scoped resolution exceeds one-game read bound')
                stream.write(chunk)
        with jena.Session(rdf,java,classpath) as session:
            if session.data_count!=record['authoritativeTripleCount']:raise ValueError('Scoped resolution graph count changed')
            _,report,_=session.validate_with_jena(data_path=rdf,shape_path=shapes,java=java,classpath=classpath,max_heap='384m')
        export_sha=evidence.sha(rdf)
    current()
    if fingerprint()!=version or any(evidence.sha(Path(w['path']))!=w['sha256'] for w in witnesses):
        raise ValueError('Scoped resolution inputs changed during validation')
    evidence.atomic(output.with_suffix('.source.json'),source)
    report_path=output.with_suffix('.report.ttl');report.serialize(destination=report_path,format='turtle')
    proof=dict(artifactType='baseballo-pa-resolution-admission',contractVersion=1,gamePk=promotion['gamePk'],
        graph=promotion['authoritativeGraph'],promotionSourceSha256=promotion['rawSha256'],
        sourceSha256=source['resolution']['sourceSha256'],
        authoritativeRdfSha256=promotion['authoritativeRdfSha256'],validationExportSha256=export_sha,
        implementationSha256=version,engine='jena',retainedSourceEvidence=witnesses,
        sourceCensusSha256=evidence.sha(output.with_suffix('.source.json')),shapeSha256=evidence.sha(shapes),
        reportSha256=evidence.sha(report_path),plateAppearances=outcome(members,report))
    evidence.atomic(output,proof)
    evidence.atomic(output.with_suffix('.receipt.json'),dict(promotionManifestSha256=promotion['promotionManifestSha256'],
        proofSha256=evidence.sha(output),rdfChanged=False))
    return proof
