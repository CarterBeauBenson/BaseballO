"""Prepared display annotations from the same promoted game graphs as scores."""
import hashlib
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
QUERY = ROOT/'sparql/options/metric-display-labels.rq'
PLAYER = re.compile(r'https://baseballontology.org/data/player/[0-9]+\Z')


def fingerprint():
    return hashlib.sha256(Path(__file__).read_bytes()+QUERY.read_bytes()).hexdigest()


def initialize(connection):
    # Additive migration: existing per-game metric checkpoints remain reusable.
    connection.executescript('''
        CREATE TABLE IF NOT EXISTS dashboard_display_manifest (
            graph_iri TEXT PRIMARY KEY REFERENCES game_dimension(graph_iri), input_sha256 TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS dashboard_display_label (
            graph_iri TEXT NOT NULL REFERENCES game_dimension(graph_iri), entity TEXT NOT NULL,
            label TEXT NOT NULL, PRIMARY KEY(graph_iri,entity));
    ''')


def query(graph):
    if not re.fullmatch(r'https://w3id.org/baseball/graph/game/[0-9]+', graph):
        raise ValueError('Invalid display graph')
    return QUERY.read_text(encoding='utf-8').replace('# DATASET', f'FROM NAMED <{graph}>').replace(
        'VALUES (?graph ?entity)', 'VALUES ?graph').replace(
        '# DISPLAY_ROWS', f'<{graph}>').replace('FILTER(isLiteral(?label))',
        'FILTER(isLiteral(?label)) FILTER(STRSTARTS(STR(?entity), "https://baseballontology.org/data/player/"))')


def store(connection, graph, identity, bindings):
    labels = {}
    for row in bindings:
        entity = row.get('entity',{}); label = row.get('label',{})
        if (row.get('graph',{}).get('value') == graph and entity.get('type') == 'uri'
                and PLAYER.fullmatch(entity.get('value','')) and label.get('type') == 'literal'
                and label.get('value','').strip()):
            labels.setdefault(entity['value'], set()).add(label['value'])
    with connection:
        remove(connection, graph)
        connection.executemany('INSERT INTO dashboard_display_label VALUES (?,?,?)',
            [(graph,entity,next(iter(values))) for entity,values in sorted(labels.items()) if len(values)==1])
        connection.execute('INSERT INTO dashboard_display_manifest VALUES (?,?)', (graph,identity))


def remove(connection, graph):
    for table in ('dashboard_display_label','dashboard_display_manifest'):
        connection.execute(f'DELETE FROM {table} WHERE graph_iri=?',(graph,))


def read(connection, scope, result):
    # Resolve names against each returned player's actual selected graphs.
    # Emit a name on the player record, not the same name once per season game.
    records=[]
    def collect(metric):
        records.extend(metric.get('playerResults', []))
        for group in metric.get('byMechanism', {}).values(): collect(group)
    for metric in result.get('metrics', [result.get('metric', {})]): collect(metric)
    targets={}
    for record in records:
        targets.setdefault(record['player'],set()).update(record.get('graphs', []))
    names={player:set() for player in targets}
    if targets:
        for graph,player,label in connection.execute(
                'SELECT l.graph_iri,l.entity,l.label FROM dashboard_display_label l '
                'JOIN game_dimension g USING(graph_iri) WHERE g.game_set=? AND g.official_date BETWEEN ? AND ?',
                (scope['gameSet'],scope['startDate'],scope['endDate'])):
            if graph in targets.get(player, ()):
                names[player].add(label)
    resolved={player:next(iter(labels)) for player,labels in names.items() if len(labels)==1}
    for record in records:
        record.pop('playerLabel',None)
        if record['player'] in resolved: record['playerLabel']=resolved[record['player']]
    return dict(source='prepared-sql-player-labels',labels=[],namedPlayers=len(resolved),
                conflictingPlayers=sum(len(labels)>1 for labels in names.values()))
