# Field selection inventory

The standalone people endpoint widens population coverage but overlaps the
MLB-game payload. Fields marked as duplicates may be mapped here only under the
accepted reference-source ownership migration; old game RDF persists until a
separate equivalence-proven cutover.

| Field or family | Disposition | Proposed treatment |
| --- | --- | --- |
| `id` | mapped; identity/join-only | Key the Person and emit a Non-Name Identifier that designates the Person and uses the MLB person-ID Reference System. |
| `fullName` | mapped; authoritative duplicate during migration | Emit a Proper Name designating the Person with exact decoded Unicode text. |
| `nickName` | mapped; authoritative duplicate during migration | Emit a Nickname designating the Person with exact decoded Unicode text. |
| `height` | mapped; authoritative duplicate during migration | Strictly parse feet/inches, require strictly positive total inches, create the Person's Height quality and a response-versioned Measurement ICE, normalize to a decimal value, and use CCO Inch. |
| `birthDate` | mapped; authoritative duplicate during migration | Create the stable Birth Process and response-versioned Calendar Date Identifier/Day evidence; do not emit a Birth-to-Day edge. |
| `link`, `nameSlug` | identity/join-only; excluded | Request/navigation/discovery metadata only; not a world assertion or IRI source beyond the reviewed numeric ID. |
| `firstLastName`, `lastFirstName`, `nameFirstLast`, `fullFMLName`, `fullLFMName`, `boxscoreName`, `initLastName`, `lastInitName` | deterministically derived; excluded | Rendering variants do not create additional Name individuals. |
| `currentAge`, `lastPlayedDate` | deterministically derived; excluded | Derive in SPARQL/serving from accepted dates and participation history with an explicit observation time. |
| `firstName`, `middleName`, `lastName`, `useName`, `useLastName`, `nameMatrilineal`, `nameSuffix`, `nameTitle` | authoritative duplicate; blocked/unresolved | Name-part, title, preferred-use, and historical semantics are not reviewed. |
| `pronunciation` | authoritative duplicate; blocked/unresolved | A pronunciation string is neither another Proper Name nor a safely typed phonetic representation under the accepted model. |
| `weight` | authoritative duplicate; blocked/unresolved | Likely measures Mass, not CCO Weight, but the bare integer unit is unproven. Emit no Mass, measurement, value, or Pound unit. |
| `birthCity`, `birthStateProvince`, `birthCountry` | authoritative duplicate; blocked/unresolved | Free strings do not establish stable geographic entities, containment, or Birth location. |
| `batSide` | authoritative duplicate; blocked/unresolved | Persistent batting laterality/disposition and game-observed side are not yet modeled. |
| `pitchHand` | authoritative duplicate; blocked/unresolved | Bodily laterality and Pitch Act realization structure are not yet modeled. |
| `primaryPosition` | authoritative duplicate; blocked/unresolved | The target could be a customary Role, roster designation, Person classification, or presentation field. |
| `currentTeam` hydration | blocked/unresolved | Effective interval and accepted organizational-context/history pattern are absent. |
| `primaryNumber` | authoritative duplicate; blocked/unresolved | A number assignment is team/Role/interval scoped; a current string alone does not evidence its assignment act or interval. |
| `strikeZoneTop`, `strikeZoneBottom` | authoritative duplicate; blocked/unresolved | Static person values must not replace plate-appearance/pitch contextual geometry; bearer, frame, unit, and temporal scope require review. |
| `mlbDebutDate`, `draftYear` | authoritative duplicate; blocked/unresolved | Date/year alone does not identify the relevant debut participation or draft act. |
| `active`, `isPlayer`, `isVerified`, `gender` | authoritative duplicate; blocked/unresolved | Provider record/status values do not license stronger existence, occupation, verification, gender, or sex assertions. |

## Null, parsing, identity, and version policy

- Null or absent optional selected fields are valid inputs and emit no node and
  no triple.
- Before RML, the source-contract input validator quarantines a malformed
  present ID, ISO date, or height value. Post-RML SHACL validates only emitted
  RDF and cannot detect a source value the mapping omitted.
- Person IRIs use `(MLB person resource kind, provider ID)`.
- The Person's Height quality and Birth Process use stable Person-scoped IRIs.
- Response ICE IRIs use request scope and response SHA-256.
- Height Measurement ICE IRIs use Person, measurement kind, and response hash.
- Calendar Date Identifier IRIs use Person, `birthDate`, lexical date, and
  response hash.
- Name IRIs use Person, reviewed name kind, and a hash of the decoded lexical
  value; no array index is used.
- Height parsing accepts only the reviewed feet/inches grammar. Total inches is
  `(12 * feet) + inches` and must be greater than zero; no floating unit
  inference occurs.
- Text is UTF-8 decoded exactly once. The RDF literal preserves the exact
  scalar sequence; malformed replacement characters fail the proof.
