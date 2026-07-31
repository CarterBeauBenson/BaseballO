# Game, team, and official queries

This family reports games by season, venue, and team; home/away splits; team
matchups; umpire and official-scorer assignments; and mapped game start/end
timestamps. It describes loaded game graphs only and does not infer standings,
wins, losses, or schedule completeness that the current mapping does not emit.

The execution-context builder selects the final play timestamp before RML
execution because the selected processor expands `[-1:]` to every play.
Fixture validation requires exactly that one terminal value in the RDF graph;
`game-timeline.rq` therefore reads the mapped boundary directly.
