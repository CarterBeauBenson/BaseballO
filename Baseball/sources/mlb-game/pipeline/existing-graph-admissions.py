"""Run existing admission profiles against existing RDF and retained input.

The validation response may be newer than the graph's original input. Keep both
identities explicit. Passing SHACL, not a source revision or matching score,
establishes conformance. No graph mutation or RML execution belongs here.
"""
from pathlib import Path

SHORT={'batting':'b1','scoring-run':'e1','runner-resolution':'c2',
       'pitch-count':'m3','runner-boundary':'b2','defensive':'d1'}


def fingerprint(evidence,adapter):
    return evidence.hashlib.sha256(Path(__file__).read_bytes()+adapter.fingerprint().encode()).hexdigest()


def path_for(evidence,state,promotion,family,adapter):
    return evidence.refresh_path(state,promotion,SHORT[family],fingerprint(evidence,adapter))


def load(evidence,state,promotion,family,adapter):
    path=path_for(evidence,state,promotion,family,adapter);receipt=path.with_suffix('.receipt.json')
    version=fingerprint(evidence,adapter);producer=adapter.fingerprint()
    if not receipt.is_file():
        compatibility=evidence.read(evidence.COMPATIBILITY_PATH)
        context=evidence.sha(evidence.ROOT/'scripts/pipeline/prepare-rml-context.py')
        candidates=[]
        for name in ('defensiveGroundoutRepair','compoundResultRepair','intentionalWalkPrefix'):
            repair=compatibility.get(name,{})
            entry=repair.get('independentProofs',{}).get(family,{})
            if entry.get('currentImplementationSha256')==version and context==repair.get('currentContextSha256'):
                candidates.extend(entry.get('previous',[]) or [entry])
        for entry in candidates:
            candidate=evidence.refresh_path(state,promotion,SHORT[family],entry['previousImplementationSha256'])
            if candidate.with_suffix('.receipt.json').is_file():
                version=entry['previousImplementationSha256'];producer=entry['previousSourceProducerSha256']
                path=candidate;receipt=path.with_suffix('.receipt.json');break
        else:return None
    record=evidence.read(receipt)
    if record.get('promotionManifestSha256')!=promotion['promotionManifestSha256'] or record.get('proofSha256')!=evidence.sha(path):
        raise ValueError('Existing graph admission receipt changed')
    proof=evidence.read(path)
    expected=dict(artifactType='baseballo-'+family+'-admission',contractVersion=1,
        gamePk=promotion['gamePk'],graph=promotion['authoritativeGraph'],
        authoritativeRdfSha256=promotion['authoritativeRdfSha256'],promotionSourceSha256=promotion['rawSha256'],
        implementationSha256=version,sourceProducerSha256=producer)
    if any(proof.get(k)!=v for k,v in expected.items()):raise ValueError('Existing graph admission belongs to another input')
    for suffix,key in (('.source.json','sourceCensusSha256'),('.shapes.ttl','shapeSha256'),('.report.ttl','reportSha256')):
        if key in proof and evidence.sha(path.with_suffix(suffix))!=proof[key]:
            raise ValueError('Existing graph validation artifact changed')
    source=evidence.read(path.with_suffix('.source.json'))
    if source.get('sourceSha256')!=proof.get('sourceSha256') or source.get('gamePk')!=promotion['gamePk']:
        raise ValueError('Existing graph source witness differs from its census')
    if proof.get('status')=='admitted' and not all(proof.get(k) for k in
            ('sourceReconciled','graphConforms','sourceCensusSha256','shapeSha256','reportSha256')):
        raise ValueError('Existing graph admission lacks conformance evidence')
    if family=='defensive' and proof.get('status')=='admitted' and proof.get('populationComplete') is not True:
        raise ValueError('Existing graph defensive population is incomplete')
    evidence.checked_marker(promotion)
    return dict(proof,proofSha256=record['proofSha256'])


def validate(evidence,state,promotion,witness,rdf,session,java,classpath):
    """One already loaded graph; unchanged source-owned census and SHACL code."""
    source_path=Path(witness['path']);raw=source_path.read_bytes()
    if evidence.hashlib.sha256(raw).hexdigest()!=witness['sha256']:
        raise ValueError('Retained source response changed')
    results=[]
    for family in SHORT:
        adapter=evidence.module(evidence.HERE/(family+'-admission.py'),'existing_graph_'+family.replace('-','_'))
        existing=evidence.load(adapter,state,promotion,family)
        if existing.get('status')=='admitted' or load(evidence,state,promotion,family,adapter) is not None:continue
        version=fingerprint(evidence,adapter);output=path_for(evidence,state,promotion,family,adapter)
        owner=getattr(adapter,'B',adapter);original=owner.module
        owner.module=lambda path,name,loader=original: session if Path(path).name=='validate-shacl.py' else loader(path,name)
        try:
            proof=adapter.prove(raw=raw,game_pk=promotion['gamePk'],rdf_path=rdf,
                output=output,java=java,classpath=classpath)
        finally:owner.module=original
        if fingerprint(evidence,adapter)!=version or evidence.sha(source_path)!=witness['sha256']:
            raise ValueError('Existing graph validation inputs changed')
        # Preserve the original graph identity and this export's separate byte
        # hash. Never label the newer response as the original promotion input.
        proof.update(validationExportSha256=proof['authoritativeRdfSha256'],
            authoritativeRdfSha256=promotion['authoritativeRdfSha256'],
            promotionSourceSha256=promotion['rawSha256'],sourceProducerSha256=adapter.fingerprint(),
            implementationSha256=version,retainedSourceEvidence=witness)
        evidence.atomic(output,proof)
        results.append((output,family,proof['status']))
    # Receipts are committed only by the caller after its final current-graph check.
    return results


def commit(evidence,promotion,results):
    for output,_,_ in results:
        evidence.atomic(output.with_suffix('.receipt.json'),dict(artifactType='baseballo-admission-evidence-refresh',
            promotionManifestSha256=promotion['promotionManifestSha256'],proofSha256=evidence.sha(output),rdfChanged=False))
