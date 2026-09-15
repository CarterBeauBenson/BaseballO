"""Review-only source/graph PA-count comparison after the focused serving proof.

Matching counts are evidence, not official-credit identity or source admission.
The report never supplies playerResults to a serving route.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--serving-proof', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    proof = json.loads(args.serving_proof.read_bytes())
    assert proof['jenaQueryPassed'] and proof['sqlExactMatch']
    mapping = json.loads((ROOT/proof['mappingProof']).read_bytes())
    raw = (ROOT/mapping['source']).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == mapping['inputSha256']
    assert proof['rdfSha256'] == mapping['rdfSha256']
    document = json.loads(raw)
    census = proof['metric']['coverage']['battingParticipation']
    plays = document['liveData']['plays']['allPlays']
    source = Counter(str(p['matchup']['batter']['id']) for p in plays)
    graph = {r['player'].rsplit('/', 1)[-1]: r['observedPlateAppearances'] for r in census['players']}
    assert census['withoutBatter'] == census['withMultipleBatters'] == 0
    assert census['observedPlateAppearances'] == len(plays)
    assert source == graph
    players, teams, substitutions = [], [], []
    for side, team in document['liveData']['boxscore']['teams'].items():
        total = 0
        for player in team['players'].values():
            identifier = str(player['person']['id'])
            official = player['stats'].get('batting', {}).get('plateAppearances')
            if official is None:
                assert identifier not in source
                continue
            assert type(official) is int and official >= 0
            total += official
            assert source[identifier] == official
            if official:
                players.append(dict(player='https://baseballontology.org/data/player/'+identifier,
                    name=player['person']['fullName'], teamId=team['team']['id'],
                    sourceOfficialPlateAppearances=official, observedGraphPlateAppearances=graph[identifier]))
        assert total == team['teamStats']['batting']['plateAppearances']
        teams.append(dict(side=side, teamId=team['team']['id'], sourceOfficialPlateAppearances=total))
    for play in plays:
        for event in play['playEvents']:
            if event.get('details', {}).get('eventType') == 'offensive_substitution':
                substitutions.append(dict(atBatIndex=play['about']['atBatIndex'], eventIndex=event['index'],
                                          count=event['count'], playerId=event.get('player', {}).get('id')))
    report = dict(status='passed-review-only-count-comparison', gamePk=mapping['gamePk'],
        source=mapping['source'], sourceSha256=mapping['inputSha256'], rdfSha256=proof['rdfSha256'],
        querySha256=proof['querySha256'], implementationSha256=proof['implementationSha256'],
        jenaQueryPassed=True, sqlExactMatch=True, observedPlateAppearances=len(plays),
        players=sorted(players, key=lambda row: row['player']), teams=teams,
        offensiveSubstitutions=substitutions, perPlayerCountsMatch=True,
        officialCreditGraphContractAdmitted=False, teamGameExposureContractAdmitted=False,
        metricScoresProduced=False, playerLeaderboardProduced=False,
        limitation='Count equality in this game does not identify official credit on substituted turns or prove selected-period team exposure.')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(observedPlateAppearances=len(plays), players=len(players),
                         perPlayerCountsMatch=True, playerLeaderboardProduced=False)))


if __name__ == '__main__':
    main()
