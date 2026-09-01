# Ownership inventory

| Fact family | Accepted owner | Boundary |
| --- | --- | --- |
| Games, innings, plate appearances, pitches, contacts, baserunning, adjudications, and game-scoped roles | `mlb-game` | Event facts and their provenance remain in the game lane. |
| Canonical team, person, and venue links required by game events | `mlb-game` | Links remain usable when a reference module is disconnected. |
| Team, league, division, and season reference facts | `mlb-organizations` | Exact semantic coverage remains limited by accepted and future source designs. |
| Person identity, names, and other accepted descriptive facts | `mlb-people` | Game-event participation remains owned by `mlb-game`. |
| Venue identity, names, locations, and accepted physical facts | `mlb-venues` | Game occurrence and event facts remain owned by `mlb-game`. |
| Transaction records and source-proven transaction processes | `mlb-transactions` | Transaction types still marked unresolved remain information-layer records only. |
| Cross-source joins and analytical products | triple-store/SPARQL derived layer | No source RML or source SHACL crosses module boundaries. |
| Existing promoted game RDF | persistent authoritative record | Not deleted or rewritten by this ownership decision. |
| Future game-reference cutover | coordinated migration | Populate reference graphs, update scoped queries, rebuild derived products, and prove equivalence before removing duplicate future assertions. |
