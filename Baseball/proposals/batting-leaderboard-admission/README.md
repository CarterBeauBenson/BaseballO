# B1: first batting leaderboard admission

Status: draft, not accepted. No new ontology term, object property, source
module or RML assertion is proposed. This is a named analytical source-contract
decision over existing MLB graph patterns, not a claim that a game passed it.

## Decision requested

May the following independently reconciled graph population supply official
PA qualification and applicable team-game exposure for the first batting
leaderboard, without creating an RDF statistical-credit relation?

1. Count each distinct completed batting turn through its existing PA,
   Batter Act, realized Batter Role and bearer, and the existing adjudicated
   batting-result pattern. Counted result types are Single, Double, Triple,
   Home Run, Batted Ball Out, Force Out, Grounded Into Double Play, Double Play,
   Sacrifice Fly, Sacrifice Bunt, Walk (including intentional walk), HBP,
   Fielders Choice, Error and Interference Processes. Statistical eligibility
   does not grant positive metric credit: error/FC exclusions and interference
   deferral remain in force.
2. Reconcile that exact source-to-graph membership against the unfiltered
   final source revision and each player's independently reported boxscore PA
   total, including zero totals, and both team totals. Do not substitute game
   totals for player reconciliation. Source `type=atBat`, `isComplete`,
   matching counts alone, or a generic Batter Act alone cannot admit a PA.
3. An independently verified runner-only interruption contributes no official
   PA to the batter. Preserve its existing batting participation and running
   evidence. Unknown result categories, ambiguous membership or disagreement
   block the selected population; they do not disappear from the denominator.
4. For this initial admission, require complete evidence that there was no
   offensive replacement after batting began within each counted turn. A
   replacement before the turn begins can be reconciled to its actual batter.
   A substituted turn requiring separate original/replacement official credit
   blocks the selected population. Do not transfer earlier actions to the
   final matchup, guess the credit, or create a new Role/Act identity.
5. Count applicable team games from existing game-scoped Player Role
   realization, its bearer and organizational Team context, checked against
   each final boxscore roster and the game's existing home/away Team Roles.
   A rostered player need not have batted. Count distinct game/team pairs,
   including missed batting games, team changes and both doubleheader games.
   Do not infer membership across a gap between observations. Missing exposure
   for any applicable selected game blocks qualification.
6. NiFi must verify selected-game coverage, unchanged source/graph hashes,
   owning source SHACL, per-player membership and exposure before releasing
   the population. Store proof/provenance separately from the metric facts.
   Scores and qualification counts come from authoritative RDF queries into
   SQL, never directly from source JSON. A partial set of players or games
   cannot be relabeled as the selected-period top five.

The approved 3.1 PA/team-game minimum, selected-period averages, exact
arithmetic and Empty Games count are unchanged. Complete metric-specific
scores remain required independently of qualification. B1 does not admit
TFS boundary reconstruction, percentile cohorts, defensive actions or
review-eligible populations. The first target is Offensive Reach using the
already accepted contact/award and progress-exclusion policies, followed by
its applicable dependent summaries only when their full inputs pass.

## Why explicit review is needed

Previous decisions separate actual contribution from official statistical PA
credit. They have not accepted the conditional equivalence above. The proposal
uses a bounded analytical population over existing entities; it does not claim
that generic batting participation universally equals official credit.
The repository requires a named decision before a new source/semantic query
assumption becomes executable. Until B1 is accepted, only read-only inventories
and tests of already accepted graph paths may be implemented.

See [source evidence and field selection](source-evidence.md) and the
[existing graph shapes](source-independent-mermaid.md).
