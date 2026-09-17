"""E1/Q5 complete pitch/count validation over existing mapped world entities.

Source counter values constrain SHACL only; they never supply serving scores.
Withheld completeness does not change or disable the accepted source mapping.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import importlib.util
import json
from pathlib import Path

from rdflib import Graph, Literal, XSD

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('count_admission_support',HERE/'batting-admission.py')
B=importlib.util.module_from_spec(spec);spec.loader.exec_module(B)
CONTEXT=B.module(ROOT/'scripts/pipeline/prepare-rml-context.py','count_existing_context')
SHAPE=HERE.parent/'shacl/pitch-count-admission.ttl'


def fingerprint():
    paths=[Path(__file__),SHAPE,HERE/'batting-admission.py',HERE/'reconcile-metric-source.py',
           ROOT/'scripts/pipeline/prepare-rml-context.py',ROOT/'scripts/pipeline/validate-shacl.py']
    return B.sha('\n'.join(p.relative_to(ROOT).as_posix()+':'+B.sha(p.read_bytes()) for p in paths).encode())


def virtual_intentional_walk(play, season):
    """Recognize the accepted complete award with zero delivered pitches.

    VB entries serialize the award's ball counter; they are not four actual
    pitch or automatic-count judgment events. Other empty histories fail.
    """
    events=play.get('playEvents',[])
    return (play.get('result',{}).get('eventType')=='intent_walk'
        and len(events)==4 and [e.get('index') for e in events]==[0,1,2,3]
        and all(e.get('isPitch') is False and e.get('type')=='no_pitch'
            and e.get('details',{}).get('call',{}).get('code')=='VB'
            and e.get('details',{}).get('isBall') is True
            and e.get('details',{}).get('isStrike') is False
            and e.get('count',{}).get('balls')==i
            and e.get('count',{}).get('strikes')==0
            and e.get('count',{}).get('outs')==play.get('count',{}).get('outs')
            for i,e in enumerate(events,1))
        and bool(CONTEXT.runner_metric_evidence(play,str(play['atBatIndex']),str(season))['awardAdvances']))


def census(raw,game_pk):
    game_pk=B.identity(int(game_pk));doc=json.loads(raw);source=B.SOURCE.reconcile(raw,game_pk)
    issues=[dict(code='SOURCE_RECONCILIATION',detail=i) for i in source['blockingIssues']]
    doc[CONTEXT.CONTEXT_KEY]={'runnerHistoryReconciliation':{'sourceConsistency':'consistent' if not issues else 'inconsistent'}}
    automatic=CONTEXT.automatic_count_awards(doc)
    awards={(r['atBatIndex'],r['playId']):r for r in automatic['automaticAwards']}
    game=B.BASE+'data/game/'+game_pk;pas=[]
    identities=Counter(e.get('playId') for p in doc['liveData']['plays']['allPlays'] for e in p['playEvents'] if e.get('playId'))
    for play in doc['liveData']['plays']['allPlays']:
        pa=str(play['atBatIndex']);result_type=play['result']['eventType']
        if result_type in B.INTERRUPTIONS:continue  # No official PA; B1 separately reconciles this exclusion.
        errors=[];selected=[];strikes=0;previous_end=None
        if result_type not in B.RESULTS:errors.append('UNKNOWN_OFFICIAL_PA_RESULT')
        if [e.get('index') for e in play['playEvents']]!=list(range(len(play['playEvents']))):
            errors.append('UNRECONCILED_EVENT_MEMBERSHIP')
        if virtual_intentional_walk(play,doc['gameData']['game']['season']):
            pas.append(dict(pa=game+'/plate-appearance/'+pa,events=[],zeroPitchIntentionalWalk=True))
            continue
        for event in play['playEvents']:
            detail=event.get('details',{});pid=event.get('playId');code=detail.get('call',{}).get('code')
            after=event.get('count',{}).get('strikes')
            if type(after) is not int or not 0<=after<=3:
                errors.append('INVALID_STRIKE_COUNT');continue
            award=awards.get((pa,pid))
            if event.get('isPitch') is not True and not award:
                if after!=strikes or detail.get('isBall') is True or detail.get('isStrike') is True:
                    errors.append('UNMAPPED_NONPITCH_COUNT_EVENT')
                strikes=after
                continue
            if not isinstance(pid,str) or not CONTEXT.SAFE_IRI_SEGMENT.fullmatch(pid) or identities[pid]!=1:
                errors.append('AMBIGUOUS_COUNT_EVENT_ID');continue
            if award:
                if not award.get('clockOrderSupported', True):
                    errors.append('UNSUPPORTED_AWARD_ORDER')
                increment=award['kind']=='strike'
                selected.append(dict(event=award['processIri'],kind='award',award=award,
                                     strike=bool(increment),strikesAfter=after))
            else:
                if code in {'C','S','W','M','T','O','L'}:increment=True
                elif code=='F':increment=strikes<2
                elif code in {'B','*B','X','D','E','H'}:increment=False
                else:
                    errors.append('UNACCOUNTED_PITCH_CALL');continue
                try:
                    start=datetime.fromisoformat(event['startTime'].replace('Z','+00:00'))
                    end=datetime.fromisoformat(event['endTime'].replace('Z','+00:00'))
                    if not start.tzinfo or not end.tzinfo or start>end or (previous_end and previous_end>start):
                        raise ValueError()
                except (KeyError,ValueError,AttributeError):
                    errors.append('UNSUPPORTED_PITCH_ORDER');continue
                previous_end=end
                selected.append(dict(event=game+'/pitch/'+pid,kind='pitch',playId=pid,strike=bool(increment),
                    strikesAfter=after,start=event['startTime'],end=event['endTime'],call=code,
                    balls=event.get('count',{}).get('balls')))
            if strikes>=3 or after!=strikes+increment:errors.append('UNEXPLAINED_STRIKE_TRANSITION')
            strikes=after
        if not selected:errors.append('EMPTY_COUNT_HISTORY')
        else:
            last=selected[-1];call=last.get('call')
            terminal=(strikes==3 and result_type in {'strikeout','strikeout_double_play'}
                or result_type in {'walk','intent_walk'} and (last.get('balls')==4 or last.get('award',{}).get('ballsAfter')==4)
                or result_type=='hit_by_pitch' and call=='H'
                or result_type not in {'strikeout','strikeout_double_play','walk','intent_walk','hit_by_pitch','catcher_interf'} and call in {'X','D','E'})
            if not terminal:errors.append('UNSUPPORTED_PA_TERMINATION')
            for first,second in zip(selected,selected[1:]):
                if first['kind']==second['kind']=='award':errors.append('UNORDERED_ADJACENT_AWARDS')
        for error in sorted(set(errors)):issues.append(dict(code=error,plateAppearance=game+'/plate-appearance/'+pa))
        pas.append(dict(pa=game+'/plate-appearance/'+pa,events=selected))
    return dict(gamePk=game_pk,game=game,sourceSha256=B.sha(raw),sourceRevision=source['sourceRevision'],
                status='withheld' if issues else 'reconciled',issues=issues,plateAppearances=pas,
                withheldAutomaticAwards=automatic['withheldAutomaticAwards'])


def shape_text(source):
    shapes=[]
    def prop(path,value):return 'sh:property [ sh:path '+path+' ; sh:hasValue '+value+' ]'
    def node(target,parts):shapes.append('[] a sh:NodeShape ; sh:targetNode '+B.iri(target)+' ; '+' ;\n'.join(parts)+' .')
    for pa in source['plateAppearances']:
        pitch_ids=[e['event'] for e in pa['events'] if e['kind']=='pitch']
        def strike_iri(e):
            # The existing foul-tip individual is already a Strike Process;
            # it must not be mistaken for a second generic strike individual.
            return source['game']+'/process/'+('foul-tip' if e.get('call') in {'T','O'} else 'strike')+'/'+e['playId']
        strike_ids=[strike_iri(e) if e['kind']=='pitch' else e['event']
                    for e in pa['events'] if e['strike']]
        award_ids=[e['event'] for e in pa['events'] if e['kind']=='award']
        members=lambda values:', '.join(B.iri(v) for v in values) or '<urn:baseballo:no-count-events>'
        no_extra=B.PREFIXES+'''SELECT $this WHERE {
          { ?event a base:StrikeProcess ; obo:BFO_0000132 $this . FILTER(?event NOT IN ('''+members(strike_ids)+''')) }
          UNION { ?event obo:BFO_0000132 $this . ?record a base:BaseballEventRecord ; cco:ont00001808 ?event .
            FILTER(CONTAINS(STR(?record), "/event-record/count-award/"))
            FILTER(?event NOT IN ('''+members(award_ids)+''')) }
        }'''
        node(pa['pa'],['sh:class base:PlateAppearance',
            'sh:sparql [ sh:message "Count event membership differs from the final source" ; sh:select '+Literal(no_extra).n3()+' ]',
            'sh:property [ sh:path [ sh:inversePath obo:BFO_0000132 ] ; sh:qualifiedValueShape [ sh:class base:PitchAct ] ; sh:qualifiedMinCount '+str(len(pitch_ids))+' ; sh:qualifiedMaxCount '+str(len(pitch_ids))+' ]'])
        if pa.get('zeroPitchIntentionalWalk'):
            node(pa['pa']+'/result',['sh:class base:WalkProcess',prop('obo:BFO_0000132',B.iri(pa['pa']))])
        for e in pa['events']:
            if e['kind']=='award':
                a=e['award']
                node(a['processIri'],['sh:class base:'+a['kind'].title()+'Process',prop('obo:BFO_0000132',B.iri(pa['pa'])),
                     prop('obo:BFO_0000117',B.iri(a['judgmentIri']))])
                node(a['judgmentIri'],['sh:class base:'+a['kind'].title()+'JudgmentAct',prop('cco:ont00001986',B.iri(a['decisionIri'])),
                     prop('cco:ont00001921',B.iri(a['ruleIri']))])
                node(a['decisionIri'],['sh:class base:'+a['kind'].title()+'DecisionICE',prop('cco:ont00001808',B.iri(a['processIri']))])
                node(a['recordIri'],['sh:class base:BaseballEventRecord',*(prop('cco:ont00001808',B.iri(a[f])) for f in ('processIri','judgmentIri','decisionIri'))])
                if a.get('previousPitchIri'):node(a['previousPitchIri'],[prop('obo:BFO_0000063',B.iri(a['processIri']))])
                if a.get('nextPitchIri'):node(a['processIri'],[prop('obo:BFO_0000063',B.iri(a['nextPitchIri']))])
                continue
            pitch=e['event'];record=source['game']+'/event-record/pitch/'+e['playId']
            node(pitch,['sh:class base:PitchAct',prop('obo:BFO_0000132',B.iri(pa['pa'])),
                        prop('obo:BFO_0000199',B.iri(pitch+'/temporal-interval'))])
            node(pitch+'/temporal-interval',['sh:class obo:BFO_0000038',
                *(prop('obo:BFO_0000222' if side=='start' else 'obo:BFO_0000224',B.iri(pitch+'/temporal-instant/'+side)) for side in ('start','end'))])
            for side in ('start','end'):
                node(pitch+'/temporal-instant/'+side,['sh:class base:BaseballEventTemporalInstant'])
                node(pitch+'/timestamp/'+side,['sh:class base:BaseballTimestampICE',
                    prop('cco:ont00001916',B.iri(pitch+'/temporal-instant/'+side)),prop('cco:ont00001808',B.iri(pitch)),
                    'sh:property [ sh:path cco:ont00001767 ; sh:minCount 1 ; sh:maxCount 1 ; sh:datatype xsd:dateTime ; sh:minInclusive '+Literal(e[side],datatype=XSD.dateTime).n3()+' ; sh:maxInclusive '+Literal(e[side],datatype=XSD.dateTime).n3()+' ]'])
            count=int(e['strike'])
            node(record,['sh:class base:BaseballEventRecord',prop('cco:ont00001808',B.iri(pitch)),
                'sh:property [ sh:path cco:ont00001808 ; sh:qualifiedValueShape [ sh:class base:StrikeProcess ; '+
                prop('obo:BFO_0000132',B.iri(pa['pa']))+' ] ; sh:qualifiedMinCount '+str(count)+' ; sh:qualifiedMaxCount '+str(count)+' ]'])
            if count:
                strike=strike_iri(e)
                node(record,[prop('cco:ont00001808',B.iri(strike))])
                node(strike,['sh:class base:StrikeProcess',prop('obo:BFO_0000132',B.iri(pa['pa'])),
                    'sh:property [ sh:path obo:BFO_0000117 ; sh:qualifiedMinCount 1 ; sh:qualifiedMaxCount 1 ; sh:qualifiedValueShape [ sh:or ( [ sh:class base:StrikeJudgmentAct ] [ sh:class base:FoulTipJudgmentAct ] ) ; sh:property [ sh:path cco:ont00001986 ; sh:qualifiedMinCount 1 ; sh:qualifiedMaxCount 1 ; sh:qualifiedValueShape [ sh:or ( [ sh:class base:StrikeDecisionICE ] [ sh:class base:FoulTipCallICE ] ) ; '+prop('cco:ont00001808',B.iri(strike))+' ] ] ] ]'])
    text=SHAPE.read_text(encoding='utf-8').replace('# __COUNT_SHAPES__','\n'.join(shapes))
    Graph().parse(data=text,format='turtle')
    return text


def prove(*,raw,game_pk,rdf_path,output,java=None,classpath=None):
    source=census(raw,game_pk);implementation=fingerprint();rdf_sha=B.sha(rdf_path.read_bytes())
    output.parent.mkdir(parents=True,exist_ok=True)
    B.SOURCE.write_atomic(output.with_suffix('.source.json'),source)
    proof=dict(artifactType='baseballo-pitch-count-admission',contractVersion=1,gamePk=source['gamePk'],
        graph='https://w3id.org/baseball/graph/game/'+source['gamePk'],sourceSha256=source['sourceSha256'],
        sourceRevision=source['sourceRevision'],authoritativeRdfSha256=rdf_sha,implementationSha256=implementation,
        status='withheld',sourceReconciled=source['status']=='reconciled',graphConforms=False,issues=source['issues'],
        sourceCensusSha256=B.sha(output.with_suffix('.source.json').read_bytes()))
    proof['zeroPitchPlateAppearances']=[p['pa'] for p in source['plateAppearances'] if p.get('zeroPitchIntentionalWalk')]
    if proof['sourceReconciled']:
        shapes=output.with_suffix('.shapes.ttl');shapes.write_text(shape_text(source),encoding='utf-8',newline='\n')
        if java:
            validator=B.module(ROOT/'scripts/pipeline/validate-shacl.py','count_shacl')
            conforms,report,_=validator.validate_with_jena(data_path=rdf_path.resolve(),shape_path=shapes.resolve(),
                java=java,classpath=classpath,max_heap='512m')
        else:
            from pyshacl import validate
            conforms,report,_=validate(Graph().parse(rdf_path),shacl_graph=Graph().parse(shapes),advanced=True)
        report_path=output.with_suffix('.report.ttl');report.serialize(destination=report_path,format='turtle')
        proof.update(graphConforms=bool(conforms),shapeSha256=B.sha(shapes.read_bytes()),reportSha256=B.sha(report_path.read_bytes()),
                     engine='jena' if java else 'pyshacl')
        if conforms:proof['status']='admitted'
        else:proof['issues'].append(dict(code='PITCH_COUNT_MAPPING_COVERAGE'))
    if fingerprint()!=implementation or B.sha(rdf_path.read_bytes())!=rdf_sha:raise ValueError('Pitch-count proof inputs changed')
    B.SOURCE.write_atomic(output,proof)
    return proof


def promoted_admission(state_root, promotion):
    withheld=dict(status='withheld',issues=[dict(code='PITCH_COUNT_PROOF_MISSING_OR_STALE')])
    marker_path=Path(promotion['promotionManifest'])
    if B.sha(marker_path.read_bytes())!=promotion['promotionManifestSha256']:
        raise ValueError('Promotion marker changed while loading pitch-count admission')
    marker=json.loads(marker_path.read_text(encoding='utf-8-sig'))
    path=Path(marker.get('pitchCountAdmission',''))
    if not path.is_file():return withheld
    if not path.resolve().is_relative_to((state_root/'pipeline/evidence/mlb-game'/promotion['gamePk']).resolve()):
        raise ValueError('Pitch-count proof escaped its owning game evidence directory')
    if B.sha(path.read_bytes())!=marker.get('pitchCountAdmissionSha256'):
        raise ValueError('Pitch-count proof hash differs from promotion')
    proof=json.loads(path.read_text(encoding='utf-8'))
    if (proof.get('artifactType')!='baseballo-pitch-count-admission' or proof.get('contractVersion')!=1
            or proof.get('gamePk')!=promotion['gamePk'] or proof.get('implementationSha256')!=fingerprint()
            or proof.get('sourceSha256')!=promotion['rawSha256']
            or proof.get('authoritativeRdfSha256')!=promotion['authoritativeRdfSha256']
            or proof.get('graph')!=promotion['authoritativeGraph']):return withheld
    if proof.get('status')=='admitted' and any(not proof.get(key) for key in
            ('sourceCensusSha256','shapeSha256','reportSha256')):
        raise ValueError('Admitted pitch-count proof lacks retained validation artifact hashes')
    for suffix,key in (('.source.json','sourceCensusSha256'),('.shapes.ttl','shapeSha256'),('.report.ttl','reportSha256')):
        if key in proof and B.sha(path.with_suffix(suffix).read_bytes())!=proof[key]:
            raise ValueError('Pitch-count validation artifact changed: '+key)
    return {**proof,'proofSha256':B.sha(path.read_bytes())}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('input','rdf','output'):parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--game-pk',required=True);parser.add_argument('--java',type=Path);parser.add_argument('--jena-classpath',type=Path)
    args=parser.parse_args()
    if args.java and not args.jena_classpath:parser.error('--java requires --jena-classpath')
    outputs={args.output.resolve(),*(args.output.with_suffix(s).resolve() for s in ('.source.json','.shapes.ttl','.report.ttl'))}
    if outputs & {args.input.resolve(),args.rdf.resolve()}:raise ValueError('Proof cannot overwrite source or RDF')
    raw=args.input.read_bytes()
    result=prove(raw=raw,game_pk=args.game_pk,rdf_path=args.rdf,output=args.output,java=args.java,classpath=args.jena_classpath)
    if raw!=args.input.read_bytes():raise ValueError('Source changed during pitch-count admission')
    print(json.dumps(result))
