"""Exact graph-pair counts without a grouped scan across the named dataset.

Each branch counts one fixed graph. Empty/missing graphs produce no row, as
in the original grouped query, and index identity is checked independently.
The materializer still compares every count and identity with promotion proof.
"""
import re

SOURCE = 'https://w3id.org/baseball/graph/game/'
INDEX = 'https://w3id.org/baseball/graph/query-index/game/'
GAME = 'https://baseballontology.org/data/game/'
RESOURCE = 'https://w3id.org/baseball/query-index-build/game/'
MAX_BATCH = 200


def records_in_scope(records):
    if not records or len(records) > MAX_BATCH:
        raise ValueError('Live graph count requires between 1 and 200 promoted games')
    seen = set()
    for record in records:
        identifier = str(record.get('gamePk', ''))
        if not re.fullmatch(r'[0-9]+', identifier) or identifier in seen:
            raise ValueError('Invalid or duplicate live graph-count game identity')
        seen.add(identifier)
        expected = dict(authoritativeGraph=SOURCE+identifier, queryIndexGraph=INDEX+identifier,
                        gameIri=GAME+identifier, queryIndexResource=RESOURCE+identifier)
        if any(record.get(key) != value for key, value in expected.items()):
            raise ValueError('Live graph-count identity differs from its promoted game')
        yield expected


def source_counts(records):
    branches = []
    for row in records_in_scope(records):
        branches.append('''{
  { SELECT (COUNT(*) AS ?sourceCount) WHERE {
      GRAPH <%s> { ?sourceSubject ?sourcePredicate ?sourceObject }
  } }
  FILTER(?sourceCount > 0)
  BIND(<%s> AS ?sourceGraph)
  BIND(<%s> AS ?game)
}''' % (row['authoritativeGraph'], row['authoritativeGraph'], row['gameIri']))
    return 'SELECT ?sourceGraph ?game ?sourceCount WHERE {\n' + '\nUNION\n'.join(branches) + '\n}\nORDER BY ?sourceGraph\n'


def index_counts(records):
    branches = []
    for row in records_in_scope(records):
        branches.append('''{
  { SELECT (COUNT(*) AS ?indexCount) WHERE {
      GRAPH <%s> { ?indexSubject ?indexPredicate ?indexObject }
  } }
  FILTER(?indexCount > 0)
  FILTER EXISTS {
    GRAPH <%s> {
      <%s> a <https://w3id.org/baseball/query-index/QueryIndex> ;
          <https://w3id.org/baseball/query-index/sourceGraph> <%s> ;
          <https://w3id.org/baseball/query-index/indexedGame> <%s> .
    }
  }
  BIND(<%s> AS ?indexGraph)
  BIND(<%s> AS ?sourceGraph)
  BIND(<%s> AS ?game)
  BIND(<%s> AS ?indexResource)
}''' % (row['queryIndexGraph'], row['queryIndexGraph'], row['queryIndexResource'],
        row['authoritativeGraph'], row['gameIri'], row['queryIndexGraph'],
        row['authoritativeGraph'], row['gameIri'], row['queryIndexResource']))
    return ('SELECT ?indexGraph ?sourceGraph ?game ?indexResource ?indexCount WHERE {\n'
            + '\nUNION\n'.join(branches) + '\n}\nORDER BY ?indexGraph\n')
