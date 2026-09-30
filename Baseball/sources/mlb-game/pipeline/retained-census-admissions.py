"""Check existing RDF against hash-bound retained source censuses.

This uses each source owner's unchanged conformance routine. It neither
reconstructs raw input nor relabels the original census producer as current.
"""
import copy
from pathlib import Path


def fingerprint(evidence,adapter):
    return evidence.hashlib.sha256(Path(__file__).read_bytes()+adapter.fingerprint().encode()).hexdigest()


def source(evidence,state,promotion,family,adapter):
    marker=evidence.checked_marker(promotion);field=evidence.FIELDS[family]
    path=Path(marker.get(field,''));owner=(Path(state)/'pipeline/evidence/mlb-game'/promotion['gamePk']).resolve()
    if not path.is_file() or not path.resolve().is_relative_to(owner):return None
    if evidence.sha(path)!=marker.get(field+'Sha256'):raise ValueError('Retained source proof changed')
    proof=evidence.read(path);version=proof.get('implementationSha256')
    # B1's own retained-census adapter handles historical official-PA rules.
    # Its producer binds the census version internally; do not relabel it.
    if family=='batting' and version!=adapter.fingerprint():return None
    if any(proof.get(k)!=v for k,v in dict(gamePk=promotion['gamePk'],sourceSha256=promotion['rawSha256'],
            authoritativeRdfSha256=promotion['authoritativeRdfSha256'],graph=promotion['authoritativeGraph']).items()):return None
    if version!=adapter.fingerprint():
        reuse=evidence.code_equivalence(family,version,adapter.fingerprint())
        if reuse is None:return None
        if reuse['kind']=='prior-stricter-defensive-selection' and proof.get('status')!='admitted':return None
    path=path.with_suffix('.source.json')
    if not path.is_file() or evidence.sha(path)!=proof.get('sourceCensusSha256'):raise ValueError('Retained source census changed')
    census=evidence.read(path)
    if census.get('gamePk')!=promotion['gamePk'] or census.get('sourceSha256')!=promotion['rawSha256']:
        raise ValueError('Retained census belongs to another source')
    # K1 changed the expected compound result type; preserve the old census as
    # evidence, but require a current witness for precisely those members.
    if family=='batting' and any(r.get('eventType')=='strikeout_double_play' and
            r.get('resultType')!='https://baseballontology.org/DoublePlayProcess' for r in census.get('members',[])):return None
    return dict(kind='retained-source-census',path=str(path),sha256=evidence.sha(path),
                censusProducerSha256=version,sourceSha256=census['sourceSha256'])


def path_for(evidence,state,promotion,family,adapter):
    # One full digest binds both identities. Concatenating two 64-character
    # hashes made the runner-resolution sidecar exceed Windows MAX_PATH.
    key=evidence.hashlib.sha256((promotion['promotionManifestSha256']+fingerprint(evidence,adapter)).encode()).hexdigest()
    return Path(state)/'pipeline/evidence/mlb-game'/promotion['gamePk']/'admission-refresh'/('census-'+key)/(family+'.json')


def load(evidence,state,promotion,family,adapter):
    path=path_for(evidence,state,promotion,family,adapter);receipt=path.with_suffix('.receipt.json')
    if not receipt.is_file():return None
    record=evidence.read(receipt)
    if record.get('promotionManifestSha256')!=promotion['promotionManifestSha256'] or record.get('proofSha256')!=evidence.sha(path):
        raise ValueError('Retained census receipt changed')
    proof=evidence.read(path)
    expected=dict(gamePk=promotion['gamePk'],graph=promotion['authoritativeGraph'],
        authoritativeRdfSha256=promotion['authoritativeRdfSha256'],sourceSha256=promotion['rawSha256'],
        implementationSha256=fingerprint(evidence,adapter),sourceProducerSha256=adapter.fingerprint())
    if any(proof.get(k)!=v for k,v in expected.items()):raise ValueError('Retained census admission belongs to another input')
    for suffix,key in (('.source.json','sourceCensusSha256'),('.shapes.ttl','shapeSha256'),('.report.ttl','reportSha256')):
        if key in proof and evidence.sha(path.with_suffix(suffix))!=proof[key]:raise ValueError('Retained census validation artifact changed')
    witness=proof['retainedSourceEvidence']
    if evidence.sha(Path(witness['path']))!=witness['sha256']:raise ValueError('Original retained census changed')
    if proof.get('status')=='admitted' and not all(proof.get(k) for k in
            ('sourceReconciled','graphConforms','sourceCensusSha256','shapeSha256','reportSha256')):
        raise ValueError('Retained census admission lacks conformance evidence')
    evidence.checked_marker(promotion)
    return dict(proof,proofSha256=record['proofSha256'])


def validate(evidence,state,promotion,witnesses,rdf,session,java,classpath):
    results=[]
    for family,witness in witnesses.items():
        adapter=evidence.module(evidence.HERE/(family+'-admission.py'),'retained_census_'+family.replace('-','_'))
        version=fingerprint(evidence,adapter)
        if evidence.sha(Path(witness['path']))!=witness['sha256']:raise ValueError('Retained census changed before validation')
        census=evidence.read(Path(witness['path']));output=path_for(evidence,state,promotion,family,adapter)
        owner=getattr(adapter,'B',adapter);original=owner.module;original_census=adapter.census
        owner.module=lambda path,name,loader=original: session if Path(path).name=='validate-shacl.py' else loader(path,name)
        adapter.census=lambda raw,game_pk:copy.deepcopy(census)
        try:
            proof=adapter.prove(raw=b'',game_pk=promotion['gamePk'],rdf_path=rdf,output=output,java=java,classpath=classpath)
        finally:owner.module=original;adapter.census=original_census
        if version!=fingerprint(evidence,adapter) or evidence.sha(Path(witness['path']))!=witness['sha256']:
            raise ValueError('Retained census validation inputs changed')
        proof.update(validationExportSha256=proof['authoritativeRdfSha256'],
            authoritativeRdfSha256=promotion['authoritativeRdfSha256'],implementationSha256=version,
            sourceProducerSha256=adapter.fingerprint(),censusProducerSha256=witness['censusProducerSha256'],
            retainedSourceEvidence=witness)
        evidence.atomic(output,proof);results.append((output,family,proof['status']))
    return results
