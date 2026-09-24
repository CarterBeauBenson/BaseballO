# Game, team, and official queries

This family reports games by season, venue, and team; home/away splits; team
matchups; umpire and official-scorer assignments; and mapped game start/end
timestamps. It describes loaded game graphs only and does not infer standings,
wins, losses, or schedule completeness that the current mapping does not emit.

The execution-context builder selects the last genuine baseball record with
an end timestamp, excluding administrative records and requiring corroborating
Final/game-over source state. It does not rely on the processor's ambiguous
`[-1:]` slicing. T1 withholds contradictory clock pairs instead of inventing a
replacement time. `game-timeline.rq` reads the available mapped boundaries
directly; a missing boundary is not inferred from another event.

`games-by-team-and-season` and `umpire-assignments` have exact indexed
companions for measurement, but their current timings are effectively neutral;
the operational router deliberately keeps them authoritative. `game-timeline`
also remains authoritative because terminal-time evidence is not part of the
query-index contract.
