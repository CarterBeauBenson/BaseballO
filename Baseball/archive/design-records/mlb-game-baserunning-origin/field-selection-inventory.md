# Bounded field selection

All inputs are supplied by the existing MLB-game source. This extends owning-
lane coverage without introducing another provider or entity identity policy.

| Field | Selection | Scope and missing behavior |
| --- | --- | --- |
| gamePk, venue.id, PA atBatIndex, runner-row position | Identity/join-only | Existing game, field, act and resolution IRIs. |
| runner.id | Identity/join-only | Existing Person; missing or ambiguous identity withholds the link. |
| details.playIndex and playEvents.index | Identity/join-only | Require a uniquely matched event within the same PA. |
| movement.isOut | Already supplied | Existing resolution branch; null placeholders have no supported resolution. |
| movement.start, movement.originBase | Already supplied | Matching first/second/third values license origin at this act's start; null, disagreement and unsupported tokens are withheld. |
| movement.end | Already supplied | Existing accepted safe destination. Reuse the Code Identifier pattern for an explicit terminal Base code as well as origin. |
| Temporal persistence or complete unchanged-runner state | Unresolved | Not supplied by the proposed origin link or absence of rows. |

Code identifiers reuse the existing venue-scoped Base and source-base-code
identifier IRIs. Their categorical first/second/third codes are not physical
coordinates or authoritative metric ordinal values.
