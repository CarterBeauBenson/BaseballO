# Source evidence

The accepted people inventories show `primaryPosition` in both the standalone
people endpoint and the authoritative MLB game payload. The observed family
contains code, name, type, and abbreviation content. It does not identify an
actual Player Act or prove that the description held for a complete career.

The ontologist selected the Football Ontology pattern. In that ontology,
`SoccerPositionDescription` is a Descriptive ICE about a player bearing a
tactical Role, player Disposition, or Quality; position-specific descriptions
specialize that information class. BaseballO reuses the pattern without
importing Football Ontology classes or copying soccer-specific semantics.

BaseballO already supplies persistent Batter, Pitcher, Catcher, and Fielder
Roles and their realization Acts. The accepted people decisions add Batting
Side and Throwing Side Dispositions. A generic Baseball Fielding Disposition
fills the remaining source-independent real-world cluster need. No API response
was retained or newly downloaded for this proposal.
