# Batting queries

This family covers complete plate-appearance outcome distributions, player
plate appearances, home runs by venue, extra-base hits, total bases, multi-hit
games, three-true-outcome totals, and hitless games. Results are derived from
mapped result individuals, their explicit specific classes, adjudication acts,
`BatterAct` participation, and plate-appearance containment. A query counts the
result rather than its record, judgment, or decision; no totals are stored
during ingestion.

All nine batting queries now have exact authoritative/indexed companions across
the eight-game corpus and are selected as indexed routes by the reviewed
runner. Eight are positive-evidence aggregations. `hitless-games-by-player` is
the exception: its absence claim is accepted only after every selected per-game
index passes current-manifest checks and complete `PlateAppearanceFact` and
`HitFact` equivalence. Canonical queries remain authoritative and unchanged.
