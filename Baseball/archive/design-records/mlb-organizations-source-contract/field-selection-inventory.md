# Field selection inventory

This inventory applies to the dedicated organizations endpoint responses. A
field marked as an authoritative duplicate is still eligible for temporary
reference-graph population because the accepted ownership migration requires
backfill and equivalence before future game-lane cutover.

## Team response

| Field or family | Disposition | Proposed treatment |
| --- | --- | --- |
| `id` | mapped; identity/join-only | Key the Baseball Team IRI and emit an MLB team Non-Name Identifier that designates it and uses the MLB team-ID Reference System. Do not treat the integer as a quality. |
| `name` | mapped; authoritative duplicate during migration | Emit one Proper Name with exact decoded Unicode text designating the Team. Existing game RDF remains. |
| nested `league.id`, `league.name` | mapped identity/name; authoritative duplicate | Identify and name a generic CCO Organization using the MLB league-ID Reference System. Emit no Team-to-League relation. |
| nested `division.id`, `division.name` | mapped identity/name; authoritative duplicate | Identify and name a generic CCO Organization using the MLB division-ID Reference System. Emit no Team-to-Division relation. |
| `season` | mapped identity scope; identity/join-only | Emit the scoped season-code identifier only when the response also supplies the reviewed league-season context. Never attach the value as a timeless Team property. |
| `venue.id`, `venue.name` | authoritative duplicate; different owner | Do not map in this module. Preserve only as request/equivalence evidence; `mlb-venues` owns venue reference facts. |
| `link`, nested `*.link` | identity/join-only; excluded | Request/navigation metadata only. |
| `sport.id`, `sport.name` | authoritative duplicate; request validation | Validate the baseball request scope; emit no additional domain assertion. |
| `teamName`, `shortName`, `franchiseName`, `clubName`, `locationName` | blocked/unresolved | Potential names or presentation strings whose name kind, official scope, and history are not established. |
| `teamCode`, `fileCode`, `abbreviation` | blocked/unresolved | Provider code/reference systems and temporal stability are not yet reviewed. |
| `springVenue`, `springLeague` | blocked/unresolved | Seasonal affiliation and venue context require a reviewed historical pattern. |
| `allStarStatus`, `firstYearOfPlay`, `active` | blocked/unresolved | Do not infer status, founding, existence, dissolution, or identity continuity from provider metadata. |

## League response

| Field or family | Disposition | Proposed treatment |
| --- | --- | --- |
| `id` | mapped; identity/join-only | Key a generic CCO Organization and emit its MLB league identifier/reference-system pattern. |
| `name` | mapped; authoritative duplicate during migration | Emit a Proper Name designating that Organization. |
| `season`, `seasonId` | mapped; identity/join-only | Together with league ID, key a Baseball Season and Baseball Season Plan and emit the season-code identifier. |
| `seasonDateInfo.*Date` | mapped; genuinely additional | For every valid non-null date, emit a Plan-part Calendar Date Identifier, date value, designated Day, and a field-key identifier using the MLB season-date-field Reference System. |
| `regularSeasonStartDate` + `regularSeasonEndDate` | mapped phase identity | When both are valid and non-null, key the regular-season Phase by `(plan, regular-season)`; the Plan prescribes it and it is an occurrent part of the Season. |
| `postSeasonStartDate` + `postSeasonEndDate` | mapped phase identity | When both are valid and non-null, key the postseason Phase by `(plan, postseason)` with the same two relations. |
| other date keys including preseason, spring, half-season, all-star, season-wide, and offseason dates | mapped only as Plan date evidence | Preserve as keyed Date Identifiers and Days. Do not create additional Phase individuals or boundary relations without review. |
| nested `divisions[].id`, `divisions[].name` | mapped identity/name; duplicate or wider coverage | Identify and name generic CCO Organizations. Emit no League-to-Division relation. |
| `divisions[]` membership/nesting | blocked/unresolved | Does not license a timeless or historically scoped affiliation edge. |
| `link`, nested `*.link` | identity/join-only; excluded | Request/navigation metadata only. |
| `sport` | authoritative duplicate; request validation | Validate source scope only. |
| `abbreviation`, `nameShort`, `orgCode`, `sortOrder` | blocked/unresolved | Presentation or code semantics and histories are not established. |
| `seasonState`, `active` | blocked/unresolved | Provider record state does not establish Organization or Season world state. |
| wildcard/split-season/playoff booleans | blocked/unresolved | A boolean does not identify the Rule or prescribed format it purports to summarize. |
| game/team/wildcard counts | blocked/unresolved | Planned versus actual target and counting grain are not established. |
| qualifier plate appearances/outs pitched | blocked/unresolved | Rule, statistical denominator, and unit require separate modeling. |
| configuration flags and presentation ordering | blocked/unresolved | No research claim is approved. |

## Division response

| Field or family | Disposition | Proposed treatment |
| --- | --- | --- |
| `id` | mapped; identity/join-only | Key a generic CCO Organization and emit its MLB division identifier/reference-system pattern. |
| `name` | mapped; authoritative duplicate during migration | Emit a Proper Name designating that Organization. |
| nested `league.id`, `league.name` | mapped identity/name; authoritative duplicate | Identify and name the League Organization. Emit no Division-to-League relation. |
| `season` | identity/join-only | Scope the response and joins; do not attach it as a timeless Division property. |
| `link`, nested `*.link` | identity/join-only; excluded | Request/navigation metadata only. |
| `sport` | authoritative duplicate; request validation | Validate source scope only. |
| `league` nesting | blocked/unresolved | The historically scoped institutional relation is not represented by an accepted executable pattern. |
| `hasWildcard`, `numPlayoffTeams` | blocked/unresolved | These are season-plan claims whose rule and target are not modeled. |
| `nameShort`, `abbreviation`, `sortOrder`, `active` | blocked/unresolved | Presentation/code/status semantics and histories are not established. |

## Derived and excluded values

| Value | Disposition | Consequence |
| --- | --- | --- |
| Display labels assembled from location, club, or short names | deterministically derivable | Build only in a serving/UI layer from accepted names; do not create additional RDF names. |
| Division-to-League pairs inferred from co-nesting | deterministically derivable but semantically blocked | May be inspected as evidence, but are not promoted as an affiliation relation. |
| Endpoint links and array indexes | identity/join-only or mechanical | Never become world assertions or identity components. |

## Null, identity, and version policy

- Null or absent selected fields are valid inputs and emit no node and no
  triple.
- Before RML, the source-contract input validator quarantines malformed present
  IDs or dates. Post-RML SHACL validates only emitted RDF and must not be
  represented as proof that every present source value was mapped.
- Team, league, and division world IRIs use `(MLB resource kind, provider ID)`.
- Season and Plan IRIs use `(MLB league ID, season code)`.
- Phase IRIs use `(Plan IRI, reviewed phase key)`.
- Response ICE IRIs use endpoint family, request scope, and response SHA-256.
- Date Identifier IRIs include Plan, field key, lexical date, and response hash
  so source revisions are not overwritten.
- Proper Name IRIs include designated entity, name kind, and a hash of the
  exact decoded lexical value. The literal itself is not repaired or folded.
- No IRI uses an array index.
