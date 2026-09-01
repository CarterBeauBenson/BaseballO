# Final MLB authority and transaction RML review

Status: **accepted source-independent design - executable RML still requires source-specific review**

This is the accepted source-independent review surface for the next MLB RML
implementation pass. Carter Beau Benson accepted the nineteen linked package
Mermaids on 2026-08-30 from commit
`b8c6cc76711286c979b9acb11db3c48ae7d6a581`. The archived package decisions
authorize the named ontology changes. Source-specific Mermaid approval remains
the gate before executable RML and SHACL implementation.

## Realist explanatory structure

The source record is evidence, not the center of the graph. Each admitted field
must answer the following source-independently:

- **who**: the persistent Person, Organization, or material bearer;
- **what exists**: independent continuants, Sites, and their parts;
- **why the bearer can behave as it does**: specifically dependent Qualities,
  Dispositions, Roles, and Artifact Functions;
- **what happened**: Acts and Processes with participants and agents;
- **where and when**: Sites, Fiat Points, Geospatial Positions, and Temporal
  Regions; and
- **how the source picks those entities out**: Names, Identifiers,
  Measurements, Position Descriptions, and other ICEs that designate or are
  about the world-side entities.

An ICE never substitutes for the entity, SDC, or occurrent it describes.

## Shared temporal authority

- [Canonical source-neutral Day authority](canonical-day-authority/source-independent-mermaid.md)
- Earlier Day precedes later Day, including empty Days.
- A Calendar Date Identifier designates a Day.
- A dated Process occupies its own region; that region may be a temporal part
  of the Day at the precision supported by the source.
- Game UTC timestamp, venue-local official Day, and transaction institutional
  Day remain distinct evidence. No transaction timezone is invented.

## Persistent role histories

- [Player-Team continuous stint](player-team-continuous-stint/source-independent-mermaid.md)
- [Team-Division member stint](team-division-member-stint/source-independent-mermaid.md)
- [Team-League member stint](team-league-member-stint/source-independent-mermaid.md)
- [Major League Free Agent Role](major-league-free-agent-role/source-independent-mermaid.md)

Every supported history uses the same Gain-precedes-Stasis-precedes-Loss
pattern. The bearer and exact Role participate as reviewed; each transition
affects that exact Role and occupies its own region. Stasis never realizes a
Role. Left-censored and open histories omit invented boundaries. Missing
observations do not terminate a Role.

## Grounded transaction world mappings

- [Trade](mlb-transactions-trade-code/source-independent-mermaid.md)
- [Signing](mlb-transactions-signing-codes/source-independent-mermaid.md)
- [Release, free-agency declaration, and retirement](mlb-transactions-release-retirement-codes/source-independent-mermaid.md)
- [Roster-status institutional model](baseball-roster-status-institutional-model/source-independent-mermaid.md)

The roster-status proposal contains seven proposed class IRIs: the shared Act,
Release Act and decision ICE, Free Agency Declaration Act and decision ICE,
and Retirement Declaration Act and decision ICE. It proposes no property.

## Persistent people and their SDCs

- [Batting Side Disposition](mlb-people-batting-laterality/source-independent-mermaid.md)
- [Throwing Side Disposition](mlb-people-pitching-laterality/source-independent-mermaid.md)
- [Baseball Position Description and its real cluster](mlb-people-primary-position/source-independent-mermaid.md)
- [Mass measured in pounds](mlb-people-mass-measurement/source-independent-mermaid.md)

Batting and throwing sides are real Dispositions borne by the Person and
realized only in evidenced Batter, Throw, or Pitch Acts. Left and right are
distinct particular dispositions; switch or ambidextrous evidence supports
both. A baseball position is a Descriptive ICE about the Person and a cluster
of Roles, Dispositions, and Qualities. It is never substituted for those SDCs.
Mass and Height are Person-borne Qualities; response-versioned Measurement ICEs
measure them without inventing a Measurement Process.

## Persistent venue, parts, functions, and qualities

- [Venue reference-point coordinates](mlb-venues-coordinates-crs/source-independent-mermaid.md)
- [Spectator-accommodation amount](mlb-venues-capacity/source-independent-mermaid.md)
- [Playing-surface artifact](mlb-venues-playing-surface/source-independent-mermaid.md)
- [Roof artifact](mlb-venues-roof/source-independent-mermaid.md)

The Venue persists. Its selected reference point is a real Geospatial Position
designated by WGS-84 coordinate information. A playing surface and supported
roof are Material Artifact parts of the Venue and bear existing CCO Structural
Support or Covering Artifact Functions. Seats bear Sitting Artifact Functions;
standing-room Sites do not. Capacity measures a Spectator Accommodation Amount
Quality grounded in seats and designed standing-room accommodation. Qualities
and Functions may exist while no spectator-use or baseball Process occurs.
Mutable parts and measurements remain response-scoped unless evidence supports
a Stasis or transition boundary.

## Information-only transaction families in the first pass

- [Assigned, Recalled, Optioned, Outrighted, Selected](mlb-transactions-roster-movement-codes/source-independent-mermaid.md)
- [DFA, Waiver, Suspension, Status Change, Acquired, Obtained](mlb-transactions-waiver-status-codes/source-independent-mermaid.md)

These rows retain exact nominal classification, canonical aboutness, and date
evidence. They do not create a world Act, temporary Role, or team-stint
boundary until an independent semantic anchor is reviewed.

## Source and pipeline boundary

- Each RML and SHACL file remains in its owning source module.
- Persistent Persons, Teams, Venues, Leagues, and Divisions remain in
  source-owned authority products.
- Transaction Acts remain persistent event evidence, not reusable identity
  authority.
- Cross-source history is constructed only after independent promotion.
- NiFi owns corpus tests, context construction, RML, SHACL, retry, quarantine,
  promotion, provenance, and daily replacement. Codex does not babysit runs.
- The first implementation proof is one record and then one bounded game/day;
  corpus ingestion starts only after the source-owned SHACL gate passes.

## Accepted boundary

The accepted package is **Final MLB authority and transaction RML review**,
comprising the nineteen linked design records in this document. It includes
nineteen exact proposed class IRIs: the previously listed role/status classes
plus the people and venue classes linked above. It proposes no object property.
Acceptance does not authorize Statcast work or any provider-code class not
shown here.
