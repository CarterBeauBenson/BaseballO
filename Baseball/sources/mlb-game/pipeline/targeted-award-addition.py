"""NiFi's W1/W2/W3 repairs: existing award/dependency maps, additive promotion."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import urllib.request
import uuid
from rdflib import Graph, Literal, Namespace, RDF, URIRef
from rdflib.compare import isomorphic

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
DECISION='archive/design-records/mlb-game-zero-pitch-walk-prefix/review.json'
DEPENDENCY_DECISION='archive/design-records/mlb-game-w1-award-dependencies/review.json'
FINAL_AWARD_DECISION='archive/design-records/mlb-game-final-award-selection/review.json'
FINAL_AWARD_CASES=ROOT/'archive/design-records/mlb-game-final-award-selection/evidence.json'
RECOVERY=HERE/'award-input-recovery.json'
SHAPE=HERE.parent/'shacl/intentional-walk-award-addition.ttl'
MAPS=('AwardCauseMap','AwardRequirementMap','AwardRequiredByMap','AwardEvidenceRecordMap',
      'AwardRuleEditionMap','AwardRuleIdentifierMap','AwardRuleEditionIdentifierMap')
DEPENDENCY_MAPS=('RunnerEpisodeMap','RunnerEpisodeAgentMap','RunnerEpisodeRecordMap','SafeDecisionDestinationMap')

def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value

A=module(HERE/'targeted-history-addition.py','award_addition_mechanics')
C=module(HERE/'pitch-count-admission.py','award_count_contract')
TX,I,J,EVENT=A.TX,A.I,A.J,A.EVENT
sha,read,atomic=A.sha,A.read,A.atomic

def selected_dependencies(play,pa,awards):
    """Reuse the accepted selector only at the selected W1 row identities."""
    identity=lambda row:tuple(row[key] for key in ('atBatIndex','runnerIndex','runnerId','resolutionKind'))
    wanted={identity(row) for row in awards}
    existing=C.CONTEXT.runner_episode_evidence(play,pa)
    selected={key:[row for row in rows if identity(row) in wanted] for key,rows in existing.items()}
    if {identity(row) for row in selected['runnerEpisodes']}!=wanted:
        raise ValueError('W2 dependencies do not match the selected W1 runner resolutions')
    return selected

def select(raw,game_pk):
    if not game_pk.isdecimal():raise ValueError('Invalid W1 game identity')
    doc=json.loads(raw)
    if str(doc.get('gamePk'))!=game_pk:raise ValueError('W1 source game differs')
    source=C.B.SOURCE.reconcile(raw,game_pk)
    if source['blockingIssues']:raise ValueError('W1 source census is not reconciled')
    doc[C.CONTEXT.CONTEXT_KEY]={'runnerHistoryReconciliation':C.CONTEXT.personal_runner_histories(raw)}
    named={str(c['atBatIndex']):c for c in read(FINAL_AWARD_CASES)['cases']
        if c['gamePk']==game_pk and c['sourceWitness']['sha256']==hashlib.sha256(raw).hexdigest()}
    selected=[]
    for play in doc['liveData']['plays']['allPlays']:
        pa=str(play['atBatIndex']);case=named.get(pa)
        if not case and (len(play.get('playEvents',[]))<=4
                or not C.virtual_intentional_walk(play,doc['gameData']['game']['season'],doc)):continue
        rows=C.CONTEXT.runner_metric_evidence(play,pa,
            str(doc['gameData']['game']['season']),document=doc)['awardAdvances']
        if case and ([(r['runnerIndex'],r['runnerId']) for r in rows]
                !=[(str(case['runnerIndex']),str(case['runnerId']))]
                or play['result']['eventType']!=case['result']
                or play['playEvents'][-1]['index']!=case['terminalEventIndex']):
            raise ValueError('W3 selection differs from its named final award')
        item=dict(atBatIndex=pa,
            terminalEventIndex=play['playEvents'][-1]['index'],awardAdvances=rows,
            **selected_dependencies(play,pa,rows))
        if case:item.update(selectionDecision=FINAL_AWARD_DECISION,
            resultClass=C.B.RESULTS[case['result']])
        selected.append(item)
    return selected

def execution_inputs(raw,game_pk,selected,context,mapping):
    venue=str(json.loads(raw)['gameData']['venue']['id'])
    if not venue.isdecimal():raise ValueError('W2 source venue identity is invalid')
    atomic(context,dict(gamePk=int(game_pk),gameData=dict(venue=dict(id=int(venue))),
        liveData=dict(plays=dict(allPlays=[{C.CONTEXT.CONTEXT_KEY:{key:p[key] for key in
            ('awardAdvances','runnerEpisodes','safeDecisionDestinations')}} for p in selected]))))
    A.subset_mapping(game_pk,mapping,MAPS+DEPENDENCY_MAPS)
    # As with the existing gamePk substitution, resolve the unchanged root
    # reference from this exact source before running the sliced JSONPath maps.
    mapping.write_text(mapping.read_text(encoding='utf-8').replace('{$.gameData.venue.id}',venue),
                       encoding='utf-8',newline='\n')

def shapes(game_pk,selected):
    base=C.B.BASE+'data/game/'+game_pk;text=[];counts=[]
    for item in selected:
        pa=base+'/plate-appearance/'+item['atBatIndex']
        if item.get('selectionDecision')!=FINAL_AWARD_DECISION:
            counts.append(dict(pa=pa,events=[],zeroPitchIntentionalWalk=True))
        for row in item['awardAdvances']:
            suffix=item['atBatIndex']+'/'+row['runnerIndex']
            values=dict(RESULT=pa+'/result',RESULT_CLASS=item.get('resultClass','WalkProcess'),PA=pa,ACT=base+'/runner-act/movement/'+suffix,
                PLAYER=C.B.BASE+'data/player/'+row['runnerId'],RULE=row['ruleIri'],EDITION=row['ruleEditionIri'],
                RECORD=base+'/runner-record/'+suffix,RULE_IDENTIFIER=row['ruleIdentifierIri'],
                EDITION_IDENTIFIER=row['ruleEditionIdentifierIri'],RULE_CODE=Literal(row['ruleCode']).n3(),
                EDITION_LABEL=Literal(row['ruleEditionIdentifier']).n3())
            part=SHAPE.read_text(encoding='utf-8')
            for key,value in values.items():part=part.replace('__'+key+'__',value)
            text.append(part)
    text.append(C.shape_text(dict(game=base,plateAppearances=counts)))
    return '\n'.join(text)

def authoritative_scope(data,focus):
    """Retarget unchanged source constraints to the addition's exact nodes.

    Constraints still query the full base-plus-delta graph and require all
    dependent facts. Unrelated old conformance debt is not declared repaired.
    """
    shapes=Graph().parse(HERE.parent/'shacl/authoritative.ttl');sh=Namespace('http://www.w3.org/ns/shacl#')
    for predicate in (sh.targetClass,sh.targetSubjectsOf,sh.targetObjectsOf,sh.targetNode):
        for shape,_,value in list(shapes.triples((None,predicate,None))):
            if predicate==sh.targetClass:targets=set(data.subjects(RDF.type,value))
            elif predicate==sh.targetSubjectsOf:targets=set(data.subjects(value,None))
            elif predicate==sh.targetObjectsOf:targets=set(data.objects(None,value))
            else:targets={value}
            shapes.remove((shape,predicate,value))
            for target in targets & focus:shapes.add((shape,sh.targetNode,target))
    return shapes


def revalidate(marker,manifest,rdf,evidence,java,classpath,selected,game_pk,delta,
               *, shape_text=shapes, decisions=None, project_census=None):
    """Preserve original source outcomes; check affected facts before promotion."""
    decisions=decisions or dict(decision=DECISION,dependencyDecision=DEPENDENCY_DECISION,selectionDecision=FINAL_AWARD_DECISION)
    fields={};shape=evidence/'addition.shapes.ttl';shape.write_text(shape_text(game_pk,selected),encoding='utf-8',newline='\n')
    with J.Session(rdf,java,classpath,max_heap='384m') as session:
        def check(path,report):
            conforms,graph,_=session.validate_with_jena(data_path=rdf,shape_path=path,
                java=java,classpath=classpath,max_heap='384m')
            graph.serialize(destination=report,format='turtle');return conforms
        if not check(shape,evidence/'addition.report.ttl'):raise ValueError('Selected addition or existing referent failed SHACL')
        scoped=evidence/'authoritative-scoped.shapes.ttl'
        authoritative_scope(Graph().parse(rdf),set(delta.subjects())|set(delta.objects())).serialize(destination=scoped,format='turtle')
        if not check(scoped,evidence/'authoritative.report.ttl'):
            raise ValueError('W1 affected facts failed unchanged authoritative SHACL')
        for field,value in marker.items():
            if not field.endswith('Admission'):continue
            prior=Path(value)
            if sha(prior)!=marker[field+'Sha256']:raise ValueError('W1 retained admission changed')
            proof=read(prior)
            A.retain_source_binding(proof,marker,field)
            if proof.get('authoritativeRdfSha256')!=manifest['outputSha256']:
                raise ValueError('W1 retained proof belongs to another graph')
            target=evidence/prior.name
            for suffix,key in (('.source.json','sourceCensusSha256'),('.shapes.ttl','shapeSha256'),('.report.ttl','reportSha256')):
                if key in proof:
                    source=prior.with_suffix(suffix)
                    if sha(source)!=proof[key]:raise ValueError('W1 retained validation artifact changed')
                    target.with_suffix(suffix).write_bytes(source.read_bytes())
            projection=None
            if project_census is not None and 'sourceCensusSha256' in proof:
                projection=project_census(field,read(target.with_suffix('.source.json')),selected)
                if projection is not None:
                    # An accepted addition changes an exact selected census.
                    # Preserve its original source/producer/outcome and name
                    # the additional witness; SHACL checks the new exact set.
                    source,shape_text_updated,provenance=projection
                    provenance=dict(provenance,originalSourceCensusSha256=proof['sourceCensusSha256'],
                        originalShapeSha256=proof.get('shapeSha256'))
                    counts={}
                    if field=='runnerHistoryAdmission':
                        counts['selectedHistories']=len(source['history']['histories'])
                    elif field=='contactContinuationAdmission':
                        counts={key:sum(p['status']==status for p in source['plays'])
                            for key,status in (('admittedPlays','admitted'),('withheldPlays','withheld'))}
                    provenance['originalCounts']={key:proof.get(key) for key in counts}
                    proof.update(counts)
                    source['targetedSourceProjection']=provenance
                    atomic(target.with_suffix('.source.json'),source)
                    target.with_suffix('.shapes.ttl').write_text(shape_text_updated,encoding='utf-8',newline='\n')
                    proof.update(sourceCensusSha256=sha(target.with_suffix('.source.json')),
                        shapeSha256=sha(target.with_suffix('.shapes.ttl')),
                        targetedSourceProjection=provenance)
            if 'shapeSha256' in proof:
                conforms=check(target.with_suffix('.shapes.ttl'),target.with_suffix('.report.ttl'))
                if proof.get('graphConforms',proof.get('conforms')) is True and not conforms:
                    raise ValueError('W1 invalidated previously conforming '+field)
                proof['reportSha256']=sha(target.with_suffix('.report.ttl'))
                proof['graphConforms']=conforms
            proof.update(authoritativeRdfSha256=sha(rdf),graphRevalidation=dict(**decisions,
                originalProofSha256=sha(prior),mode='selected-additive-census' if projection is not None else 'unchanged-source-census',checkedAtUtc=TX.now()))
            # A retained withheld status remains withheld, even if its graph now passes.
            atomic(target,proof);fields[field]=str(target);fields[field+'Sha256']=sha(target)
    return fields

def base_manifest(marker,promotion,prior):
    """Keep failed staging separate from the validated promoted graph identity.

    Older promotions predate immutable manifest retention. The ordinary
    inventory validates that case from its exact promoted index and recorded
    source-RDF hash. Keep the unavailable original manifest explicit.
    """
    if sha(prior)==marker['rmlManifestSha256']:return read(prior)
    if promotion['rmlManifestAdmissionMode']!='pending-staging-over-current-promotion':
        raise ValueError('W1 base mapping manifest changed')
    return dict(gamePk=marker['gamePk'],graphIri=promotion['authoritativeGraph'],
        inputSha256=promotion['rawSha256'],outputSha256=promotion['authoritativeRdfSha256'],
        mappingBaseIri='https://baseballontology.org/mapping/mlb-direct',
        baseMappingManifestAvailability='unavailable-prior-staging-reuse',
        basePromotionManifest=promotion['promotionManifest'],
        basePromotionManifestSha256=promotion['promotionManifestSha256'])


def apply_delta(store,graph,missing,removed):
    """Default additions stay POSTs; an explicitly scoped correction is atomic."""
    if len(removed):
        named=URIRef(graph).n3()
        old=removed.serialize(format='nt');new=missing.serialize(format='nt')
        update=f'WITH {named} DELETE {{ {old} }} INSERT {{ {new} }} WHERE {{ {old} }}'
        request=urllib.request.Request('http://127.0.0.1:3031/baseball-dev/update',data=update.encode(),
            method='POST',headers={'Content-Type':'application/sparql-update'})
    else:
        request=urllib.request.Request(store._url(graph),data=missing.serialize(format='nt',encoding='utf-8'),
            method='POST',headers={'Content-Type':'application/n-triples'})
    with urllib.request.urlopen(request,timeout=120) as response:
        if response.status not in (200,201,204):raise RuntimeError('Targeted graph mutation failed')


def add_game(state,game_pk,witness,java,mapper,classpath,*,repair=None):
    """Share the existing additive transaction; selection stays source-specific."""
    repair=repair or dict(decisions=dict(decision=DECISION,dependencyDecision=DEPENDENCY_DECISION,selectionDecision=FINAL_AWARD_DECISION),
        select=select,execution_inputs=execution_inputs,revalidate=revalidate,
        validation_scope='selected-approved-awards-and-retained-admissions')
    decisions=repair['decisions']
    for decision in decisions.values():
        if read(ROOT/decision)['status']!='accepted':raise ValueError('Targeted addition is not accepted: '+decision)
    source_path=Path(witness['path']);raw=source_path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=witness['sha256']:raise ValueError('W1 retained source changed')
    selected=repair['select'](raw,game_pk)
    if not selected:return dict(status='not-applicable',rdfChanged=False)
    store=TX.HttpGraphStore('http://127.0.0.1:3031/baseball-dev/data');TX.recover(store,state,game_pk)
    marker_root=state/'pipeline/evidence/nifi/game-promotion'/game_pk
    marker_path=max(marker_root.glob('*.json'),key=lambda p:(read(p)['promotedAtUtc'],p.name));marker=read(marker_path)
    selection_sha=hashlib.sha256(json.dumps(selected,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    promotion=I.validated_promotion_record(state,marker_path,game_pk,I.query_index_contract_admission())
    I.retain_game_artifacts(state,game_pk)
    prior=I.retained_artifact(state,game_pk,marker['rmlManifestSha256'],Path(marker['rmlManifest']))
    manifest=base_manifest(marker,promotion,prior)
    run=uuid.uuid4().hex;evidence=state/'pipeline/evidence/mlb-game'/game_pk/run;evidence.mkdir(parents=True)
    context=evidence/'game-context.json'
    mapping=evidence/'addition.rml.ttl';repair['execution_inputs'](raw,game_pk,selected,context,mapping)
    delta_path=evidence/'addition.ttl'
    A.command([java,'-Xmx256m','-jar',mapper,'-m',mapping,'-o',delta_path,'-s','turtle',
        '-b',manifest['mappingBaseIri'],'--strict'],evidence,evidence/'rml.log')
    delta=Graph().parse(delta_path)
    if not len(delta):raise ValueError('Selected RML addition produced no triples')
    base_bytes=store.get(marker['authoritativeGraph'])
    if base_bytes is None:raise ValueError('W1 base graph is missing')
    base=TX.nt_graph(base_bytes)
    if len(base)!=marker['authoritativeTripleCount']:raise ValueError('W1 base graph changed')
    prior_rdf=Path(manifest.get('outputPath',''))
    if prior_rdf.is_file() and sha(prior_rdf)==manifest['outputSha256'] and not isomorphic(base,Graph().parse(prior_rdf)):
        raise ValueError('W1 live graph differs from retained promoted RDF')
    removed=repair['removals'](base,delta,game_pk,selected) if 'removals' in repair else Graph()
    missing=delta-base
    if not len(missing) and not len(removed):
        # A matching source selection is not a receipt for the current mapping.
        # Confirm its actual triples against the current promoted graph before
        # resuming event delivery, without another graph write or transaction.
        EVENT.emit(state,marker_path)
        if (all(marker.get('targetedAddition',{}).get(key)==value for key,value in decisions.items())
                and marker.get('targetedAddition',{}).get('selectionSha256')==selection_sha
                and marker['targetedAddition'].get('sourceWitness')==witness):
            return dict(status='already-complete',promotionEvidence=str(marker_path),**marker['targetedAddition'])
        return dict(status='already-present',rdfChanged=False,selected=selected)
    combined=(base-removed)+delta;rdf=evidence/'authoritative-with-addition.nt';combined.serialize(destination=rdf,format='nt')
    fields=repair['revalidate'](marker,manifest,rdf,evidence,java,classpath,selected,game_pk,missing)
    inventory=dict(gamePk=game_pk,sourceWitness=witness,basePromotionSha256=sha(marker_path),
        selected=selected,missingTriples=sorted([list(map(lambda term:term.n3(),t)) for t in missing]),
        removedTriples=sorted([list(map(lambda term:term.n3(),t)) for t in removed]))
    atomic(evidence/'addition-inventory.json',inventory)
    addition=dict(**decisions,selectionSha256=selection_sha,
        basePromotionSha256=sha(marker_path),baseRmlManifestSha256=marker['rmlManifestSha256'],
        baseRdfSha256=promotion['authoritativeRdfSha256'],baseExportSha256=TX.sha_bytes(base_bytes),
        sourceWitness=witness,inventorySha256=sha(evidence/'addition-inventory.json'),
        deltaPath=str(delta_path),deltaSha256=sha(delta_path),effectiveMappingSha256=sha(mapping),
        executionContextSha256=sha(context),contextBuilderSha256=sha(ROOT/'scripts/pipeline/prepare-rml-context.py'),
        addedTriples=len(missing),removedTriples=len(removed),baseTripleCount=len(base),resultingTripleCount=len(combined),
        mutation='targeted-sparql-delete-insert' if len(removed) else 'additive-graph-store-post',
        acquiredInputs=int(witness.get('kind')=='targeted-reacquisition'))
    if sha(source_path)!=witness['sha256']:raise ValueError('W1 source changed before promotion')
    latest=max(marker_root.glob('*.json'),key=lambda p:(read(p)['promotedAtUtc'],p.name))
    if latest!=marker_path or sha(marker_path)!=addition['basePromotionSha256']:raise ValueError('W1 promotion changed')
    promoted=marker_root/(run+'.json');TX.prepare(store,state,game_pk,run)
    try:
        apply_delta(store,marker['authoritativeGraph'],missing,removed)
        observed=TX.nt_graph(store.get(marker['authoritativeGraph']))
        if not isomorphic(observed,combined):
            difference=dict(expectedCount=len(combined),observedCount=len(observed),
                missingCount=len(combined-observed),unexpectedCount=len(observed-combined),
                missingSample=[list(map(lambda term:term.n3(),t)) for t in list(combined-observed)[:5]],
                unexpectedSample=[list(map(lambda term:term.n3(),t)) for t in list(observed-combined)[:5]])
            atomic(evidence/'mutation-difference.json',difference)
            raise ValueError('Targeted mutation differs from the exact validated result: '+str(evidence/'mutation-difference.json'))
        A.command(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',ROOT/'scripts/pipeline/build-query-index.ps1',
            '-GamePk',game_pk,'-SourceRdfFile',rdf,'-SourceRdfSha256',sha(rdf)],ROOT,evidence/'query-index.log')
        updated=dict(manifest,artifactType='baseballo-rml-targeted-addition-manifest',
            mappingExecution='retained-base-with-scoped-correction' if len(removed) else 'retained-base-plus-targeted-delta',
            targetedAddition=addition,outputPath=str(rdf),outputSha256=sha(rdf),
            serialization='ntriples',shaclStatus='validated',shaclValidatedAtUtc=TX.now(),completedAtUtc=TX.now())
        updated['shaclValidationScope']=repair['validation_scope']
        if sha(prior)==marker['rmlManifestSha256']:updated['baseRmlManifest']=str(prior)
        atomic(Path(marker['rmlManifest']),updated);index=read(Path(marker['queryIndexManifest']));I.retain_game_artifacts(state,game_pk)
        next_marker=dict(marker,pipelineRunId=run,transactionRunId=run,promotedAtUtc=TX.now(),authoritativeTripleCount=len(combined),
            queryIndexTripleCount=index['indexTripleCount'],rmlManifestSha256=sha(Path(marker['rmlManifest'])),
            queryIndexManifestSha256=sha(Path(marker['queryIndexManifest'])),targetedAddition=addition,**fields)
        candidate=evidence/'promotion.json';atomic(candidate,next_marker)
        I.validated_promotion_record(state,candidate,game_pk,I.query_index_contract_admission())
        atomic(promoted,next_marker);TX.commit(state,game_pk,run)
    except BaseException:
        if not promoted.is_file():TX.restore(store,state,game_pk,run,'targeted-award-addition-failed')
        raise
    EVENT.emit(state,promoted)
    return dict(status='complete',promotionEvidence=str(promoted),**addition)

def finished_attempt(previous,version,source_sha):
    return (previous.get('implementationSha256')==version and previous.get('sourceSha256')==source_sha
        and (previous.get('status') in {'complete','already-complete','already-present','not-applicable'}
             or previous.get('attempts',0)>=2))


def recovery_witness(state):
    """NiFi resumes only the named input-retirement failures, never a corpus."""
    request=read(RECOVERY);request_sha=sha(RECOVERY);version=fingerprint()
    for case in request['cases']:
        if not A.SCOPE.active(state,case['gamePk']):continue
        pk=case['gamePk'];control=state/'pipeline/control/mlb-game/award-addition'/(pk+'.json')
        previous=read(control) if control.is_file() else {}
        if previous.get('additionComplete'):
            retire_recovery_input(state,previous)
            if previous.get('status')=='failed':
                previous.update(status='complete');previous.pop('error',None);atomic(control,previous)
            continue
        if previous.get('status')!='failed':continue
        if (previous.get('sourceWitness',{}).get('recoveryRequestSha256')==request_sha
                and previous.get('status') in {'complete','already-complete','already-present','not-applicable'}):continue
        if finished_attempt(previous,version,previous.get('sourceSha256')):continue
        # The existing owner's receipt identifies the retired input and
        # successful promotion. Reacquisition keeps a distinct response hash.
        cleanup=read(state/'pipeline/evidence/mlb-game'/pk/case['retiringPromotionRunId']/'cleanup.json')
        if (cleanup.get('rawRetiredAfterPromotion') is not True
                or cleanup.get('sourceWitness',{}).get('sha256')!=case['retiredSourceSha256']):
            raise ValueError('Award recovery does not match the recorded retired input')
        directory=state/'pipeline/quarantine/mlb-game'/pk/'targeted-award'
        source=directory/'input.json';manifest=directory/'acquisition.json'
        if manifest.is_file():
            witness=read(manifest)
            if witness.get('recoveryRequestSha256')!=request_sha or sha(source)!=witness['sha256']:
                raise ValueError('Award recovery input changed')
            return witness
        url=f'https://statsapi.mlb.com/api/v1.1/game/{pk}/feed/live'
        if source.is_file():raw=source.read_bytes()  # interrupted manifest write
        else:
            with urllib.request.urlopen(urllib.request.Request(url,headers={'Accept':'application/json'}),timeout=60) as response:
                raw=response.read()
        if str(json.loads(raw).get('gamePk'))!=pk:raise ValueError('Award recovery game identity differs')
        directory.mkdir(parents=True,exist_ok=True)
        if not source.is_file():
            pending=source.with_suffix('.pending');pending.write_bytes(raw);pending.replace(source)
        witness=dict(gamePk=pk,path=str(source),sha256=hashlib.sha256(raw).hexdigest(),
            kind='targeted-reacquisition',scopeDecision=request['scopeDecision'],url=url,
            recoveryRequestSha256=request_sha,retiredSourceSha256=case['retiredSourceSha256'],acquiredAtUtc=TX.now())
        atomic(manifest,witness);return witness
    return None


def retire_recovery_input(state,result):
    witness=result.get('sourceWitness',{})
    if not witness.get('recoveryRequestSha256') or not result.get('promotionEvidence'):return
    source=Path(witness['path']);owned=state/'pipeline/quarantine/mlb-game'/result['gamePk']/'targeted-award/input.json'
    if source.resolve()!=owned.resolve():raise ValueError('Award retirement escapes its owned input')
    promoted=Path(result['promotionEvidence']);marker=read(promoted)
    if (str(marker.get('gamePk'))!=result['gamePk']
            or marker.get('targetedAddition',{}).get('sourceWitness')!=witness):
        raise ValueError('Award retirement does not match its successful promotion')
    path=source.with_name('retirement.json')
    identity=dict(sourceSha256=witness['sha256'],promotionEvidence=str(promoted),promotionManifestSha256=sha(promoted))
    if path.is_file():
        receipt=read(path)
        if any(receipt.get(k)!=v for k,v in identity.items()):raise ValueError('Award retirement receipt changed')
        if receipt.get('rawRetiredAfterPromotion') is True and not source.exists():return
    elif not source.is_file():raise ValueError('Award recovery input vanished before retirement')
    atomic(path,dict(identity,rawRetiredAfterPromotion=False))
    if source.is_file():
        if sha(source)!=witness['sha256']:raise ValueError('Award retirement input changed')
        source.unlink()
    atomic(path,dict(identity,rawRetiredAfterPromotion=True,retiredAtUtc=TX.now()))


def tick(state,game_pk,witness,java,mapper,classpath):
    if not A.SCOPE.active(state,game_pk):return dict(gamePk=game_pk,status='outside-active-scope')
    control=state/'pipeline/control/mlb-game/award-addition'/(game_pk+'.json')
    version=fingerprint()
    previous=read(control) if control.is_file() else {}
    owned=state/'pipeline/quarantine/mlb-game'/game_pk/'targeted-award/input.json'
    if Path(witness['path']).resolve()==owned.resolve():
        acquired=read(owned.with_name('acquisition.json'))
        if acquired['sha256']!=witness['sha256']:raise ValueError('Award recovery witness changed')
        witness=acquired
    if finished_attempt(previous,version,witness['sha256']):return previous
    same=(previous.get('implementationSha256')==version and previous.get('sourceSha256')==witness['sha256'])
    result=dict(gamePk=game_pk,implementationSha256=version,sourceSha256=witness['sha256'],
        sourceWitness=witness,checkedAtUtc=TX.now(),attempts=previous.get('attempts',0)+1 if same else 1)
    try:
        result.update(add_game(state,game_pk,witness,java,mapper,classpath))
        if result['status'] in {'complete','already-complete'} and witness.get('recoveryRequestSha256'):
            result['additionComplete']=True
            atomic(control,result)  # a cleanup interruption must not repeat mapping
            retire_recovery_input(state,result)
    except Exception as error:result.update(status='failed',error=str(error))
    atomic(control,result);return result

def fingerprint():
    return hashlib.sha256(Path(__file__).read_bytes()+SHAPE.read_bytes()+A.MAPPING.read_bytes()
        +Path(A.__file__).read_bytes()+C.fingerprint().encode()+(ROOT/DECISION).read_bytes()
        +(ROOT/DEPENDENCY_DECISION).read_bytes()+(ROOT/FINAL_AWARD_DECISION).read_bytes()
        +FINAL_AWARD_CASES.read_bytes()+RECOVERY.read_bytes()).hexdigest()


def final_award_witness(state):
    """Only W3's five retained responses; no acquisition or widened inventory."""
    version=fingerprint()
    for case in read(FINAL_AWARD_CASES)['cases']:
        if not A.SCOPE.active(state,case['gamePk']):continue
        pk=case['gamePk'];witness=case['sourceWitness']
        if not (state/'pipeline/evidence/nifi/game-promotion'/pk).is_dir():continue
        control=state/'pipeline/control/mlb-game/award-addition'/(pk+'.json')
        previous=read(control) if control.is_file() else {}
        if finished_attempt(previous,version,witness['sha256']):continue
        source=Path(witness['path'])
        if not source.is_file() or sha(source)!=witness['sha256']:
            # Preserve a missing retained witness as a case failure; never
            # fetch replacement bytes or prevent the other cases from running.
            atomic(control,dict(gamePk=pk,status='failed',error='W3 exact retained response unavailable',
                implementationSha256=version,sourceSha256=witness['sha256'],attempts=2,checkedAtUtc=TX.now()))
            continue
        return dict(gamePk=pk,**witness)
    return None


