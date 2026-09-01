# Source evidence

## Provider and observation

Provider: MLB Stats API. Observed transiently on 2026-08-28 through official
endpoints including:

- <https://statsapi.mlb.com/api/v1/teams/147?hydrate=league,division,sport,venue>
- <https://statsapi.mlb.com/api/v1/leagues/103?hydrate=divisions>
- <https://statsapi.mlb.com/api/v1/divisions/201?hydrate=league,sport>

No raw response was retained. Future acquisition remains transient and must
record request, response, and promoted-graph hashes in the source lane.

## Observed response families

### Team

Observed fields included `id`, `name`, `season`, `venue`, `springVenue`,
`springLeague`, `allStarStatus`, `teamCode`, `fileCode`, `abbreviation`,
`teamName`, `locationName`, `firstYearOfPlay`, `league`, `division`, `sport`,
`shortName`, `franchiseName`, `clubName`, and `active`.

The existing MLB game contract already exposes the same team identity, name,
league, division, and venue family for participating teams. Those assertions
remain owned by the game lane even when the current game RML does not yet bind
every field. Wider endpoint population coverage is an operational distinction
that requires an explicit later ownership decision; it is not a new semantic
predicate.

### League

Observed fields included identity/names/codes; `seasonState`; wildcard and
split-season flags; game/team/wildcard counts; `seasonDateInfo` phase dates and
qualifier thresholds; season; divisions; sport; sort order; and active status.

Many values are season-plan assertions, not timeless qualities of the League.
The endpoint's nested season object is evidence for a season-specific plan,
but booleans and counts require a precise referent before mapping.

### Division

Observed fields included identity/names/codes; season; league; sport;
wildcard/playoff settings; sort order; and active status. The Division-to-League
connection is world-relevant, but the response nesting alone does not establish
the relation that supplies either Organization's identity. Playoff settings are
season-plan assertions and must not be attached timelessly to the Division.

## Positive and nearby negative evidence

Positive: a team object that links a stable team ID to a league ID and division
ID for the requested season supports Organization identity plus scoped
affiliation, but the same fields already occur in the authoritative game
payload and are not remapped here.

Nearby negative: a team object with `active: false` does not state whether the
Organization dissolved, suspended operations, changed identity, or is merely
excluded from the provider's current product surface.

Positive: phase boundary dates in `seasonDateInfo` support Date Identifiers in
a Baseball Season Plan.

Nearby negative: the first and last dates in the response do not prove that a
game occurred at each boundary or that the whole offseason is an occurrent
part of the competitive Baseball Season.

Ontologist decision: the Baseball Season itself is a temporally extended BFO
Process. A Plan may prescribe it, and its Baseball Games may contain intentional
Baseball Acts, without making the Season or its phases Planned Acts.

The same category rule applies to participation and agency. A League may
participate in a Season or intentionally perform an Act of Planning that
outputs a Baseball Season Plan, but the API's nesting and plan content do not
themselves evidence either Process relation, a particular Act, or its Agent.
The draft withholds all of those assertions.

`BaseballLeague` and `BaseballDivision` are therefore blocked rather than
given circular or category-invalid definitions. A Baseball Rule is a
Directive Information Content Entity, not a continuant part of an Organization.
The fact that it prescribes Games or a Season cannot serve as an Organization
parthood axiom. An accepted authority, governance, organizational-role, or
other independently grounded pattern is required before those classes are
proposed.

## Existing relation coverage

The pinned BFO/CCO vocabulary supplies `is affiliated with`, `has affiliate`,
`agent in`, `has agent`, `has participant`, `has output`, `has occurrent part`,
`occurrent part of`, `prescribes`, `prescribed by`, `has continuant part`,
`continuant part of`, `designates`, and `is about`. Availability is not
fitness: continuant parthood cannot connect a Rule ICE to an Organization, and
the unqualified affiliation properties do not express season scope. Those
claims are withheld until an accepted pattern exists. No new object property
is proposed.
