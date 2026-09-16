"""NiFi-owned review source inventory, explicitly not semantic admission.

Keep PA-level and event-level evidence so a pitch-only scan cannot silently
drop terminal reviews. Provider codes stay provider codes. Repeated observations
are retained for later identity reconciliation, never declared distinct Acts.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def inventory(raw: bytes, game_pk: str):
    doc=json.loads(raw)
    if str(doc.get('gamePk'))!=str(game_pk):raise ValueError('Review inventory game identity mismatch')
    plays=doc.get('liveData',{}).get('plays',{}).get('allPlays')
    if not isinstance(plays,list):raise ValueError('Review inventory requires the full play array')
    observations=[];issues=[]
    for pi,play in enumerate(plays):
        candidates=[(f'/liveData/plays/allPlays/{pi}',play,play.get('about',{}).get('hasReview'))]
        candidates.extend((f'/liveData/plays/allPlays/{pi}/playEvents/{ei}',event,
            event.get('details',{}).get('hasReview')) for ei,event in enumerate(play.get('playEvents',[])))
        for pointer,record,flag in candidates:
            details=record.get('reviewDetails')
            if details is None and flag is not True:continue
            if not isinstance(details,dict):
                issues.append(dict(pointer=pointer,code='REVIEW_FLAG_WITHOUT_DETAILS'))
                details={}
            observations.append(dict(pointer=pointer,atBatIndex=play.get('about',{}).get('atBatIndex'),
                eventIndex=record.get('index'),playId=record.get('playId'),isPitch=record.get('isPitch'),
                sourceHasReview=flag,reviewDetails=details,
                resultDescription=record.get('result',{}).get('description'),
                eventCall=record.get('details',{}).get('call'),
                reportedBatterId=play.get('matchup',{}).get('batter',{}).get('id')))
    counts=Counter((str(r['reviewDetails'].get('reviewType','unknown')),
        'pending' if r['reviewDetails'].get('inProgress') is True else
        'overturned' if r['reviewDetails'].get('isOverturned') is True else
        'affirmed' if r['reviewDetails'].get('isOverturned') is False else 'unknown') for r in observations)
    return dict(artifactType='baseballo-mlb-game-review-source-inventory',contractVersion=1,
        gamePk=str(game_pk),sourceSha256=hashlib.sha256(raw).hexdigest(),
        implementationSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        status='diagnostic',metricPopulationAdmitted=False,graphConformanceAssessed=False,
        observations=observations,issues=issues,
        observationCounts=[dict(providerCode=c,outcome=o,count=n) for (c,o),n in sorted(counts.items())],
        reportedFinalCounters={k:doc.get('gameData',{}).get(k) for k in ('review','absChallenges')},
        limitations=['Observations are not reconciled review identities.',
            'Provider codes do not establish an RDF mechanism or eligible-decision population.',
            'Reported players are not automatically affected players.',
            'Final counters do not establish decision-time challenge availability.'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--game-pk',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.input.resolve()==args.output.resolve():raise ValueError('Source bytes must remain immutable')
    result=inventory(args.input.read_bytes(),args.game_pk)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    temporary=args.output.with_suffix(args.output.suffix+'.tmp')
    if temporary.resolve()==args.input.resolve():raise ValueError('Source bytes must remain immutable')
    temporary.write_text(json.dumps(result,ensure_ascii=True,indent=2)+'\n',encoding='utf-8')
    temporary.replace(args.output)
    print(json.dumps(dict(status=result['status'],observations=len(result['observations']),issues=len(result['issues']))))


if __name__=='__main__':main()
