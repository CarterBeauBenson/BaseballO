# Source evidence

## Provider surface

Provider: MLB Stats API. The accepted source review observed the official
endpoint families represented by examples such as:

- <https://statsapi.mlb.com/api/v1/teams/147?hydrate=league,division,sport,venue>
- <https://statsapi.mlb.com/api/v1/leagues/103?hydrate=divisions>
- <https://statsapi.mlb.com/api/v1/divisions/201?hydrate=league,sport>

Season-scoped acquisition will use the equivalent collection or singular
requests with an explicit season request parameter. The exact request URI and
parameters belong in the provenance manifest. No response JSON is retained by
this proposal.

Observed team responses contain provider identity, `name`, season, league,
division, venue, sport, alternate names/codes, and provider status fields.
Observed league responses additionally expose `seasonDateInfo`, season-format
flags, counts, qualifier values, and division objects. Observed division
responses expose provider identity/name, league and sport objects, season, and
format/presentation fields.

## Existing MLB-game overlap and accepted ownership

The MLB live-game payload already contains participating team identities,
names, league IDs, division IDs, and venue IDs. That is semantic overlap even
where current game RML coverage is incomplete. The accepted
`mlb-reference-source-ownership` decision assigns future team, league,
division, and season reference facts to this detachable module while retaining
canonical identity links in `mlb-game`.

Consequently, the initial organizations load is a population and equivalence
stage, not permission to delete prior game RDF. The old and new graphs may
temporarily contain equivalent identifier/name facts. Only a coordinated,
separately validated cutover may stop future duplicate emission from the game
lane.

## Evidence-to-claim analysis

| Evidence | Claim supported | Nearby claim not supported |
| --- | --- | --- |
| A provider resource with `id` and `name` | A provider identifier and Proper Name designate an Organization. | The integer is an intrinsic Organization quality or globally meaningful without its Reference System. |
| Team, league, and division objects in one response | The response is about each identified Organization. | Their nesting by itself establishes a timeless or season-scoped affiliation relation. |
| League ID plus season code | A stable source scope for one League-season Season and Plan identity. | The League is thereby an Agent or participant in the Season Process. |
| Named `seasonDateInfo.*Date` fields | Plan-part Calendar Date Identifiers with field-key provenance designate Days. | A game occurred on each Day, the Process occupies the whole Day, or a Day is directly a Phase boundary under an unreviewed relation. |
| Complete regular-season or postseason start/end pair | Evidence for the provider's named game-containing Phase in that Season Plan. | Preseason, offseason, all-star break, or half-season fields are automatically Baseball Season Phases. |
| `active`, format flags, and counts | Provider record content useful for later investigation. | Organizational existence, dissolution, implemented rules, or a timeless world-state assertion. |

## Accepted vocabulary available to this contract

The accepted ontology supplies Baseball Team, generic CCO Organization,
Baseball Season, Baseball Season Phase, Baseball Season Plan, Descriptive
Information Content Entity, Non-Name Identifier, Proper Name, Calendar Date
Identifier, Reference System, and Day. It also supplies `is about`,
`designates`, `uses reference system`, `has continuant part`, `prescribes`,
and `occurrent part of`.

No new universal or object property is needed for the solid shape. The
availability of generic affiliation properties is not evidence that those
unqualified properties can carry the required historical scope.

## Operational evidence contract

The source response is transient. Before RML, a source-contract input validator
checks every present selected ID and date and quarantines malformed values.
Null or absent optional values remain valid inputs and emit nothing. This
payload check is distinct from post-RML source SHACL: SHACL validates only the
cardinality, datatype, value, and edge structure of RDF that RML emitted and
cannot detect a malformed source field that RML silently omitted.

Before successful raw deletion, the future lane must retain request time and
URI, HTTP status, response SHA-256, mapping version, input-validation result,
graph hash, SHACL report, promotion target, and promotion outcome. World
entities use canonical provider-kind identities. The generic response ICE uses
a content/version identity. Array positions never participate in an IRI.
