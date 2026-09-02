# Competency questions

1. Can an MLB official be represented when MLB supplies a stable person
   identifier but omits the official's name?
2. Can the official's Umpire Role and participation in the game be represented
   without inventing a name or name-bearing ICE?
3. Can a pitch-result challenge be represented when MLB records the review and
   resulting call but does not say whether the prior call was confirmed or
   overturned?
4. Can such a review retain its input and output information while leaving the
   review-outcome classification unasserted?
5. Can a Plate Appearance remain a real, incomplete Process when it contains a
   pitch but ends without a plate-appearance result because play was
   interrupted by a delay or the inning ended on a baserunning out?
6. Can an MLB rain-delay advisory identify a game-contained delay Process
   without asserting an unevidenced weather cause?

## Accepted answers recorded in conversation

- Stable MLB person identity is sufficient for the Person, Umpire Role, and
  participation assertions. A missing name causes the optional label and name
  ICE to be omitted; it does not suppress the official.
- A pitch-result challenge supports the Review Act, its challenge, the reviewed
  pitch or call, and a resulting decision ICE. Confirmed/overturned status is
  asserted only when the source states it.
- An interrupted Plate Appearance remains a Plate Appearance containing every
  evidenced pitch. It receives no fabricated terminal result. The pattern also
  covers an inning ending on a baserunning out during an otherwise incomplete
  plate appearance.
- `Status Change - Delayed: Rain` supports a Process occurring within the Game
  and an MLB advisory ICE about it. `Rain` remains provider classification
  evidence and does not by itself establish a meteorological cause.
