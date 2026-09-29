"""Independent roster and player checks over the existing B1 graph contract.

This is validation provenance, never an alternative source of metric values.
Original whole-game admissions remain unchanged. Each player must pass all
applicable B1 membership, result, assignment and count constraints.
"""
import importlib.util
import json
from pathlib import Path
import tempfile
import urllib.request
from rdflib import Graph, Literal, URIRef, Namespace

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
spec=importlib.util.spec_from_file_location('individual_b1_contract',HERE/'batting-admission.py')
B=importlib.util.module_from_spec(spec);spec.loader.exec_module(B)
SHAPE=HERE.parent/'shacl/player-participation-admission.ttl'
SH=Namespace('http://www.w3.org/ns/shacl#')
ROSTER=URIRef('urn:baseballo:validation:player-participation:roster')
INVENTORY=URIRef('urn:baseballo:validation:player-participation:inventory')


def fingerprint():
    return B.sha(Path(__file__).read_bytes()+SHAPE.read_bytes()+B.fingerprint().encode())


def node(name,target,queries):
    constraints=['sh:sparql [ sh:message '+Literal(message).n3()+' ; sh:select '+
                 Literal(B.PREFIXES+query).n3()+' ]' for message,query in queries]
    return B.iri(name)+' a sh:NodeShape ; sh:targetNode '+B.iri(target)+' ; '+ ' ;\n'.join(constraints)+' .'


def members(values):
    return ', '.join(B.iri(v) for v in sorted(set(values))) or '<urn:baseballo:no-members>'


