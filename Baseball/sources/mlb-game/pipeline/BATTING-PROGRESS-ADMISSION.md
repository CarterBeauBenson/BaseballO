# Complete batting progress and Empty Games

The accepted E1, B1, A1/B2 and metric policies now have conditional live player
producers for Offensive Reach, Hidden Help Rate, Empty Games and Contribution
Mix. No ontology,
RML or identity policy changed. Source expectations remain validation inputs;
all metric facts come from the canonical promoted-RDF query.

`runner-resolution-admission.py` binds the complete final runner census to the
owning `runner-resolution-admission.ttl` SHACL profile. It checks each existing
resolution, act, episode, player, PA, outcome, supported base endpoints and
the existing Steal Attempt typing for the six mapped steal/caught-stealing
event types. Missing or spurious Steal Attempt typing fails the source-bound
shape. This does not by itself assert analytical independence.
Missing or extra resolutions and contradictory participant/destination evidence
cannot admit a population. Source revision, RDF, implementation, shapes and
report hashes remain bound to the promotion marker. The SQL table stores only
that proof provenance. NiFi runs it before promotion in the existing source
SHACL stage; it is independent of the counted-run and official-PA admissions.

An all-null strikeout runner record does not automatically describe a second
movement or an out. A bounded case is now reconciled when the same batter has
exactly one explicit safe wild-pitch/passed-ball companion at the same third
strike, the final result is not an out, and the post-state independently puts
that batter on first. The census retains the empty record's hash and companion
index. SHACL requires the existing Uncaught Third Strike judgment/decision
pattern, the actual safe movement, and absence of an invented extra running act.
Missing, contradictory, partial or reviewed cases remain unresolved. This
source-record distinction supplies neither batting credit nor an independent
contribution channel.

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

B2 contact continuations now feed all four player producers. Multiple
resolutions must belong to one existing C1 personal Process with exact member
coverage, the same contact and a complete same-PA portion. A nonbranching
forward sequence of explicit segment origins and Safe/Run/Out destinations
supplies one original-to-terminal result. A terminal Out removes all earlier
safe credit; surviving multisegment progress counts the runner once and the
play once per channel. Missing whole membership, disconnected or branching
segments, reverse progress and independent-channel mixing remain withheld.
The traversal creates no RDF temporal assertion or new identity. Its retained
trace names every existing resolution, episode and personal Process.

The [real six-movement proof](../../../benchmarks/metrics/contact-progress-2026-09-15/README.md)
reproduces the accepted Offensive Reach of two through canonical Jena extraction
and SQL. This replaces the earlier example-only query with the shared producer.

The existing SPARQL kernels count reached participants, pool Hidden Help's
applicable PA numerator/denominator, and identify Empty Games. Player rows
publish exact range means for Reach and Help and game counts for Empty Games.
The existing automatic PA minimum and graph-scoped player names apply. A known
empty Help denominator has no rate; it is distinct from an incomplete score.

Contribution Mix uses the same common admissions and then requires a complete
independent-running participation inventory. Distinct positive contact/award
plays count once in each applicable batting channel; an independent positive
episode counts once for its runner. Multiple beneficiaries cannot inflate the
batter-other channel. All distinct supported independent attempts, including
nonpositive attempts, enter the separate participation count. A strikeout with
a runner caught stealing is withheld because the accepted hit-and-run decision
does not let those outcomes alone establish strategy or responsibility.
Unattributed non-batter outs also withhold that participation census.

Exact selected-period channel counts feed the existing normalized entropy
formula. No daily entropy scores are averaged and no exact fraction is
fabricated for logarithms. Players with no positive contributions have a known
empty entropy denominator. Zero-PA players with positive independent running
remain eligible through the accepted running minimum; the UI applies batting
OR running qualification using the separate complete participation counts.

The whole-game proof covers all 73 PAs and 90 runner resolutions in game
824087. The public date-range request remains withheld without independent
schedule admission. This does not declare the deployed range, other attribution
channels, TFS, defensive metrics or season-reference percentiles complete.
