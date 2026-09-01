# Field selection inventory

Every observed field family has one review disposition. A family row applies
to the equivalent nested object members unless a narrower row overrides it.

## Team fields

| Field or family | Disposition | Treatment |
| --- | --- | --- |
| `id` | identity or join only | Reuse the canonical MLB team identity policy; do not treat the integer as a team quality. |
| `name`, `teamName` | authoritative duplicate | Already present in the MLB game source for participating teams; use an existing Proper Name pattern only if a later ownership migration is accepted. |
| `shortName`, `franchiseName`, `clubName`, `locationName` | unresolved | Potentially useful names, but their official/preferred scopes and change histories are not established. |
| `teamCode`, `fileCode`, `abbreviation` | unresolved | Presentation and code systems; no analytical need or stable scope yet proven. |
| `link` fields | identity or join only | Request/navigation metadata; never a domain assertion. |
| `season` | identity or join only | Scopes the response and joins a proposed Baseball Season; it is not itself a Team property. |
| `league.id` | authoritative duplicate | Already present on participating teams in the authoritative MLB game payload even where current RML coverage is incomplete; complete the owning lane only after temporal review. |
| `division.id` | authoritative duplicate | Already present on participating teams in the authoritative MLB game payload even where current RML coverage is incomplete; complete the owning lane only after temporal review. |
| `venue.id` | authoritative duplicate | Existing MLB game data links the participating team and venue; a general home-venue relation still needs temporal review. |
| `springVenue.id`, `springLeague.id` | unresolved | Potentially useful seasonal affiliations, but the effective interval and relation kind are not explicit. |
| `sport.id` | authoritative duplicate | BaseballO and the endpoint already constrain this lane to baseball; preserve only for request validation. |
| `allStarStatus` | unresolved | Provider status code with no established world-side referent or temporal scope. |
| `firstYearOfPlay` | unresolved | Does not establish founding, first game, uninterrupted operation, or organizational identity continuity. |
| `active` | unresolved | Provider record status; does not establish existence or dissolution. |

## League fields

| Field or family | Disposition | Treatment |
| --- | --- | --- |
| `id` | identity or join only | Canonical identity for Baseball League. |
| `name` | authoritative duplicate | Already nested in participating-team league objects in the MLB game payload. |
| `abbreviation`, `nameShort`, `orgCode` | unresolved | Code/name status and history not yet established. |
| `season` | identity or join only | Identifies the season-plan scope. |
| `divisions[]` | deterministically derivable | Division-to-league pairs for represented seasons follow from simultaneous team league/division objects in the game corpus; zero-team or broader coverage remains a later ownership question. |
| `sport` | authoritative duplicate | Request validation only. |
| `seasonDateInfo.*Date` | genuinely additional | Date Identifiers that are parts of a Baseball Season Plan; exact phase mapping must match named boundaries. |
| `seasonState` | unresolved | Provider state classification; acquisition-time and transition semantics are not documented. |
| `hasWildCard`, `hasSplitSeason`, `hasPlayoffPoints` | unresolved | Potential plan facts; boolean columns do not identify the rule or prescribed process. |
| `numGames`, `numTeams`, `numWildcardTeams` | unresolved | Season-scoped planned/actual distinction and counting target are not explicit. |
| `qualifierPlateAppearances`, `qualifierOutsPitched` | unresolved | Useful plan thresholds, but their rule, statistic denominator, and unit must be modeled before ingestion. |
| `conferencesInUse`, `divisionsInUse`, `sortOrder` | unresolved | Provider organization/presentation configuration, not yet a research claim. |
| `active` | unresolved | Provider status only. |

## Division fields

| Field or family | Disposition | Treatment |
| --- | --- | --- |
| `id` | identity or join only | Canonical identity for Baseball Division. |
| `name` | authoritative duplicate | Already nested in participating-team division objects in the MLB game payload. |
| `league.id` | deterministically derivable | Derive from the simultaneous league and division objects on authoritative game-team records for the same season. |
| `season` | identity or join only | Scopes affiliations/settings to Baseball Season. |
| `sport` | authoritative duplicate | Request validation only. |
| `hasWildcard`, `numPlayoffTeams` | unresolved | Season Plan/rule assertions; do not attach timelessly to the Division. |
| `nameShort`, `abbreviation`, `sortOrder` | unresolved | Presentation/code metadata with no DSQ requirement yet. |
| `active` | unresolved | Provider status only. |

## Proposed ontology vocabulary

| Class | Direct parent | Purpose |
| --- | --- | --- |
| `BaseballSeason` | BFO Process | A game-containing Process institutionally delimited by a Baseball Rule, without inferring an Organization participant or Agent. |
| `BaseballSeasonPhase` | BFO Process | A game-containing Process that is an occurrent part of a Baseball Season. |
| `BaseballSeasonPlan` | CCO Plan | The Directive ICE that prescribes a Baseball Season and its phases. |

No new object property is required.

`BaseballLeague` and `BaseballDivision` are unresolved and are not proposed.
The observed identifiers and nesting do not supply independently grounded
Organization differentiae. A Baseball Rule ICE cannot be used as a continuant
part of an Organization, and no unreviewed authority or governance relation is
substituted for that invalid parthood.

The unqualified CCO affiliation properties are intentionally absent from the
candidate axioms. The raw team links remain useful evidence, but they cannot be
promoted as timeless assertions or repaired by adding "during season" to a
diagram label.
