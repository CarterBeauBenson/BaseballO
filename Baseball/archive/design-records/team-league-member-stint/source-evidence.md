# Source evidence

This is a corpus-driven design package based on the repository's accepted MLB
organizations review. It adds no API payload.

## Provider evidence already recorded

The accepted organizations source review records Team responses with canonical
Team identity, a season request/context value, and nested League identity/name.
League responses also carry provider identity, season data, and Division
objects. The accepted source-specific contract maps the involved Organizations
but intentionally emits no Team-to-League relation because historical scope
was unresolved.

The existing de-duplication inventory marks nested Team `league.id` and
`league.name` as authoritative duplicates during migration from MLB-game
reference data. Their identity/name assertions belong to the organizations
authority lane. The membership fact is distinct mapping-coverage debt; another
provider exposing the same pair does not make it a new assertion type.

League ID plus season code currently scopes a Baseball Season and Baseball
Season Plan. That keying decision is useful context, but neither the Plan nor
the Season proves that the Team bears a Member Role, that the League is an
Agent, or that the League participates in the Season.

## Existing vocabulary

The candidate shape reuses only:

- Baseball Team (`base:BaseballTeam`);
- generic CCO Organization (`cco:ont00001180`) for the League;
- Organization Member Role (`cco:ont00000175`);
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
- `designates` (`cco:ont00001916`); and
- `occupies temporal region` (`obo:BFO_0000199`).

No new class or property is needed for this candidate structure. The open
issues are evidential, temporal, and identity-related. When a boundary is
supported, Gain or Loss has the Team as participant, affects the exact Member
Role, and occupies its own Temporal Region. The Team and Role participate in
the intervening Stasis, which occupies its own Temporal Interval. The Stasis
does not realize the Role. Gain or Loss typing alone does not license a
`realizes` relation to the affected Role.

## Evidence still required

- A corpus audit demonstrating whether the season parameter changes the Team's
  nested League historically.
- Coverage for Teams that change League, cease operation, return, or appear in
  more than one competition context.
- A reviewed continuity rule across seasons and offseasons.
- A boundary policy for Day-level evidence that localizes Gain/Loss Temporal
  Regions and relates them to the Stasis interval without assuming exact
  adjacency, including open/censored intervals and corrections.
- Independent evidence for Team-League membership rather than an inference
  solely through Division membership.

The resulting world-side Role history may persist in an authority graph after
transient payload deletion only after those gates are answered and the
source-specific Mermaid/RML/SHACL sequence is separately approved.
