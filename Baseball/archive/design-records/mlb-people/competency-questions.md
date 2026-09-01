# Competency questions

1. Which stable Person does an MLB person identifier designate?
2. Which person assertions are already present in the authoritative MLB game
   payload, even when the current game RML does not yet emit them?
3. Would a standalone people lane add semantic evidence, or only population
   coverage and a different refresh cadence?
4. What Height and Mass Qualities inhere in the Person, and which Measurement
   ICEs directly bear their values and use their units?
5. Which Birth process brought forth the Person, and which Date Identifier
   designates the reported day?
6. What Person, Bodily Components, Spatial Orientations, Home Plate, and Batter
   Acts constitute the world-side account of persistent batting laterality?
7. What anatomical and spatial structure distinguishes pitching-hand
   laterality, and what Pitch Acts may realize the relevant disposition?
8. Does `primaryPosition` classify a Person, a customary Player Role, a roster
   designation, or some other entity?
9. What temporal interval and institutional relation would make `currentTeam`
   true rather than merely current at acquisition time?
10. Can every accented name survive an exact UTF-8 round trip?

Negative tests:

- duplicate people fields do not become new assertions in a second source
  graph merely because a standalone endpoint exposes them;
- `gender: M` does not assert CCO Male Sex;
- `active: false` does not assert death, retirement, or loss of every Player
  Role;
- `currentAge` and `lastPlayedDate` are not ingested when accepted historical
  data determines them;
- `S` is not treated as a third physical side, and no laterality ICE replaces
  the missing world-side structure;
- `primaryPosition` is not asserted as a realized game role; and
- `Eugenio Suárez` never appears with a replacement character or mojibake.
