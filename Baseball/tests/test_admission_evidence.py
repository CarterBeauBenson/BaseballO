import importlib.util
import ast
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import subprocess
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('admission_evidence',ROOT/'sources/mlb-game/pipeline/admission-evidence.py')
E=importlib.util.module_from_spec(spec);spec.loader.exec_module(E)


class AdmissionEvidence(unittest.TestCase):
    def test_prior_admitted_clock_proofs_have_identical_checks_when_source_issues_are_empty(self):
        record=E.read(E.COMPATIBILITY_PATH)['priorClockIsolation']
        def old(path):
            return subprocess.check_output(['git','-C',str(ROOT.parent),'show',
                record['changeCommit']+'^:Baseball/'+path])
        def tree(text):return ast.dump(ast.parse(text),include_attributes=False)
        source='sources/mlb-game/pipeline/reconcile-metric-source.py'
        before=ast.parse(old(source));after=ast.parse((ROOT/source).read_bytes())
        definitions={n.name:n for n in after.body if isinstance(n,ast.FunctionDef)}
        current=definitions['reconcile']
        # T1 adds an issue partition and diagnostic values, not new issue
        # predicates. Verify those exact edits before comparing the whole AST.
        added={
            'clock_conflicts':"clock_conflicts = [i for i in issues if i['code'] in CLOCK_CONFLICT_CODES]",
            'blocking_issues':"blocking_issues = [i for i in issues if i['code'] not in CLOCK_CONFLICT_CODES]"}
        for name,statement in added.items():
            matches=[n for n in current.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets)]
            self.assertEqual(len(matches),1)
            self.assertEqual(ast.dump(matches[0]),ast.dump(ast.parse(statement).body[0]))
            current.body.remove(matches[0])
        returned=current.body[-1].value
        extra={k.arg:k.value for k in returned.keywords if k.arg in {'blockingIssues','clockConflicts','clockDecision','clockStatus'}}
        expected=ast.parse("dict(blockingIssues=blocking_issues,clockConflicts=clock_conflicts,clockDecision=CLOCK_DECISION,clockStatus='conflicted' if clock_conflicts else 'no-reversed-pairs')").body[0].value
        self.assertEqual({k:ast.dump(v) for k,v in extra.items()},{k.arg:ast.dump(k.value) for k in expected.keywords})
        returned.keywords=[k for k in returned.keywords if k.arg not in extra]
        status=next(k for k in returned.keywords if k.arg=='status')
        self.assertEqual(ast.dump(status.value),ast.dump(ast.parse("'consistent' if not blocking_issues else 'inconsistent'",mode='eval').body))
        status.value=ast.parse("'consistent' if not issues else 'inconsistent'",mode='eval').body
        for node in ast.walk(current):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='issue' and node.args and isinstance(node.args[0],ast.Constant):
                code=node.args[0].value
                if code in {'REVERSED_PLAY_TIMES','REVERSED_EVENT_TIMES'}:
                    variable='about' if code=='REVERSED_PLAY_TIMES' else 'event'
                    self.assertEqual({k.arg:ast.dump(k.value) for k in node.keywords},
                        {key:ast.dump(ast.parse(variable+"['"+key+"']",mode='eval').body) for key in ('startTime','endTime')})
                    node.keywords=[]
        constants={n.targets[0].id:n for n in after.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name)}
        self.assertEqual(ast.literal_eval(constants['CLOCK_CONFLICT_CODES'].value),{'REVERSED_PLAY_TIMES','REVERSED_EVENT_TIMES'})
        self.assertEqual(ast.literal_eval(constants['CLOCK_DECISION'].value),'archive/design-records/mlb-game-clock-conflict-isolation/review.json')
        self.assertEqual(ast.literal_eval(constants['VERSION'].value),2)
        constants['VERSION'].value=ast.Constant(1)
        after.body=[n for n in after.body if n not in (constants['CLOCK_CONFLICT_CODES'],constants['CLOCK_DECISION'])]
        self.assertEqual(ast.dump(before),ast.dump(after))

        class PriorIssueKey(ast.NodeTransformer):
            def visit_Subscript(self,node):
                self.generic_visit(node)
                if isinstance(node.slice,ast.Constant) and node.slice.value=='blockingIssues':node.slice.value='issues'
                return node
        for family,entry in record['families'].items():
            if family in {'pitch-count','runner-boundary'}:
                continue  # Context-dependent positive cases are exercised below.
            own='sources/mlb-game/pipeline/'+family+'-admission.py'
            shape='sources/mlb-game/shacl/'+family+'-admission.ttl'
            support='sources/mlb-game/pipeline/batting-admission.py'
            validator='scripts/pipeline/validate-shacl.py';context='scripts/pipeline/prepare-rml-context.py'
            adapter=E.module(ROOT/own,'prior_'+family.replace('-','_'))
            self.assertEqual(adapter.fingerprint(),entry['currentImplementationSha256'])
            self.assertEqual(tree(old(own)),ast.dump(PriorIssueKey().visit(ast.parse((ROOT/own).read_bytes()))))
            for unchanged in (shape,validator):self.assertEqual(old(unchanged),(ROOT/unchanged).read_bytes())
            paths=([own,shape,source,validator] if family=='batting' else
                [own,shape,support,source,validator] if family=='scoring-run' else
                [own,shape,context,support,source,validator])
            digest=hashlib.sha256('\n'.join(p+':'+hashlib.sha256(old(p)).hexdigest() for p in paths).encode()).hexdigest()
            self.assertEqual(digest,entry['previousImplementationSha256'])
            if family=='runner-resolution':
                definition=lambda raw:next(n for n in ast.parse(raw).body if getattr(n,'name',None)=='nonmovement_strikeout_records')
                self.assertEqual(ast.dump(definition(old(context))),ast.dump(definition((ROOT/context).read_bytes())))

    def test_prior_clock_reuse_requires_positive_hash_bound_source_census(self):
        record=E.read(E.COMPATIBILITY_PATH)
        entries=[(family,entry,kind) for section,kind in
            [('priorClockIsolation','prior-stricter-clock-check'),
             ('priorPinchHitterIsolation','prior-stricter-pinch-hitter-check')]
            for family,entry in record[section]['families'].items()]
        for family,entry,kind in entries:
            with self.subTest(family=family),tempfile.TemporaryDirectory() as temp:
                state=Path(temp);path=state/'pipeline/evidence/mlb-game/1/run'/f'{family}.json'
                proof=dict(artifactType='baseballo-'+family+'-admission',contractVersion=1,gamePk='1',
                    graph='graph',sourceSha256='source',authoritativeRdfSha256='rdf',
                    implementationSha256=entry['previousImplementationSha256'],status='admitted',
                    sourceReconciled=True,graphConforms=True,issues=[])
                for suffix,key in (('.source.json','sourceCensusSha256'),('.shapes.ttl','shapeSha256'),('.report.ttl','reportSha256')):
                    E.atomic(path.with_suffix(suffix),dict(gamePk='1',sourceSha256='source',status='reconciled',issues=[]))
                    proof[key]=E.sha(path.with_suffix(suffix))
                marker=state/'promotion.json';field=E.FIELDS[family]
                def publish(value):
                    E.atomic(path,value);E.atomic(marker,{field:str(path),field+'Sha256':E.sha(path)})
                    return dict(gamePk='1',rawSha256='source',authoritativeGraph='graph',authoritativeRdfSha256='rdf',
                        promotionManifest=str(marker),promotionManifestSha256=E.sha(marker))
                promotion=publish(proof)
                result=E.compatible_proof(state,promotion,family,entry['currentImplementationSha256'])
                self.assertEqual({key:result[key] for key in proof},proof)
                self.assertEqual(result['implementationReuse']['kind'],kind)
                self.assertIsNone(E.compatible_proof(state,promotion,family,'unknown-next-version'))
                self.assertIsNone(E.compatible_proof(state,{**promotion,'rawSha256':'different'},family,entry['currentImplementationSha256']))
                self.assertIsNone(E.compatible_proof(state,publish({**proof,'status':'withheld'}),family,entry['currentImplementationSha256']))
                E.atomic(path.with_suffix('.source.json'),dict(gamePk='1',sourceSha256='source',status='withheld',issues=[dict(code='REVERSED_PLAY_TIMES')]))
                inconsistent={**proof,'sourceCensusSha256':E.sha(path.with_suffix('.source.json'))}
                with self.assertRaisesRegex(ValueError,'reconciled source census'):
                    E.compatible_proof(state,publish(inconsistent),family,entry['currentImplementationSha256'])

    def test_prior_positive_count_and_boundary_checks_preserve_census_and_shapes(self):
        record=E.read(E.COMPATIBILITY_PATH)
        raw=(ROOT/'data/raw/game-566279.json').read_bytes()
        for section,families in [('priorClockIsolation',('pitch-count','runner-boundary')),
                                 ('priorPinchHitterIsolation',('runner-boundary',))]:
            change=record[section]
            for family in families:
                with self.subTest(section=section,family=family),tempfile.TemporaryDirectory() as temp:
                    own='sources/mlb-game/pipeline/'+family+'-admission.py'
                    shape='sources/mlb-game/shacl/'+family+'-admission.ttl'
                    context='scripts/pipeline/prepare-rml-context.py'
                    support='sources/mlb-game/pipeline/batting-admission.py'
                    source='sources/mlb-game/pipeline/reconcile-metric-source.py'
                    validator='scripts/pipeline/validate-shacl.py'
                    paths=([own,shape,context,support,source,validator] if family=='runner-boundary' else
                           [own,shape,support,source,context,validator])
                    prior_root=Path(temp)/'Baseball'
                    for relative in paths:
                        contents=subprocess.check_output(['git','-C',str(ROOT.parent),'show',
                            change['changeCommit']+'^:Baseball/'+relative])
                        target=prior_root/relative;target.parent.mkdir(parents=True,exist_ok=True)
                        target.write_bytes(contents)
                    before=E.module(prior_root/own,'old_positive_'+family.replace('-','_'))
                    after=E.module(ROOT/own,'current_positive_'+family.replace('-','_'))
                    entry=change['families'][family]
                    self.assertEqual(before.fingerprint(),entry['previousImplementationSha256'])
                    self.assertEqual(after.fingerprint(),entry['currentImplementationSha256'])
                    for unchanged in (shape,validator):
                        self.assertEqual((prior_root/unchanged).read_bytes(),(ROOT/unchanged).read_bytes())
                    previous=before.census(raw,'566279');current=after.census(raw,'566279')
                    self.assertEqual(previous['issues'],[])
                    self.assertEqual(current,previous)
                    self.assertEqual(after.shape_text(current),before.shape_text(previous))
                    # The newly handled initial PH case could not supply a
                    # previous positive check. Existing complete substitutions
                    # keep their exact participants, even across both edits.
                    doc=json.loads((ROOT/'data/raw/samples/2026-07-18/824169.json').read_bytes())
                    play=doc['liveData']['plays']['allPlays'][31]
                    self.assertEqual(before.CONTEXT.batter_participation_context(play,'824169',source_consistent=True),
                                     after.CONTEXT.batter_participation_context(play,'824169',source_consistent=True))
                    play['playEvents']=play['playEvents'][3:]
                    for index,event in enumerate(play['playEvents']):event['index']=index
                    play['playEvents'][0].pop('replacedPlayer')
                    play['playEvents'][0]['count'].update(balls=0,strikes=0)
                    with self.assertRaises((KeyError,ValueError)):
                        before.CONTEXT.batter_participation_context(play,'824169',source_consistent=True)
                    self.assertEqual(len(after.CONTEXT.batter_participation_context(play,'824169',source_consistent=True)['participations']),1)

    def test_exact_q5_edit_does_not_change_reused_proof_dependencies(self):
        record=E.read(E.COMPATIBILITY_PATH)
        path=ROOT/record['contextPath']
        old=subprocess.check_output(['git','-C',str(ROOT.parent),'show',
            record['changeCommit']+'^:Baseball/'+record['contextPath']])
        current=path.read_bytes()
        self.assertEqual(hashlib.sha256(old).hexdigest(),record['previousContextSha256'])
        self.assertEqual(hashlib.sha256(current).hexdigest(),record['currentContextSha256'])
        before,after=ast.parse(old),ast.parse(current)
        changed=record['changedDefinition']
        # The whole module, including imports and constants, must be identical
        # apart from this one definition. Never infer compatibility by labels.
        def without_changed(tree):
            clone=copy.deepcopy(tree)
            clone.body=[n for n in clone.body if getattr(n,'name',None)!=changed]
            return ast.dump(clone,include_attributes=False)
        self.assertEqual(without_changed(before),without_changed(after))
        definitions={n.name:n for n in after.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
        old_definitions={n.name:n for n in before.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
        self.assertNotEqual(ast.dump(old_definitions[changed]),ast.dump(definitions[changed]))
        for family,entry in record['families'].items():
            adapter=E.module(E.HERE/(family+'-admission.py'),'equivalence_'+family.replace('-','_'))
            self.assertEqual(adapter.fingerprint(),entry['currentImplementationSha256'])
            context_attributes={n.attr for n in ast.walk(ast.parse(Path(adapter.__file__).read_text()))
                if isinstance(n,ast.Attribute) and isinstance(n.value,ast.Name) and n.value.id=='CONTEXT'}
            self.assertEqual(context_attributes,set(entry['contextDefinitions']))
            visited=set();pending=list(context_attributes & definitions.keys())
            while pending:
                name=pending.pop()
                if name in visited:continue
                visited.add(name)
                nodes=list(ast.walk(definitions[name]))
                self.assertFalse(any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name)
                    and n.func.id in {'eval','exec','getattr','globals','locals','__import__','module'} for n in nodes))
                pending.extend({n.id for n in nodes if isinstance(n,ast.Name)} & definitions.keys()-visited)
            self.assertNotIn(changed,visited,family)
            common=[E.HERE/'batting-admission.py',E.HERE/'reconcile-metric-source.py',ROOT/'scripts/pipeline/validate-shacl.py']
            paths=([Path(adapter.__file__),adapter.SHAPE,path,*common] if family=='runner-resolution' else
                [Path(adapter.__file__),adapter.SHAPE,*common[:2],path,common[2]])
            prior=hashlib.sha256('\n'.join(p.relative_to(ROOT).as_posix()+':'+
                (record['previousContextSha256'] if p==path else E.sha(p)) for p in paths).encode()).hexdigest()
            self.assertEqual(prior,entry['previousImplementationSha256'])
        self.assertNotIn('runner-boundary',record['families'])

    def test_equivalent_code_reuses_exact_proof_without_changing_its_outcome_or_fingerprint(self):
        record=E.read(E.COMPATIBILITY_PATH)
        for family,status in [('runner-resolution','admitted'),('pitch-count','withheld'),('defensive','withheld')]:
            with self.subTest(family=family),tempfile.TemporaryDirectory() as temp:
                state=Path(temp);path=state/'pipeline/evidence/mlb-game/1/run'/f'{family}.json'
                entry=record['families'][family]
                proof=dict(artifactType='baseballo-'+family+'-admission',contractVersion=1,
                    status=status,gamePk='1',sourceSha256='source',authoritativeRdfSha256='rdf',graph='graph',
                    implementationSha256=entry['previousImplementationSha256'],sourceReconciled=True,graphConforms=True,
                    issues=[] if status=='admitted' else [dict(code='ORIGINAL_WITHHELD_REASON')])
                for suffix,key in (('.source.json','sourceCensusSha256'),('.shapes.ttl','shapeSha256'),('.report.ttl','reportSha256')):
                    E.atomic(path.with_suffix(suffix),dict(retained=key));proof[key]=E.sha(path.with_suffix(suffix))
                E.atomic(path,proof);original=path.read_bytes()
                marker=state/'promotion.json';field=E.FIELDS[family]
                E.atomic(marker,{field:str(path),field+'Sha256':E.sha(path)})
                promotion=dict(gamePk='1',rawSha256='source',authoritativeRdfSha256='rdf',authoritativeGraph='graph',
                    promotionManifest=str(marker),promotionManifestSha256=E.sha(marker))
                adapter=SimpleNamespace(fingerprint=lambda:entry['currentImplementationSha256'],
                    promoted_admission=lambda *args:{'status':'withheld'})
                result=E.load(adapter,state,promotion,family)
                self.assertEqual({key:result[key] for key in proof},proof)
                self.assertEqual(path.read_bytes(),original)
                self.assertEqual(result['implementationReuse']['currentImplementationSha256'],adapter.fingerprint())
                self.assertEqual(E.diagnostic(state,promotion,family,adapter.fingerprint())['evidenceState'],'implementation-compatible')
                self.assertIsNone(E.compatible_proof(state,{**promotion,'rawSha256':'different'},family,adapter.fingerprint()))
                self.assertIsNone(E.compatible_proof(state,promotion,family,'unrecognized-next-version'))
                if family=='defensive':
                    invalid={**proof,'status':'admitted','populationComplete':False}
                    E.atomic(path,invalid);E.atomic(marker,{field:str(path),field+'Sha256':E.sha(path)})
                    invalid_promotion={**promotion,'promotionManifestSha256':E.sha(marker)}
                    with self.assertRaisesRegex(ValueError,'conformance evidence'):
                        E.load(adapter,state,invalid_promotion,family)
                    E.atomic(path,proof);E.atomic(marker,{field:str(path),field+'Sha256':E.sha(path)})
                path.with_suffix('.report.ttl').write_text('changed report')
                with self.assertRaisesRegex(ValueError,'artifact changed'):E.load(adapter,state,promotion,family)

    def test_stale_previously_withheld_is_preserved_and_never_admitted(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);path=state/'pipeline/evidence/mlb-game/1/run/defensive.json'
            proof=dict(status='withheld',gamePk='1',sourceSha256='source',authoritativeRdfSha256='rdf',
                implementationSha256='old',issues=[dict(code='INCOMPLETE_DEFENSIVE_POPULATION')])
            E.atomic(path,proof)
            marker=state/'promotion.json';E.atomic(marker,dict(defensiveAdmission=str(path),defensiveAdmissionSha256=E.sha(path)))
            promotion=dict(gamePk='1',rawSha256='source',authoritativeRdfSha256='rdf',authoritativeGraph='graph',
                promotionManifest=str(marker),promotionManifestSha256=E.sha(marker))
            result=E.diagnostic(state,promotion,'defensive','current')
            self.assertEqual((result['evidenceState'],result['previousStatus']),('implementation-stale','withheld'))
            self.assertEqual(result['previousIssues'],proof['issues'])
            adapter=SimpleNamespace(fingerprint=lambda:'current',promoted_admission=lambda *args:{'status':'withheld'})
            self.assertEqual(E.load(adapter,state,promotion,'defensive'),{'status':'withheld'})
            # A separately produced current proof still must match the exact graph,
            # source, implementation, promotion and retained artifacts.
            target=E.refresh_path(state,promotion,'defensive','current')
            E.atomic(target,{**proof,'artifactType':'baseballo-defensive-admission','contractVersion':1,
                'graph':'graph','implementationSha256':'current'})
            E.atomic(target.with_suffix('.receipt.json'),dict(promotionManifestSha256=E.sha(marker),proofSha256=E.sha(target)))
            self.assertEqual(E.load(adapter,state,promotion,'defensive')['issues'],proof['issues'])
            changed=E.read(target);changed['sourceSha256']='another-input';E.atomic(target,changed)
            E.atomic(target.with_suffix('.receipt.json'),dict(promotionManifestSha256=E.sha(marker),proofSha256=E.sha(target)))
            with self.assertRaisesRegex(ValueError,'different inputs'):E.load(adapter,state,promotion,'defensive')


if __name__=='__main__':unittest.main()