def next_witness(state,limit=50):
    """Bounded retained-input inventory; run the reviewed fixture first."""
    excluded=A.SCOPE.excluded_games(state)
    control=state/'pipeline/control/mlb-game/award-addition'
    final_award=final_award_witness(state)
    if final_award:return final_award
    fixture=control/'822864.json'
    witness=state/'pipeline/quarantine/mlb-game/822864/3011ddc6cb194b2ea53ec644bfcc5d4e/input.json'
    if not fixture.is_file() or read(fixture).get('status') not in {'complete','already-complete','already-present'}:
        previous=read(fixture) if fixture.is_file() else {}
        if previous.get('implementationSha256')==fingerprint() and previous.get('attempts',0)>=2:return None
        if witness.is_file():
            return dict(gamePk='822864',path=str(witness),sha256='24adfc15c105909a4e09faedeb268cab6e58e5c3b630f1b7637af60f77c57b1e')
        raise ValueError('The approved W1 fixture is unavailable')
    recovery=recovery_witness(state)
    if recovery:return recovery
    inventory_path=control/'inventory.json'
    inventory=read(inventory_path) if inventory_path.is_file() else dict(inputs={})
    version=fingerprint();inspected=0
    paths=sorted((state/'pipeline/quarantine/mlb-game').glob('*/*/input.json'))
    paths+=sorted((ROOT/'data/raw').rglob('*.json'))
    for path in paths:
        # A successfully promoted owner can retire a transient input after
        # directory enumeration. Continue the bounded inventory in that case.
        try:stat=path.stat()
        except FileNotFoundError:continue
        previous=inventory['inputs'].get(str(path),{})
        if previous.get('gamePk') in excluded or path.parent.parent.name in excluded:continue
        promoted=state/'pipeline/evidence/nifi/game-promotion'
        prior_pk=previous.get('gamePk','')
        metadata=[stat.st_size,stat.st_mtime_ns,version,bool(prior_pk.isdecimal() and (promoted/prior_pk).is_dir())]
        if previous.get('identity')==metadata:continue
        try:raw=path.read_bytes()
        except FileNotFoundError:continue
        digest=hashlib.sha256(raw).hexdigest()
        try:doc=json.loads(raw)
        except (ValueError,UnicodeError) as error:
            inventory['inputs'][str(path)]=dict(identity=metadata,sha256=digest,gamePk='',status='invalid-input',error=str(error))
            inspected+=1
            if inspected>=limit:break
            continue
        if not isinstance(doc,dict):doc={}
        pk=str(doc.get('gamePk',''))
        if pk in excluded or A.SCOPE.exclusion_reason(doc):continue
        metadata[-1]=bool(pk.isdecimal() and (promoted/pk).is_dir())
        record=dict(identity=metadata,sha256=digest,gamePk=pk,status='not-applicable')
        possible=[p for p in doc.get('liveData',{}).get('plays',{}).get('allPlays',[])
            if p.get('result',{}).get('eventType')=='intent_walk' and len(p.get('playEvents',[]))>4]
        if possible and metadata[-1]:
            result=read(control/(pk+'.json')) if (control/(pk+'.json')).is_file() else {}
            if finished_attempt(result,version,digest) and result.get('status') in {'complete','already-complete','already-present','not-applicable'}:
                record['status']='complete'
            else:
                try:
                    selected=select(raw,pk)
                    if selected:record.update(status='selected',plateAppearances=[p['atBatIndex'] for p in selected])
                except (KeyError,TypeError,ValueError) as error:record.update(status='withheld',error=str(error))
                if record['status']=='selected':
                    # Keep pending until tick writes a durable result.
                    if not finished_attempt(result,version,digest):
                        atomic(inventory_path,inventory)
                        return dict(gamePk=pk,path=str(path),sha256=digest)
                    record.update(status='failed',error=result.get('error'))
        inventory['inputs'][str(path)]=record;inspected+=1
        if inspected>=limit:break
    inventory.update(checkedAtUtc=TX.now(),inspectedThisTick=inspected)
    atomic(inventory_path,inventory)
    return None


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-root',type=Path,required=True);parser.add_argument('--next',action='store_true')
    for key in ('java','mapper','jena-classpath','input'):parser.add_argument('--'+key,type=Path)
    parser.add_argument('--game-pk');parser.add_argument('--input-sha256')
    args=parser.parse_args()
    if args.next:
        print(json.dumps(next_witness(args.state_root)));raise SystemExit(0)
    if not all((args.java,args.mapper,args.jena_classpath,args.input,args.game_pk,args.input_sha256)):
        parser.error('Execution requires game, retained input/hash, Java, mapper and Jena classpath')
    result=tick(args.state_root,args.game_pk,dict(path=str(args.input),sha256=args.input_sha256),args.java,args.mapper,args.jena_classpath)
    print(json.dumps(result));raise SystemExit(result['status']=='failed')
