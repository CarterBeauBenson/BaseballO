# Existing fields used by the accepted overlap decision

This inventory records reuse of the accepted C3 pattern under answer 2 in
[the existing answers](../metric-repair-scope-2026-09-30/answers.md). It adds no source field or ontology term.

| Existing MLB field | Selection classification and use |
| --- | --- |
| gamePk, inning, halfInning | Identity/join-only; existing game and half scope. |
| eventType, player.id, replacedPlayer.id | Already supplied by the game source; explicit placement and replacement identities. |
| base | Already supplied; administrative boundary identity only, never proof of physical occupancy. |
| count.balls, count.strikes, count.outs | Already supplied; reconcile unchanged count and out state. |
| startTime, endTime | Already supplied; preserve reliable observed bounds. Overlap alone does not defeat independently reconciled state; no invented times. |
| runners.details.runner.id, playIndex, movement.start, movement.end | Already supplied; independently reconcile the replacement's actual movement and existing resolution episodes. |
| reviewDetails, hasReview, isOut, isScoringPlay | Already supplied; conflicting or unresolved effects remain exclusions. |

The accompanying diagram is the unchanged accepted C3 source-independent
shape. The temporal-overlap clarification changes neither its relations nor
its identity pattern. No separate replacement movement is inferred.
