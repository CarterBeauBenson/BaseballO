# Field selection inventory

Every disposition compares the standalone people endpoint with the
authoritative MLB game payload, not merely with what the current RML emits.

| Field or family | Disposition | Consequence |
| --- | --- | --- |
| `id` | identity or join only | Reuse canonical MLB Person identity; the integer is not a Person quality. |
| `link`, `nameSlug` | identity or join only | Request/navigation values only. |
| `fullName`, `nickName`, `pronunciation` | authoritative duplicate | Present in `gameData.players.*`; complete the owning MLB-game lane if approved. |
| `firstName`, `middleName`, `lastName`, `useName`, `useLastName`, `nameMatrilineal`, `nameSuffix`, `nameTitle` | authoritative duplicate | Present in the game contract; name-part semantics remain unresolved there. |
| `firstLastName`, `lastFirstName`, `nameFirstLast`, `fullFMLName`, `fullLFMName`, `boxscoreName`, `initLastName`, `lastInitName` | deterministically derivable | Rendering variants; do not ingest as separate names. |
| `birthDate`, `birthCity`, `birthStateProvince`, `birthCountry` | authoritative duplicate | Present in the game contract; place strings still require stable geographic identity before mapping. |
| `height`, `weight` | authoritative duplicate | Present in the game contract; model Height and Mass, not provider strings or CCO Weight. |
| `batSide`, `pitchHand` | authoritative duplicate | Present in the game contract; mapping is blocked on the world-side laterality structures. |
| `primaryPosition` | authoritative duplicate | Present in the game contract; mapping is blocked until the classified referent is established. |
| `primaryNumber` | authoritative duplicate | Present in the game contract; assignment remains team/role/interval scoped. |
| `mlbDebutDate`, `draftYear` | authoritative duplicate | Present in the game contract; neither date/year alone identifies the full world-side act. |
| `strikeZoneTop`, `strikeZoneBottom` | authoritative duplicate | Present in the game contract and in pitch context; static values must not override contextual evidence. |
| `active`, `isPlayer`, `isVerified`, `gender` | authoritative duplicate | Present provider metadata; no stronger world-state or sex assertion is licensed. |
| `currentAge`, `lastPlayedDate` | deterministically derivable | Derive from accepted birth and participation history plus an observation date. |
| `currentTeam` hydration | unresolved | Potential coverage extension, but the effective interval and institutional relation are not supplied. |

## Ontology gaps, not proposed shortcuts

| Gap | Required world-side structure before mapping |
| --- | --- |
| Persistent batting laterality | Person, Batter Act, Home Plate, relevant Spatial Orientations, realization/modal account, and distinction from one plate appearance's observed side. |
| Pitching-hand laterality | Person, appropriate Bodily Components, anatomical laterality, Pitch Act realization, and identity of the classified bearer. |
| Primary position | An evidence-backed choice among Person, customary Player Role, roster designation, or another referent. |
| Current team | A temporally qualified institutional relation with an effective interval and source-correction policy. |

No new class or property IRI is proposed. No field is admitted to a standalone
people mapping by this package.
