# Field selection and de-duplication

> Correction, 2026-09-09: passages below describing the four local runner
> properties are historical and withdrawn. Use the [structural correction](../../archive/design-records/runner-structural-correction/README.md).
> Episode/agent and decision-destination paths replace the first two shortcuts;
> directive prescription and stasis boundaries remain source-evidence gaps.


Owner: `mlb-game`. All paths under `P` refer to an individual
`liveData.plays.allPlays[]` object. This is a bounded inventory of fields needed
to investigate attribution, not a proposal to map the whole response again.

**Already supplied** means present in the authoritative MLB payload, even
where the current RML omits the required assertion. **Unresolved** marks a
semantic interpretation, not a missing provider. No additional source is
needed to supply a duplicate field.

| Field / input | Selection | Meaning, identity or join scope | Mapping / missing-value boundary |
| --- | --- | --- | --- |
| `gamePk` | Identity/join-only | Game key | Reuse accepted game identity; absent key blocks evidence association. |
| `P.about.atBatIndex` | Identity/join-only | PA within game | Reuse existing PA; never join across games by index alone. |
| `P.matchup.batter.id` | Identity/join-only | Batter Person | Reuse Person and career-persistent Batter Role. Missing identity blocks batter attribution. |
| `P.runners[].details.runner.id` | Identity/join-only | Affected Person | Distinguish pinch runner from replaced Person; substitution continuity remains reviewed work. |
| Runner array position | Identity/join-only | Existing execution-only runner-record identity within PA | Not a new world-side trajectory identity or proof of continuity. |
| `P.playEvents[].index` | Identity/join-only | Event index within PA | Validate uniqueness and existence; not causal identity. |
| `P.runners[].details.playIndex` | Identity/join-only | Runner row to source event within PA | Missing, ambiguous or mixed event association cannot establish attribution. |
| `P.playEvents[].playId` | Identity/join-only | Accepted event-record identifier scope | Non-pitch events can lack it; never fabricate a pitch join. |
| `P.about.isComplete` | Already supplied | PA completion evidence | False/missing does not support terminal consequence completeness. |
| `P.result.eventType` | Already supplied | Provider result classification | Reuse accepted world-side classes where supported; string equality is not attribution. |
| `P.runners[].details.eventType` | Already supplied | Runner-row provider classification | Mixed or misleadingly broad labels occur; no positive-credit default. |
| `P.runners[].details.movementReason` | Unresolved | Provider reason token | Needs evidence for meaning and world-side referent; null is not a reason. |
| `P.runners[].movement.originBase` | Already supplied | Reported origin context | Compare with `start`; do not assume it means PA-start occupancy. Null can occur for a batter. |
| `P.runners[].movement.start` | Already supplied | Reported movement start | Accepted `hasBaserunningOriginBase` scopes a corroborated start to the particular act; it does not supply unchanged participants. Missing is not automatically HOME. |
| `P.runners[].movement.end` | Already supplied | Reported terminal base or scoring result | Candidate `hasAdjudicatedBase` links an admitted Safe Process to its first/second/third Base; it does not assert persistent entitlement. This remains owning-lane coverage debt pending review. Null does not mean out, unchanged, or score. |
| `P.runners[].movement.isOut` | Already supplied | Runner resolution evidence | True/false/null are distinct; null placeholder must not become an Out Process. |
| `P.runners[].movement.outBase` | Already supplied | Reported base associated with out | Not a safe end state or proof of physical touching. |
| `P.runners[].movement.outNumber` | Already supplied | Reported counted-out ordinal | Not an additive number of outs. Requires distinct operative resolution identity. |
| `P.runners[].details.isScoringEvent` | Already supplied | Scoring corroboration | Does not establish batter credit; reconcile with counted Run Process. |
| `P.result.rbi` | Already supplied | Provider official RBI total | Does not supply participant-level attribution for these metrics. |
| `P.runners[].details.rbi` | Already supplied | Provider official RBI flag | Different analytical scope; false does not decide every contribution policy. |
| `P.count.outs` | Already supplied | PA record's count context | Do not relabel it as pre-consequence outs. |
| `P.playEvents[].count.outs` | Already supplied | Event-local reported count | In fixture 566279 / PA 15 the terminal pitch reports 1 while runner outs are numbered 2 and 3. Review its temporal scope. |
| `P.playEvents[].startTime` | Already supplied | Event timestamp evidence | Timestamp is not the Process; missing precision blocks ordering claims that require it. |
| `P.playEvents[].endTime` | Already supplied | Event timestamp evidence | Simultaneous timestamps/indexes do not order sub-consequences. |
| `P.matchup.postOnFirst` | Already supplied | Reported post-PA runner | Not an immediate pre-result state or evidence that an unlisted runner was unchanged. |
| `P.matchup.postOnSecond` | Already supplied | Reported post-PA runner | Same scope restriction. |
| `P.matchup.postOnThird` | Already supplied | Reported post-PA runner | Same scope restriction. |
| `P.reviewDetails.isOverturned` | Already supplied | Disposition of the review summarized at PA level | Does not identify each affected runner or original decision content. |
| `P.playEvents[].reviewDetails.isOverturned` | Already supplied | Event-level review disposition | May concern a different review in the same PA; do not conflate reviews. |
| `P.result.description` | Already supplied | Narrative evidence currently used for review type, initiator and status | Preserve provenance; absent or ambiguous narrative does not prove operative runner attribution. |
| `P.playEvents[].details.call.code` | Already supplied | Pitch-call classification used by the current pitch-review path | Does not establish runner destination or out status; retain accepted classification boundaries. |
| PA-start out count and occupancy | Deterministically derivable | Existing accepted context construction | Reuse at its accepted boundary; do not silently extend to arbitrary event boundaries. |
| Immediate pre/post-consequence state | Unresolved | Participant state at a reviewed boundary | Needs world-side pattern, identity and temporal anchoring before derivation. |
| Coalesced participant trajectory | Unresolved | Multiple rows possibly describing one continuous consequence | Same runner or adjacent rows are insufficient identity evidence. |
| Attributable out count, progress, destruction, erosion | Deterministically derivable after review | Derived analytical values over complete approved RDF | No direct JSON-to-metric calculation; remain unavailable until attribution and state are resolved. |

The [resolution-link proposal](../../archive/design-records/mlb-game-resolution-award-links/resolution-links-review.md) uses the same
runner identity, event joins, result classifications, safe/scoring evidence
and terminal Base. Its forced-chain evidence includes 822693 / PA 6 and
823016 / PA 39. These are additional examples of existing fields, not a
source extension or approval of arbitrary `movement.start` state derivation.

No field is classified as genuinely additional from another source. Existing
payload coverage must be resolved in this module. Provider labels, descriptions
and units do not create ontology universals. Base tokens are categorical
institutional states; ordinal trajectory positions belong only in the reviewed
query contract and are not lengths or physical coordinates.
