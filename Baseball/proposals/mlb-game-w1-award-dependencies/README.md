# W2: complete only the existing runner pattern required by W1

Draft for ontologist review. W1 remains accepted; this is a narrower dependency repair for its selected award rows, not a new meaning or a game rebuild.

## Concrete failure

NiFi executed W1's seven existing award maps for retained game 822864 / PA 54 / runner row 0. Nothing was promoted. The existing `AwardCausedAdvanceShape` rejects the candidate because the older promoted graph lacks the Runner Resolution Episode, the act's agent assertion, the record's act/episode links, and the Safe Decision's first-base referent. Its existing act, safe resolution, batter identity, field, judgment and decision remain intact. Unrelated counted-foul and base-stasis failures are separate and remain unresolved.

The original W1 package explicitly limited execution to seven award maps. It did not include these four already existing dependency maps. That omission in the proposed repair scope is ours; this is not missing MLB evidence.

## Requested decision

Permit the owning W1 worker to add the minimum missing dependency facts for W1-selected runner rows using existing `RunnerEpisodeMap`, `RunnerEpisodeAgentMap`, `RunnerEpisodeRecordMap` and `SafeDecisionDestinationMap`, in addition to W1's seven award maps. Reuse `runner_episode_evidence` unchanged and require an exact PA/runner/resolution identity match with the W1 award selection. No other PA or runner is selected by this approval.

For the reviewed PA 54 example this is eight dependency triples: four episode type/part relations, one existing `has agent` assertion, two source-record aboutness relations, and one Safe Decision aboutness relation to the existing first-base artifact. No new class, object property, identity rule, start-state stasis, personal running history, pitch or umpire act is requested. Any further missing referent remains withheld rather than broadening the repair.

## Competency questions and answers for review

- Is the batter's already evidenced Baserunning Act part of the already accepted Runner Resolution Episode pattern with its actual Safe Process? Yes, using the current row-scoped identity policy.
- Does the existing source runner identity support that act's existing `has agent` assertion? Yes; do not infer a different or unnamed runner.
- Is the completed safe judgment's destination the existing first-base artifact designated by the explicit terminal row? Yes. This is decision content, not a claim of a persistent base occupancy.
- Does completing this selected episode establish a complete inning, another runner's episode or a personal history? No.

## Source and selection inventory

The same retained input as W1: game 822864, quarantine run `3011ddc6cb194b2ea53ec644bfcc5d4e`, SHA-256 `24adfc15c105909a4e09faedeb268cab6e58e5c3b630f1b7637af60f77c57b1e`. No API acquisition is needed.

| Existing source field | Classification | Use |
| --- | --- | --- |
| Game / PA / runner-row indexes | Identity/join-only | Reuse current act, resolution, episode and record IRIs. |
| Runner ID 702616 | Already supplied | Existing act agent selection; same runner as W1. |
| `movement.isOut=false`, no origin, end `1B` | Already supplied | Existing reach resolution and Safe Decision destination selection. |
| Completed PA and venue 5325 | Already supplied | Existing decision content and first-base artifact identity. |
| W1 terminal event 5 | Identity/join-only | Preserve the accepted exact award join. |

## Bounded execution

After approval is recorded separately, run only these selected existing maps. The affected award must pass the unchanged owning award SHACL over the full base-plus-delta graph. Unrelated pre-existing graph failures remain recorded and cannot be labeled conforming. Existing transaction recovery preserves unrelated triples, and only the game's derived query index and dependent SQL are refreshed. No whole-game or corpus RML rerun.
