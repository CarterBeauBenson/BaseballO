# Existing graph shapes for B1

Review only. Every solid edge is an accepted BFO/CCO relation. No new domain
predicate, class or identity is proposed. Analytical selection and counts are
not new RDF relations. The source-specific proof must preserve these paths.

```mermaid
flowchart LR
  pa[Plate Appearance] -->|has occurrent part — BFO_0000117| act[Batter Act]
  act -->|realizes — BFO_0000055| br[Batter Role]
  br -->|inheres in — BFO_0000197| person[Player]
  result[Recognized batting-result Process] -->|occurrent part of — BFO_0000132| pa
  judgment[Baseball Adjudication Act] -->|occurrent part of — BFO_0000132| result
  judgment -->|has output — ont00001986| decision[Baseball Decision ICE]
  decision -->|is about — ont00001808| result
  record[Baseball Event Record] -->|is about — ont00001808| result
  record -->|is about — ont00001808| judgment
  record -->|is about — ont00001808| decision
```

The query may follow the existing inverse `occurrent part of` direction from
the Batter Act to its PA. No inference of official credit follows solely from
this diagram. B1's independent source and population conditions are essential.

```mermaid
flowchart LR
  game[Baseball Game] -->|realizes — BFO_0000055| pr[Player Role]
  pr -->|inheres in — BFO_0000197| person[Player]
  pr -->|has organizational context — ont00001992| team[Baseball Team]
  tr[Home or Away Team Role] -->|inheres in — BFO_0000197| team
  tr -->|realized in — BFO_0000054| game
```

Each game is checked separately. The query does not infer a person's missing
historical team membership from adjacent games or turn a stasis into a role
realization. Boxscore-roster equality and selected-game completeness remain
independent proof obligations.
