"""Compare M1/M2 and Q5 source-selected identities with serialized RDF.

This is a membership/serialization check, not an imperative semantic validator.
The source-owned SHACL profile constrains the meaning of the selected graph.
"""
import argparse
import json
from pathlib import Path

from rdflib import Graph, Namespace, RDF, URIRef

BASE = Namespace('https://baseballontology.org/')
BFO = Namespace('http://purl.obolibrary.org/obo/')
CCO = Namespace('https://www.commoncoreontologies.org/')


def verify(document, graph):
    root = document['_baseballO']
    evidence = root['metricMappingEvidence']
    data = f"https://baseballontology.org/data/game/{document['gamePk']}/"
    plays = document['liveData']['plays']['allPlays']
    participations = [row for play in plays for row in play['_baseballO']['batterParticipations']]
    expected_batters = {row['actIri'] for row in participations}
    actual_batters = {str(s) for s in graph.subjects(RDF.type, BASE.BatterAct)}
    if expected_batters != actual_batters:
        raise ValueError(f'Batter participation census differs: missing={len(expected_batters-actual_batters)}, extra={len(actual_batters-expected_batters)}')
    for row in participations:
        act = URIRef(row['actIri'])
        player = URIRef('https://baseballontology.org/data/player/'+row['playerId'])
        if (act, BFO.BFO_0000057, player) not in graph:
            raise ValueError(f'Batter participant identity not serialized: {act}')
        for pid in row['pitchIds']:
            for batting in graph.subjects(BFO.BFO_0000062, URIRef(data+'pitch/'+pid)):
                if (batting, RDF.type, BASE.SwingAct) in graph or (batting, RDF.type, BASE.BuntAct) in graph:
                    if (batting, BFO.BFO_0000132, act) not in graph or (batting, BFO.BFO_0000057, player) not in graph:
                        raise ValueError(f'Actual batter assignment not serialized: {batting}')
    expected_fouls = {data + f"process/strike/{e['playId']}"
                      for p in plays for e in p.get('playEvents', [])
                      if e.get('isPitch') is True and e.get('details', {}).get('call', {}).get('code') == 'F'
                      and e.get('count', {}).get('strikes') == 1}
    expected_fouls.update(data + f"process/strike/{e['playId']}" for e in evidence['countedFouls'])
    actual_fouls = {str(s) for s in graph.subjects(RDF.type, BASE.StrikeProcess)
                    if any((o, RDF.type, BASE.FoulBallProcess) in graph for o in graph.objects(s, BFO.BFO_0000062))}
    if expected_fouls != actual_fouls:
        raise ValueError(f'M1 serialization differs: missing={len(expected_fouls-actual_fouls)}, extra={len(actual_fouls-expected_fouls)}')
    expected_reviews = {data + f"review/{p['about']['atBatIndex']}/act" for p in plays if p['_baseballO'].get('hasReview') is True}
    expected_reviews.update(row['reviewIri'] for row in evidence['pitchReviews'])
    actual_reviews = {str(s) for s in graph.subjects(RDF.type, BASE.BaseballReplayReviewAct)}
    if expected_reviews != actual_reviews:
        raise ValueError(f'M2 review census differs: missing={len(expected_reviews-actual_reviews)}, extra={len(actual_reviews-expected_reviews)}')
    for row in evidence['pitchReviews']:
        required = [
            (row['reviewIri'], CCO.ont00001921, row['originalDecisionIri']),
            (row['reviewIri'], CCO.ont00001986, row['operativeDecisionIri']),
            (row['originalJudgmentIri'], RDF.type, str(BASE.ReviewedOnFieldUmpireJudgmentAct)),
            (row['originalJudgmentIri'], RDF.type, row['judgmentClassIri']),
            (row['reviewIri'], RDF.type, row['reviewClassIri']),
            (row['originalDecisionIri'], CCO.ont00001808, row['motionIri']),
            (row['operativeDecisionIri'], CCO.ont00001808, row['motionIri']),
        ]
        required.extend((row['recordIri'], CCO.ont00001808, row[k]) for k in
                        ('reviewIri', 'originalJudgmentIri', 'originalDecisionIri', 'operativeDecisionIri', 'dispositionIri', 'pitchIri'))
        for s, p, o in required:
            if (URIRef(s), p, URIRef(o)) not in graph:
                raise ValueError(f'M2 selected identity not serialized for pitch {row["playId"]}: {s} {p} {o}')
    awards = evidence.get('automaticAwards', [])
    expected_awards = {row['recordIri'] for row in awards}
    actual_awards = {str(s) for s in graph.subjects(RDF.type, BASE.BaseballEventRecord)
                     if '/event-record/count-award/' in str(s)}
    if expected_awards != actual_awards:
        raise ValueError(f'Automatic count award census differs: missing={len(expected_awards-actual_awards)}, extra={len(actual_awards-expected_awards)}')
    for row in awards:
        # Mechanical identity serialization only. Matching types, cardinalities,
        # absent fictitious pitches and order conformance belong to source SHACL.
        for key in ('processIri', 'judgmentIri', 'decisionIri'):
            if (URIRef(row['recordIri']), CCO.ont00001808, URIRef(row[key])) not in graph:
                raise ValueError(f'Automatic award identity not serialized: {row["playId"]} {key}')
    return dict(gamePk=str(document['gamePk']), inputSha256=evidence['inputSha256'],
                batterParticipations=len(participations),
                automaticCountAwards=len(awards), withheldAutomaticCountAwards=len(evidence.get('withheldAutomaticAwards', [])),
                addedCountedFouls=len(evidence['countedFouls']), allCountedFouls=len(expected_fouls),
                affirmedPitchReviews=len(evidence['pitchReviews']), allReviews=len(expected_reviews),
                sourceToGraphMembershipVerified=True, semanticConformance='requires-owning-source-SHACL',
                metricPopulationAdmitted=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--context', type=Path, required=True)
    parser.add_argument('--rdf', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(json.loads(args.context.read_bytes()), Graph().parse(args.rdf)), sort_keys=True))


if __name__ == '__main__':
    main()
