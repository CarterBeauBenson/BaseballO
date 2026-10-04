# Game, team, and official queries

This family reports games by season, venue, and team; home/away splits; team
matchups; umpire and official-scorer assignments; and mapped game start/end
timestamps. It describes loaded game graphs only and does not infer standings,
wins, losses, or schedule completeness that the current mapping does not emit.

Context assembly and clock admission share the terminal-baseball selector.
It retains a genuine plate appearance even when its result label is advisory,
excludes pure administrative records, and requires corroborating Final/game-over
state. If the terminal record lacks its end time, selection fails rather than
using an earlier play. T1 withholds contradictory clock pairs instead of
inventing a replacement time. `game-timeline.rq` reads the available mapped boundaries
directly; a missing boundary is not inferred from another event.

`games-by-team-and-season` and `umpire-assignments` have exact indexed
companions for measurement, but their current timings are effectively neutral;
the operational router deliberately keeps them authoritative. `game-timeline`
also remains authoritative because terminal-time evidence is not part of the
query-index contract.
