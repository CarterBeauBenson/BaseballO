# Statcast run and win expectancy

Status: **under review — design only**

This package isolates the genuinely additional `delta_run_exp` and
`home_win_exp` model outputs. It keeps them separate from actual Run Processes,
the Baseball Game, and the source row. A provider expectancy is an ICE produced
under a versioned model and game-state context; it is not a physical or
institutional quality inhering in a pitch.

CCO Probability Measurement ICE requires a Process/Process Aggregate
likelihood target. The ontology does not yet identify the possible home-win
outcome or remaining-inning Run aggregate needed by these fields. The graph
therefore remains blocked at those targets.

`delta_home_win_exp` and `bat_win_exp` remain deterministically derived and are
not selected for Statcast mapping. The governance artifact bucket named
`sourceIndependentMermaid` points to `source-specific-mermaid.md`.
