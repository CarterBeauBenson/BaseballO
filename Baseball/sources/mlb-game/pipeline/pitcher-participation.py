"""P1 source selection and SHACL; physical pitching is separate from PA credit."""
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SHAPE=HERE.parent/'shacl/pitcher-participation.ttl'
spec=importlib.util.spec_from_file_location('actual_pitcher_context',ROOT/'scripts/pipeline/prepare-rml-context.py')
CONTEXT=importlib.util.module_from_spec(spec);spec.loader.exec_module(CONTEXT)
BASE='https://baseballontology.org/data/'


def census(raw,game_pk):
    document=json.loads(raw)
    if str(document.get('gamePk'))!=game_pk:raise ValueError('P1 source game differs')
    rows=[];issues=[]
    for play in document['liveData']['plays']['allPlays']:
        selected=CONTEXT.pitcher_participation_context(document,play)
        pa=str(play['atBatIndex'])
        issues.extend(dict(atBatIndex=pa,**item) for item in selected['issues'])
        rows.extend(dict(atBatIndex=pa,playId=pid,playerId=player) for pid,player in selected['pitches'].items())
    return dict(gamePk=game_pk,sourceSha256=hashlib.sha256(raw).hexdigest(),pitches=rows,issues=issues)


def shapes(game_pk,selected):
    parts=[];template=SHAPE.read_text(encoding='utf-8');game=BASE+'game/'+game_pk
    for row in selected['pitches']:
        values=dict(PITCH=game+'/pitch/'+row['playId'],PA=game+'/plate-appearance/'+row['atBatIndex'],
            PLAYER=BASE+'player/'+row['playerId'])
        text=template
        for key,value in values.items():text=text.replace('__'+key+'__',value)
        parts.append(text)
    if selected.get('issues'):
        parts.append('<'+game+'/unresolved-pitcher-shape> a <http://www.w3.org/ns/shacl#NodeShape> ; '
            '<http://www.w3.org/ns/shacl#targetNode> <'+game+'> ; <http://www.w3.org/ns/shacl#in> () .')
    return '\n'.join(parts)


def validate(raw,game_pk,rdf,output,session,java,classpath):
    source=census(raw,game_pk)
    (output/'pitcher-participation.source.json').write_text(json.dumps(source,indent=2)+'\n',encoding='utf-8')
    path=output/'pitcher-participation.shapes.ttl';path.write_text(shapes(game_pk,source),encoding='utf-8')
    conforms,report,_=session.validate_with_jena(data_path=rdf,shape_path=path,
        java=java,classpath=classpath,max_heap='384m')
    report.serialize(destination=output/'pitcher-participation.report.ttl',format='turtle')
    if not conforms:raise ValueError('P1 actual-pitcher source/graph conformance failed')
