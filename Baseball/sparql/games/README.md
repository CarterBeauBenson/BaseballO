# Game, team, and official queries

This family reports games by season, venue, and team; home/away splits; team
matchups; umpire and official-scorer assignments; and mapped game start/end
timestamps. It describes loaded game graphs only and does not infer standings,
wins, losses, or schedule completeness that the current mapping does not emit.

The selected processor expands the current `[-1:]` last-play iterator to every
play in the fixture. `game-timeline.rq` consequently uses the maximum mapped
end timestamp as the explicit query-layer terminal-time convention. The RML
iterator behavior remains a source-specific mapping issue to correct.