def shape_text(source):
    game=B.iri(source['game']);roster=source['roster'];turns=source['members']
    if not roster or len({r['player'] for r in roster})!=len(roster):
        raise ValueError('A complete unambiguous roster is required')
    missing=[];expected=[]
    for row in roster:
        player,team=row['player'],row['team'];role=player+'/team/'+team.rsplit('/',1)[-1]+'/role/player'
        expected.append('|'.join((role,player,team)))
        missing.append('''{ FILTER NOT EXISTS {
$this obo:BFO_0000055 %s . %s a base:PlayerRole ; obo:BFO_0000197 %s ; cco:ont00001992 %s .
?teamRole a base:%sTeamRole ; obo:BFO_0000197 %s ; obo:BFO_0000054 $this . } }''' %
            (B.iri(role),B.iri(role),B.iri(player),B.iri(team),row['side'].title(),B.iri(team)))
    roster_query='''SELECT $this WHERE { { %s } UNION {
$this obo:BFO_0000055 ?role . ?role a base:PlayerRole .
OPTIONAL { ?role obo:BFO_0000197 ?player } OPTIONAL { ?role cco:ont00001992 ?team }
FILTER(!BOUND(?player) || !BOUND(?team) ||
  CONCAT(STR(?role),"|",STR(?player),"|",STR(?team)) NOT IN (%s)) } }''' % (' UNION '.join(missing),B.terms(expected))
    scope='obo:BFO_0000132/obo:BFO_0000132/obo:BFO_0000132 '+game
    missing_turns=['{ FILTER NOT EXISTS { '+B.iri(r['pa'])+' a base:PlateAppearance ; '+scope+' . } }' for r in turns]
    inventory_query='''SELECT $this WHERE { { %s } UNION {
?pa a base:PlateAppearance ; %s . FILTER(?pa NOT IN (%s)) } }''' % (
        ' UNION '.join(missing_turns) or 'FILTER(1 = 0)',scope,members(r['pa'] for r in turns))
    kinds=members(B.BASE+t for t in B.RESULTS.values());shapes=[]
    for person in roster:
        player=person['player'];own=[r for r in turns if r['player']==player]
        absent=[];batters=[];results=[]
        for row in own:
            pa=row['pa'];act=pa+'/batter-act';role=player+'/role/batter'
            pattern=f'''{B.iri(pa)} a base:PlateAppearance ; {scope} .
{B.iri(act)} a base:BatterAct ; obo:BFO_0000132 {B.iri(pa)} ; obo:BFO_0000055 {B.iri(role)} .
{B.iri(role)} a base:BatterRole ; obo:BFO_0000197 $this .'''
            batters.append('|'.join((pa,act,role,player)))
            if row['resultType']:
                result,judgment,decision,record=(pa+s for s in ('/result','/judgment/result','/decision/result','/event-record/result'))
                pattern+=f'''
{B.iri(result)} a base:BaseballInstitutionalProcess, {B.iri(row['resultType'])} ; obo:BFO_0000132 {B.iri(pa)} .
{B.iri(judgment)} a base:BaseballAdjudicationAct ; obo:BFO_0000132 {B.iri(result)} ; cco:ont00001986 {B.iri(decision)} .
{B.iri(decision)} a base:BaseballDecisionICE ; cco:ont00001808 {B.iri(result)} .
{B.iri(record)} a base:BaseballEventRecord ; cco:ont00001808 {B.iri(result)}, {B.iri(judgment)}, {B.iri(decision)} .'''
                results.append('|'.join((pa,result,row['resultType'])))
            absent.append('{ FILTER NOT EXISTS { '+pattern+' } }')
        membership='''SELECT $this WHERE {
{ %s } UNION {
?pa a base:PlateAppearance ; %s .
?act a base:BatterAct ; obo:BFO_0000132 ?pa ; obo:BFO_0000055 ?role .
?role a base:BatterRole ; obo:BFO_0000197 ?player .
FILTER(?player=$this || ?pa IN (%s))
FILTER(CONCAT(STR(?pa),"|",STR(?act),"|",STR(?role),"|",STR(?player)) NOT IN (%s))
} UNION {
?pa a base:PlateAppearance ; %s . FILTER(?pa IN (%s))
?result a base:BaseballInstitutionalProcess, ?type ; obo:BFO_0000132 ?pa .
FILTER(?type IN (%s))
FILTER(CONCAT(STR(?pa),"|",STR(?result),"|",STR(?type)) NOT IN (%s)) } }''' % (
            ' UNION '.join(absent) or 'FILTER(1 = 0)',scope,members(r['pa'] for r in own),B.terms(batters),
            scope,members(r['pa'] for r in own),kinds,B.terms(results))
        # Unknown source counts stay withheld; they are not filled with zero.
        count=person.get('officialPA')
        count_query='SELECT $this WHERE { FILTER(true) }' if not B.integer(count) else '''SELECT $this WHERE {
{ SELECT $this (COUNT(DISTINCT ?pa) AS ?actual) WHERE {
%s obo:BFO_0000055 ?rosterRole .
?rosterRole a base:PlayerRole ; obo:BFO_0000197 $this .
OPTIONAL {
?pa a base:PlateAppearance ; %s .
?act a base:BatterAct ; obo:BFO_0000132 ?pa ; obo:BFO_0000055 ?role .
?role a base:BatterRole ; obo:BFO_0000197 $this .
?result a base:BaseballInstitutionalProcess, ?type ; obo:BFO_0000132 ?pa . FILTER(?type IN (%s))
?judgment a base:BaseballAdjudicationAct ; obo:BFO_0000132 ?result ; cco:ont00001986 ?decision .
?decision a base:BaseballDecisionICE ; cco:ont00001808 ?result .
?record a base:BaseballEventRecord ; cco:ont00001808 ?result, ?judgment, ?decision .
} } GROUP BY $this } FILTER(?actual != %d) }''' % (game,scope,kinds,count)
        shapes.append(node('urn:baseballo:validation:player-participation:'+player.rsplit('/',1)[-1],player,
            [('B1 player PA/result/batter membership differs',membership),('B1 official player PA count differs',count_query)]))
    text=SHAPE.read_text(encoding='utf-8').replace('# __ROSTER_SHAPE__',node(str(ROSTER),source['game'],[('B1/E1 game roster differs',roster_query)]))
    text=text.replace('# __INVENTORY_SHAPE__',node(str(INVENTORY),source['game'],[('B1 complete PA inventory differs',inventory_query)]))
    text=text.replace('# __PLAYER_SHAPES__','\n'.join(shapes))
    Graph().parse(data=text,format='turtle')
    return text


