# Source evidence

This package is corpus-driven. It records evidence already present in the
repository's accepted MLB source reviews and executable contracts; it does not
perform a new API download or retain payload bytes.

## Current accepted model and implementation

- `Baseball/ontology/BaseballO.ttl` defines Player Role as an Occupation Role
  inhering in a Person with responsibility to participate for a particular
  Baseball Team. Its current comment says that one role individual is reused
  for each Person-Team pairing across games.
- `Baseball/sources/mlb-game/mapping/mlb-game.rml.ttl` currently keys the
  Player Role by Person and Team, has it inhere in the Person, assigns the Team
  as organizational context, and connects it to a Stasis of Role.
- The game mapping also permits a Baseball Game to realize that Player Role.
  This correctly keeps event realization separate from Stasis, but the
  Person-Team role key cannot distinguish a later return to the same Team.
- The current game Stasis has a temporal-region individual but no reviewed
  historical boundary evidence. Its existence is not proof of a complete
  tenure interval.

Acceptance of this package would therefore revise an identity policy for the
existing `PlayerRole` class. It would not create a replacement class. A later
migration must preserve game realization queries while changing the role IRI
grain only after equivalence and repeat-stint tests pass.

## Available MLB evidence families

The accepted people review records `currentTeam` as blocked because effective
interval and organizational-context history are absent. It can provide, at
most, a content-versioned snapshot when its observation time is preserved.

The accepted transactions review exposes Person, from-Team, to-Team, provider
type, `date`, `effectiveDate`, and optional `resolutionDate`. Those rows are
currently Information Content Entities. Their dates are represented by Date
Identifiers designating Days and are not process or role boundaries. Trade and
other role-changing world assertions remain blocked because exact transaction
classifications, team-scoped role identity, and source-specific evidence rules
have not been reviewed. The world-side boundary structure itself is no longer
a vocabulary gap: an evidenced start uses Gain of Role and an evidenced end
uses Loss of Role.

The game corpus contains team rosters and game participation. A roster
observation may show that a Person bore a team-scoped Player Role in connection
with that Game. It does not establish unobserved days, contractual status, or
the exact start/end of a continuous stint.

Future team-roster or personnel-history endpoints may provide wider evidence,
but they remain separate source modules and must pass their own field inventory,
Mermaid, RML, and SHACL gates. This proposal does not pre-create such a lane.

## Existing vocabulary

The accepted vocabulary supplies:

- Person (`cco:ont00001262`);
- Baseball Team (`base:BaseballTeam`);
- Player Role (`base:PlayerRole`);
- Gain of Role (`cco:ont00001194`);
- Loss of Role (`cco:ont00000613`);
- Stasis of Role (`cco:ont00000824`);
- Temporal Region (`obo:BFO_0000008`);
- Temporal Interval (`obo:BFO_0000202`);
- Calendar Date Identifier (`cco:ont00001340`);
- Day (`cco:ont00000800`);
- `inheres in` (`obo:BFO_0000197`);
- `has organizational context` (`cco:ont00001992`);
- `participates in` / `has participant`
  (`obo:BFO_0000056` / `obo:BFO_0000057`);
- `affects` (`cco:ont00001834`);
- `designates` (`cco:ont00001916`);
- `occupies temporal region` (`obo:BFO_0000199`); and
- `realizes` (`obo:BFO_0000055`).

No new ontology term is required for the candidate structural pattern. Each
Gain or Loss Process has the Person as participant, affects the exact Player
Role that begins or ends, and occupies its own Temporal Region. The Person and
Role participate in the intervening Stasis, which occupies its own Temporal
Interval. The Stasis does not realize the Role. Gain or Loss typing alone does
not license a `realizes` relation to the affected Role. The unresolved work
concerns source sufficiency, identity, exact temporal localization and
adjacency, and provenance.

## Evidence limits

- A provider record is an ICE about the world; it is not the Role, Stasis, or
  transition Process.
- Provider labels such as trade, assignment, release, or signing need exact
  reviewed semantics before they support a Role transition.
- A Calendar Date Identifier designating a Day does not establish which
  Temporal Region is occupied by a Gain or Loss, which instant bounds a Stasis
  interval, or whether those regions are exactly adjacent.
- Absence from a daily or game roster may mean no observation, not an ended
  Role.
- Acquisition time can bound a snapshot's evidence but cannot be substituted
  for the unknown beginning of the team stint.
