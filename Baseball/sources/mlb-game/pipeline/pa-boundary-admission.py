"""Independent C1/C2 PA admission, preserving every half-history dependency."""
from pathlib import Path
from rdflib import Graph,Namespace,RDF,URIRef
import importlib.util

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('pa_boundary_contract',HERE/'runner-boundary-admission.py')
B=importlib.util.module_from_spec(spec);spec.loader.exec_module(B)
SHAPE=HERE.parent/'shacl/pa-boundary-admission.ttl'
BASE=Namespace(B.B.BASE);OBO=Namespace('http://purl.obolibrary.org/obo/');SH=Namespace('http://www.w3.org/ns/shacl#')


def fingerprint():
    return B.B.sha(Path(__file__).read_bytes()+SHAPE.read_bytes()+B.fingerprint().encode())


def retained_source(evidence,state,promotion):
    marker=evidence.checked_marker(promotion);path=Path(marker.get('runnerBoundaryAdmission',''))
    owner=(Path(state)/'pipeline/evidence/mlb-game'/promotion['gamePk']).resolve()
    if not path.is_file():return None
    if not path.resolve().is_relative_to(owner) or evidence.sha(path)!=marker.get('runnerBoundaryAdmissionSha256'):
        raise ValueError('Retained PA boundary proof changed')
    proof=evidence.read(path);census=path.with_suffix('.source.json')
    if (proof.get('sourceSha256')!=promotion['rawSha256'] or proof.get('gamePk')!=promotion['gamePk']
            or proof.get('authoritativeRdfSha256')!=promotion['authoritativeRdfSha256']):return None
    version=proof.get('implementationSha256')
    if version!=B.fingerprint() and evidence.code_equivalence('runner-boundary',version,B.fingerprint()) is None:return None
    if evidence.sha(census)!=proof.get('sourceCensusSha256'):raise ValueError('Retained PA boundary census changed')
    return evidence.read(census),dict(path=str(census),sha256=evidence.sha(census))


def source_issues(source,pa,half):
    issues=[]
    for issue in source.get('issues',[]):
        code=issue['code'];detail=issue.get('detail',{})
        if code=='INCOMPLETE_PERSONAL_HISTORIES':
            expected=source['game']+'/inning/'+str(detail.get('inning'))+'/'+str(detail.get('half'))
            if detail.get('inning') is None or detail.get('half') is None or expected==half:issues.append(issue)
        elif code in {'UNSUPPORTED_PA_START_BOUNDARY','INCOMPLETE_AWARD_ATTRIBUTION','UNRESOLVED_NONAWARD_MOVEMENT'}:
            index=detail.get('atBatIndex') if code=='UNSUPPORTED_PA_START_BOUNDARY' else issue.get('atBatIndex')
            if index is None or source['game']+'/plate-appearance/'+str(index)==pa:issues.append(issue)
        else:issues.append(issue)  # Unknown scope is never silently localized.
    return issues


def shape_text(source,halves):
    texts=['@prefix sh: <http://www.w3.org/ns/shacl#> .'];members=[]
    for boundary in source['boundaries']:
        pa=boundary['pa'];half=halves.get(pa)
        issues=source_issues(source,pa,half) if half else [dict(code='PA_HALF_MEMBERSHIP')]
        member=dict(plateAppearance=pa,status='withheld' if issues else 'pending',issues=issues)
        members.append(member)
        if issues:continue
        selected=dict(source,boundaries=[boundary],
            histories=[h for h in source['histories'] if source['game']+'/inning/'+str(h['inning'])+'/'+h['half']==half],
            awards=[a for a in source.get('awards',[]) if a['award']==pa+'/result'])
        original=B.SHAPE
        try:
            B.SHAPE=SHAPE
            text=B.shape_text(selected)
        finally:B.SHAPE=original
        shape='urn:baseballo:validation:pa-boundary:'+pa.rsplit('/',1)[-1]
        # These remaining parameters only identify validation targets/scopes.
        for key,value in [('SHAPE',shape),('PA',pa),('HALF',half)]:text=text.replace('__'+key+'__',value)
        member['shape']=shape;texts.append(text)
    return '\n'.join(texts),members


def prove(evidence,state,promotion,rdf,session,java,classpath,raw_witness=None):
    retained=retained_source(evidence,state,promotion)
    if retained is None:
        if not raw_witness:return None
        path=Path(raw_witness['path']);raw=path.read_bytes()
        if B.B.sha(raw)!=raw_witness['sha256']:raise ValueError('PA boundary witness changed')
        source=B.census(raw,promotion['gamePk']);witness=raw_witness
    else:source,witness=retained
    data=Graph().parse(rdf);halves={}
    for pa in data.subjects(RDF.type,BASE.PlateAppearance):
        values={str(h) for h in data.objects(pa,OBO.BFO_0000132) if (h,RDF.type,BASE.HalfInning) in data}
        if len(values)==1:halves[str(pa)]=next(iter(values))
    del data
    text,members=shape_text(source,halves)
    output=evidence.refresh_path(state,promotion,'pa',fingerprint());output.parent.mkdir(parents=True,exist_ok=True)
    shapes=output.with_suffix('.shapes.ttl');shapes.write_text(text,encoding='utf-8',newline='\n')
    _,report,_=session.validate_with_jena(data_path=rdf,shape_path=shapes,java=java,classpath=classpath,max_heap='384m')
    failures={str(n) for n in report.objects(None,SH.sourceShape)}
    for member in members:
        if member['status']!='pending':continue
        member['status']='withheld' if member['shape'] in failures else 'admitted'
        if member['status']=='withheld':member['issues'].append(dict(code='PA_BOUNDARY_GRAPH_CONFORMANCE'))
        member.pop('shape')
    evidence.atomic(output.with_suffix('.source.json'),source)
    report_path=output.with_suffix('.report.ttl');report.serialize(destination=report_path,format='turtle')
    if evidence.sha(Path(witness['path']))!=witness['sha256']:raise ValueError('PA boundary witness changed during validation')
    result=dict(implementationSha256=fingerprint(),sourceCensusSha256=evidence.sha(output.with_suffix('.source.json')),
        shapeSha256=evidence.sha(shapes),reportSha256=evidence.sha(report_path),retainedSourceEvidence=witness,
        sourceSha256=source['sourceSha256'],plateAppearances=members)
    evidence.atomic(output,result)
    return dict(result,path=str(output),proofSha256=evidence.sha(output))


def verify(evidence,state,promotion,proof):
    if not proof:return
    version=proof.get('implementationSha256')
    if version not in [fingerprint(),*evidence.prior_versions('pa',fingerprint())]:
        raise ValueError('PA boundary producer is not compatible')
    path=evidence.refresh_path(state,promotion,'pa',version)
    if (Path(proof.get('path','')).resolve()!=path.resolve()
            or proof.get('proofSha256')!=evidence.sha(path)
            or proof.get('implementationSha256')!=version):
        raise ValueError('PA boundary admission changed')
    stored=evidence.read(path)
    if stored!={k:v for k,v in proof.items() if k not in {'path','proofSha256'}}:
        raise ValueError('PA boundary admission differs from parent proof')
    for suffix,key in (('.source.json','sourceCensusSha256'),('.shapes.ttl','shapeSha256'),('.report.ttl','reportSha256')):
        if evidence.sha(path.with_suffix(suffix))!=proof.get(key):raise ValueError('PA boundary artifact changed')
    source=evidence.read(path.with_suffix('.source.json'))
    if source.get('gamePk')!=promotion['gamePk'] or source.get('sourceSha256')!=proof.get('sourceSha256'):
        raise ValueError('PA boundary source identity changed')