def outcome(source,report):
    """Read SHACL results; source reconciliation issues keep their scope."""
    failures={str(n) for n in report.objects(None,SH.sourceShape)}
    roster=source['roster'];people={r['player'] for r in roster}
    by_index={r['atBatIndex']:r['player'] for r in source['members'] if 'atBatIndex' in r}
    blocked={p:[] for p in people};roster_issues=[]
    for issue in source.get('issues',[]):
        player=issue.get('player')
        if player and not player.startswith(B.BASE):player=B.BASE+'data/player/'+player
        if player not in people:player=by_index.get(issue.get('atBatIndex'))
        affected={player} if player else people
        for p in affected:blocked[p].append(issue)
        if issue.get('code') in {'ROSTER_IDENTITY_MISMATCH','AMBIGUOUS_PLAYER_TEAM','MISSING_TEAM_ROSTER','AMBIGUOUS_GAME_ROSTER'}:
            roster_issues.append(issue)
    roster_ok=str(ROSTER) not in failures and not roster_issues
    inventory_ok=str(INVENTORY) not in failures
    players=[]
    for row in roster:
        player=row['player'];issues=list(blocked[player])
        if not roster_ok:issues.append(dict(code='COMPLETE_GAME_ROSTER'))
        if not inventory_ok:issues.append(dict(code='COMPLETE_PA_INVENTORY'))
        if 'urn:baseballo:validation:player-participation:'+player.rsplit('/',1)[-1] in failures:
            issues.append(dict(code='PLAYER_GRAPH_CONFORMANCE'))
        players.append(dict(player=player,status='withheld' if issues else 'admitted',issues=issues))
    return dict(rosterComplete=roster_ok,plateAppearanceInventoryComplete=inventory_ok,players=players)


def proof_path(evidence,state,promotion):
    # Keep receipts below Windows MAX_PATH under the two full hash keys.
    return evidence.refresh_path(state,promotion,'players',fingerprint())


def retained_source(evidence,state,promotion):
    """Use a retained census, or a retained failed input as a separate witness.

    A later source response is not relabeled as the promotion's original bytes.
    It must independently match the existing graph through these B1 constraints.
    No source data is acquired and no RML or context builder runs here.
    """
    marker=evidence.checked_marker(promotion)
    original=Path(marker.get('battingAdmission',''))
    owner=(Path(state)/'pipeline/evidence/mlb-game'/promotion['gamePk']).resolve()
    if original.is_file():
        if not original.resolve().is_relative_to(owner) or evidence.sha(original)!=marker.get('battingAdmissionSha256'):
            raise ValueError('Retained participation source proof changed')
        proof=evidence.read(original);source_path=original.with_suffix('.source.json')
        if (proof.get('sourceSha256')==promotion['rawSha256']
                and proof.get('authoritativeRdfSha256')==promotion['authoritativeRdfSha256']
                and proof.get('gamePk')==promotion['gamePk'] and source_path.is_file()):
            if evidence.sha(source_path)!=proof.get('sourceCensusSha256'):
                raise ValueError('Retained participation census changed')
            version=proof.get('implementationSha256')
            if version==B.fingerprint() or evidence.code_equivalence('batting',version,B.fingerprint()) is not None:
                return evidence.read(source_path),dict(kind='retained-b1-census',path=str(source_path),sha256=evidence.sha(source_path))
    candidates=sorted((Path(state)/'pipeline/quarantine/mlb-game'/promotion['gamePk']).glob('*/input.json'))
    if not candidates:return None
    # Prefer original bytes; otherwise retain the later response's distinct hash.
    candidates.sort(key=lambda p:(evidence.sha(p)!=promotion['rawSha256'],str(p)))
    path=candidates[0];raw=path.read_bytes();source=B.census(raw,promotion['gamePk'])
    return source,dict(kind='retained-source-response',path=str(path),sha256=B.sha(raw))


def load(evidence,state,promotion):
    path=proof_path(evidence,state,promotion);receipt=path.with_suffix('.receipt.json')
    if not receipt.is_file():return None
    record=evidence.read(receipt)
    if record.get('promotionManifestSha256')!=promotion['promotionManifestSha256'] or record.get('proofSha256')!=evidence.sha(path):
        raise ValueError('Player participation receipt changed')
    proof=evidence.read(path)
    expected=dict(artifactType='baseballo-player-participation-admission',contractVersion=1,
        gamePk=promotion['gamePk'],graph=promotion['authoritativeGraph'],
        authoritativeRdfSha256=promotion['authoritativeRdfSha256'],implementationSha256=fingerprint())
    if any(proof.get(k)!=v for k,v in expected.items()):raise ValueError('Player participation belongs to another graph')
    for suffix,key in (('.source.json','sourceCensusSha256'),('.shapes.ttl','shapeSha256'),('.report.ttl','reportSha256')):
        if evidence.sha(path.with_suffix(suffix))!=proof.get(key):raise ValueError('Player participation artifact changed')
    evidence.checked_marker(promotion)
    return dict(proof,proofSha256=record['proofSha256'])


