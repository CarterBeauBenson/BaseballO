# Complete batting progress and Empty Games

The accepted E1, B1, A1/B2 and metric policies now have conditional live player
producers for Offensive Reach, Hidden Help Rate and Empty Games. No ontology,
RML or identity policy changed. Source expectations remain validation inputs;
all metric facts come from the canonical promoted-RDF query.

`runner-resolution-admission.py` binds the complete final runner census to the
owning `runner-resolution-admission.ttl` SHACL profile. It checks each existing
resolution, act, episode, player, PA, outcome and supported base endpoints.
Missing or extra resolutions and contradictory participant/destination evidence
cannot admit a population. Source revision, RDF, implementation, shapes and
report hashes remain bound to the promotion marker. The SQL table stores only
that proof provenance. NiFi runs it before promotion in the existing source
SHACL stage; it is independent of the counted-run and official-PA admissions.

Serving additionally requires complete selected schedules and independently
reconciled official PA assignment and roster exposure. An explicit pinch-runner
replacement between two other rostered people does not change the batter.
B1 still checks the exact single-Batter-Act graph, player totals and team totals;
it continues to withhold unresolved multi-batter statistical assignments.

Contact-play membership, normative awards and independent steal attempts are
the currently supported contribution channels. The accepted error, fielder's
choice and catcher-interference exclusions apply to batting progress. Steals
never benefit the batter, but a runner's positive independent contribution
can prevent their own Empty Game when they have at least one official PA.
Unknown positive channels withhold the population. An unlinked out beside
positive progress, or repeated resolutions in one attributed consequence,
requires complete supported coalescence before it can score. Safe progress
before a terminal out is never retained just to fill a card.

The existing SPARQL kernels count reached participants, pool Hidden Help's
applicable PA numerator/denominator, and identify Empty Games. Player rows
publish exact range means for Reach and Help and game counts for Empty Games.
The existing automatic PA minimum and graph-scoped player names apply. A known
empty Help denominator has no rate; it is distinct from an incomplete score.

The whole-game proof covers all 73 PAs and 90 runner resolutions in game
824087. The public date-range request remains withheld without independent
schedule admission. This does not declare the deployed range, other attribution
channels, TFS, defensive metrics or season-reference percentiles complete.
