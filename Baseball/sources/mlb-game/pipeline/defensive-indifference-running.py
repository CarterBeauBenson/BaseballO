"""D2 selection and SHACL for ordinary ingestion and targeted EG1 additions."""
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
CONTEXT_PATH=ROOT/'scripts/pipeline/prepare-rml-context.py'
spec=importlib.util.spec_from_file_location('d2_context',CONTEXT_PATH)
C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)
SHAPE=HERE.parent/'shacl/defensive-indifference-running.ttl'
MAPS=('DefensiveIndifferenceAttemptOverlayMap',)


def select(raw,game_pk):
    document=json.loads(raw)
    if str(document.get('gamePk'))!=game_pk:raise ValueError('D2 source game differs')
    return [row for play in document['liveData']['plays']['allPlays']
        for row in C.defensive_indifference_evidence(play)]


def shapes(game_pk,rows):
    pattern=SHAPE.read_text(encoding='utf-8')
    return '\n'.join([pattern.split('# D2')[0],*(pattern.replace('__ACT__',
        'https://baseballontology.org/data/game/'+game_pk+'/runner-act/movement/'+
        row['atBatIndex']+'/'+row['runnerIndex']) for row in rows)])


def validate(raw,game_pk,rdf,output,session,java,classpath):
    rows=select(raw,game_pk);shape=output/'defensive-indifference-running.shapes.ttl'
    shape.write_text(shapes(game_pk,rows),encoding='utf-8',newline='\n')
    conforms,report,_=session.validate_with_jena(data_path=rdf,shape_path=shape,
        java=java,classpath=classpath,max_heap='384m')
    report.serialize(destination=output/'defensive-indifference-running.report.ttl',format='turtle')
    receipt=dict(selected=rows,conforms=conforms,sourceSha256=hashlib.sha256(raw).hexdigest(),
        authoritativeRdfSha256=hashlib.sha256(rdf.read_bytes()).hexdigest(),
        shapeSha256=hashlib.sha256(shape.read_bytes()).hexdigest())
    (output/'defensive-indifference-running.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    if not conforms:raise ValueError('D2 defensive-indifference running SHACL failed')