def prove(evidence,state,promotion,retained,java,classpath,endpoint):
    source,witness=retained;implementation=fingerprint()
    if source.get('gamePk')!=promotion['gamePk'] or source.get('game')!=B.BASE+'data/game/'+promotion['gamePk']:
        raise ValueError('Participation source belongs to another game')
    inventory=B.module(ROOT/'scripts/pipeline/game_promotion_inventory.py','participation_inventory')
    marker=Path(promotion['promotionManifest'])
    def current():
        latest=max(marker.parent.glob('*.json'),key=lambda p:(evidence.read(p).get('promotedAtUtc',''),p.name))
        if latest!=marker or evidence.sha(latest)!=promotion['promotionManifestSha256']:
            raise ValueError('Promotion changed during participation validation')
        record=inventory.validated_promotion_record(Path(state),latest,promotion['gamePk'],inventory.query_index_contract_admission())
        if record['authoritativeRdfSha256']!=promotion['authoritativeRdfSha256']:
            raise ValueError('Participation graph identity changed')
        return record
    record=current();output=proof_path(evidence,state,promotion);output.parent.mkdir(parents=True,exist_ok=True)
    shapes=output.with_suffix('.shapes.ttl');shapes.write_text(shape_text(source),encoding='utf-8',newline='\n')
    query='CONSTRUCT { ?s ?p ?o } WHERE { GRAPH <'+record['authoritativeGraph']+'> { ?s ?p ?o } }'
    request=urllib.request.Request(endpoint,data=query.encode(),headers={'Content-Type':'application/sparql-query','Accept':'text/turtle'})
    session_module=B.module(ROOT/'scripts/pipeline/jena_session.py','participation_jena')
    with tempfile.TemporaryDirectory(prefix='player-existing-graph-') as temporary:
        rdf=Path(temporary)/'graph.ttl'
        with urllib.request.urlopen(request,timeout=120) as response,rdf.open('wb') as stream:
            size=0
            while chunk:=response.read(1024*1024):
                size+=len(chunk)
                if size>128*1024*1024:raise ValueError('Participation graph exceeds single-game read bound')
                stream.write(chunk)
        with session_module.Session(rdf,java,classpath) as session:
            if session.data_count!=record['authoritativeTripleCount']:raise ValueError('Participation graph count changed')
            _,report,_=session.validate_with_jena(data_path=rdf,shape_path=shapes,java=java,classpath=classpath,max_heap='384m')
        export_sha=evidence.sha(rdf)
    current()
    if fingerprint()!=implementation or evidence.sha(Path(witness['path']))!=witness['sha256']:
        raise ValueError('Participation inputs changed during validation')
    evidence.atomic(output.with_suffix('.source.json'),source)
    report_path=output.with_suffix('.report.ttl');report.serialize(destination=report_path,format='turtle')
    result=outcome(source,report)
    proof=dict(artifactType='baseballo-player-participation-admission',contractVersion=1,
        gamePk=promotion['gamePk'],graph=promotion['authoritativeGraph'],
        authoritativeRdfSha256=promotion['authoritativeRdfSha256'],promotionSourceSha256=promotion['rawSha256'],
        validationSourceSha256=source['sourceSha256'],validationExportSha256=export_sha,
        implementationSha256=implementation,engine='jena',retainedSourceEvidence=witness,
        sourceCensusSha256=evidence.sha(output.with_suffix('.source.json')),
        shapeSha256=evidence.sha(shapes),reportSha256=evidence.sha(report_path),**result)
    evidence.atomic(output,proof)
    evidence.atomic(output.with_suffix('.receipt.json'),dict(artifactType='baseballo-admission-evidence-refresh',
        promotionManifestSha256=promotion['promotionManifestSha256'],proofSha256=evidence.sha(output),rdfChanged=False))
    return proof
