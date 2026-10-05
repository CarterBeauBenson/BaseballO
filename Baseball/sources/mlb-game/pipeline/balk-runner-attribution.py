"""BK1 source selection and SHACL, shared by ordinary ingestion and additions."""
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
CONTEXT_PATH=ROOT/'scripts/pipeline/prepare-rml-context.py'
spec=importlib.util.spec_from_file_location('bk1_context',CONTEXT_PATH)
C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)
SHAPE=HERE.parent/'shacl/balk-runner-attribution.ttl'
MAPS=('BalkAdvanceProcessMap','BalkAdvanceJudgmentMap','BalkAdvanceDecisionMap','BalkAdvanceRecordMap','BalkRuleMap')


def select(raw,game_pk):
    document=json.loads(raw)
    if str(document.get('gamePk'))!=game_pk:raise ValueError('BK1 source game differs')
    return [row for play in document['liveData']['plays']['allPlays']
        for row in C.balk_runner_evidence(play,str(play['atBatIndex']))]


def shapes(game_pk,rows):
    game='https://baseballontology.org/data/game/'+game_pk
    parts=['@prefix sh: <http://www.w3.org/ns/shacl#> .']
    for row in rows:
        suffix=row['atBatIndex']+'/'+row['runnerIndex'];action=row['actionId']
        values=dict(RECORD=game+'/runner-record/'+suffix,PROCESS=game+'/process/balk/'+action,
            JUDGMENT=game+'/judgment/balk/'+action,DECISION=game+'/decision/balk/'+action,
            ACT=game+'/runner-act/movement/'+suffix,PA=game+'/plate-appearance/'+row['atBatIndex'],
            RESOLUTION=game+'/runner-resolution/'+row['resolutionKind']+'/'+suffix,
            RESOLUTION_CLASS='RunProcess' if row['resolutionKind']=='score' else 'SafeProcess',
            PLAYER='https://baseballontology.org/data/player/'+row['runnerId'])
        text=SHAPE.read_text(encoding='utf-8')
        for key,value in values.items():text=text.replace('__'+key+'__',value)
        parts.append(text)
    return '\n'.join(parts)


def validate(raw,game_pk,rdf,output,session,java,classpath):
    rows=select(raw,game_pk);shape=output/'balk-runner-attribution.shapes.ttl'
    shape.write_text(shapes(game_pk,rows),encoding='utf-8',newline='\n')
    conforms,report,_=session.validate_with_jena(data_path=rdf,shape_path=shape,
        java=java,classpath=classpath,max_heap='384m')
    report.serialize(destination=output/'balk-runner-attribution.report.ttl',format='turtle')
    receipt=dict(selected=rows,conforms=conforms,sourceSha256=hashlib.sha256(raw).hexdigest(),
        authoritativeRdfSha256=hashlib.sha256(rdf.read_bytes()).hexdigest(),
        shapeSha256=hashlib.sha256(shape.read_bytes()).hexdigest())
    (output/'balk-runner-attribution.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    if not conforms:raise ValueError('BK1 balk runner attribution SHACL failed')
