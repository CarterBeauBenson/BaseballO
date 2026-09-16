"""Mechanical source-selected C1 membership versus RML serialization.

The owning source SHACL remains responsible for semantic graph conformance.
This comparison detects dropped or extra serialization, not graph semantics.
"""
import argparse
import json
from pathlib import Path

from rdflib import Graph, Namespace, URIRef

BFO = Namespace('http://purl.obolibrary.org/obo/')


def verify(document, graph):
    game = str(document['gamePk'])
    base = f'https://baseballontology.org/data/game/{game}/'
    prefix = base + 'runner-trajectory/'
    evidence = document['_baseballO']['runnerHistoryReconciliation']
    expected = {(prefix + row['lifetimeKey'], base + f"runner-episode/{row['atBatIndex']}/{row['runnerIndex']}")
                for row in evidence['episodeMembership']}
    placements = {(prefix + row['lifetimeKey'], row['judgmentIri'])
                  for row in evidence.get('placementAdjudications', [])}
    actual = {(str(s), str(o)) for s, o in graph.subject_objects(BFO.BFO_0000117)
              if str(s).startswith(prefix) and '/' not in str(s)[len(prefix):]}
    expected_parts = expected | placements
    if expected_parts != actual:
        raise ValueError(f'C1 part serialization differs: missing={len(expected_parts - actual)}, extra={len(actual - expected_parts)}')
    expected_wholes = {prefix + row['lifetimeKey'] for row in evidence['histories']}
    actual_wholes = {str(s) for s in graph.subjects() if str(s).startswith(prefix) and '/' not in str(s)[len(prefix):]}
    if expected_wholes != actual_wholes:
        raise ValueError('C1 whole serialization differs from source-selected inventory')
    expected_ends = {(prefix + row['lifetimeKey'] + '/temporal-interval', row['gameEndInstantIri'])
                     for row in evidence['histories'] if row.get('gameEndInstantIri')}
    actual_ends = {(str(s), str(o)) for s, o in graph.subject_objects(BFO.BFO_0000224)
                   if str(s).startswith(prefix) and str(s).endswith('/temporal-interval')}
    if expected_ends != actual_ends:
        raise ValueError('C1 game-ending boundary serialization differs from source-selected inventory')
    return dict(gamePk=game, inputSha256=evidence['inputSha256'],
                personalHistories=len(expected_wholes), episodeMemberships=len(expected),
                placementAdjudications=len(placements),
                gameEndedHistories=len(expected_ends),
                sourceToGraphMembershipVerified=True, semanticConformance='requires-owning-source-SHACL',
                populationComplete=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--context', type=Path, required=True)
    parser.add_argument('--rdf', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(json.loads(args.context.read_bytes()), Graph().parse(args.rdf)), sort_keys=True))


if __name__ == '__main__':
    main()
