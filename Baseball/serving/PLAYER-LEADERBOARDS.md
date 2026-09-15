# Player leaderboards

The [accepted display and qualification decision](../archive/design-records/metric-leaderboard-qualification-2026-09-14/user-decision.md)
requires names and metric values for the top five qualified players, automatic
loading on page entry and date changes, and a complete list on card selection.

The page loads its restored date selection once after the catalog arrives.
Range changes immediately invalidate old scores/downloads and cancel requests;
400 ms of quiet input starts one shared refresh. Invalid or reversed custom
dates wait for correction. Card selection reuses that response.

The server's `playerLeaderboard` presentation adapter applies the accepted
batting minimum: nearest whole number of `31 * teamGames / 10`, with half
values rounded upward. This gives 3 PA for one team game, 16 for five, 22 for
seven and 502 for 162. The denominator is the player's applicable team-game
exposure throughout the selected range, including games the player missed;
it must not be replaced with games in which the player appeared. Incomplete
schedule/team exposure cannot lower the minimum.

The server sorts qualifying rational player scores by exact integer cross multiplication.
Metrics whose existing catalog says higher is worse use ascending order;
others use descending order, explicitly labeled. Equal exact values share
a competition rank; player IRI deterministically orders ties. Cards show at
most five rows, and the full list preserves all qualified players. Rounding
is only for display. A one-PA high score is excluded even on a one-game day.
Contribution Mix retains exact channel counts and evaluates and orders its
logarithmic scores approximately, before display rounding. Equal numerical
entropy evaluations share a rank; channel permutations and proportional counts
preserve ties. This does not turn logarithmic results into exact fractions.

## Serving interface and admission boundary

`playerLeaderboard` consumes only trusted serving results. It does not read
source payloads, infer completeness, average partial plays, or calculate a
new player score. The HTTP request allowlist still rejects evidence,
`playerResults`, arbitrary graphs and completeness declarations.

An admitted adapter must supply `playerPopulationComplete: true` and a
`playerResults` array for the complete applicable player score population.
Each row must carry the metric ID, player IRI, available exact metric value,
matching start/end dates and game set, complete participation evidence and
team-game count. Batting metrics also require independently admitted official
PA counts. Optional `playerLabel` is display text only.
Rows must be unique by player. Missing, conflicting or out-of-scope evidence
withholds the ranking. These interface flags serialize an independently
established admission result; setting a flag is not an admission procedure.
Complete reference populations remain required for PAQ before this display
minimum is applied.

The normalized `leaderboard` output contains qualification policy, status,
message, gap codes and every ranked row. Qualification removes low-PA rows
only after complete scores and participation have been admitted. An empty
qualified population is distinct from unavailable player scores. Current
individual Walk/HBP and run-history results remain inspectable separately.

## Still blocked

Run Construction Depth and Run Construction Breadth now have live player
producers. NiFi validates the
complete counted-run census and game roster against the final source before
promotion. SQL independently checks selected schedule coverage and requires a
complete C1 history for every counted run. Breadth additionally requires every
advance's supported contribution channel, including explicitly excluded
error/FC/interference batting progress. Only then does it emit scorer means
and complete player results. Non-scoring games remain in each player's team
exposure. Pinch runners need no inferred PA count or batting minimum.

Offensive Reach, Hidden Help Rate, Empty Games and Contribution Mix also have conditional player
producers. They require separate complete runner-resolution admission, B1
official PA counts and complete selected schedules. Supported contact, award
and independent-steal channels preserve the accepted batting exclusions and
independent running's effect on Empty Games. Unknown contribution channels or
unresolved consequence coalescence withhold the complete population. See the
[source/serving contract](../sources/mlb-game/pipeline/BATTING-PROGRESS-ADMISSION.md).

Accepted B2 contact continuations now reach these four producers through exact
C1 membership and nonbranching segment reconciliation. Several safe advances
count a surviving runner once; a terminal out removes intermediate credit.
The real six-movement example yields Reach 2 and exact RDF/SQL agreement in
the [continuation proof](../benchmarks/metrics/contact-progress-2026-09-15/README.md).

Contribution Mix additionally requires a complete independent-attempt census.
It pools exact positive play/channel counts, counts nonpositive running
attempts separately for qualification, and includes zero-PA runners. Known
empty entropy denominators yield no score; ambiguous strikeout/running-out
strategy and unattributed runner outs withhold the population. Six public
metrics now have conditional player producers; thirteen remain unfinished.

Other metric player producers remain unfinished. The isolated browser
fixtures are UI tests, not live baseball data. A deployed build must pass the
new admission stage and materialize its proof; an older graph or proof cannot
be assumed to satisfy this contract.

1. Complete player aggregates and their full applicable game/PA/run populations
   must be supplied through the accepted source-to-SQL lifecycle. Partial award
   consequences or a subset of scoring histories do not qualify. All thirteen
   reference-game scoring histories now reconcile; this is separate from
   complete selected-range admission.
2. Complete selected-period participation and team-game exposure must be
   established, including absent games and applicable multi-team history.
   Missing graphs cannot silently shrink qualification denominators.
3. The [September 15 thresholds](../archive/design-records/metric-completion-decisions-2026-09-15/user-decision.md)
   are now accepted and implemented in `web/leaderboard-qualification.json`.
   Defensive, run-construction, independent-running and review summaries use
   their eligible observation counts; Recovery Quality and PAQ-2.1 require
   both the existing PA minimum and their applicable-observation minimum.
   Participation must still be complete. No minimum is relaxed to fill a card.
   The [follow-up decision](../archive/design-records/metric-completion-decisions-2026-09-15/followup-user-decision.md)
   qualifies Contribution Path Diversity through **either** the batting or
   independent-running minimum, including zero-PA runners. This OR rule is
   implemented without changing the other metrics' qualification rules.
4. Affected-player review attribution is already accepted. Review cards now
   display separate traditional-replay and ball/strike leaderboard groups,
   with no pooled denominator or combined player rank. The trusted producer
   must supply each row's supported `mechanism`, or separate complete results
   in `byMechanism`. Source/graph population production remains unfinished.

The public participation text names PAs, runs, defensive resolutions or review
decisions. It does not expose ontology Role terminology. The same player may
appear in both review groups, each with its own qualification and rank.

## Contribution Mix serving rows

The trusted producer supplies `aggregate: {kind: "channel_entropy",
channelCounts: [batterSelf, batterOther, runnerSelf]}` for the complete selected
period. Count each positive play once per channel before pooling. The server
computes the existing normalized Shannon entropy from these exact nonnegative
integer counts. It rejects a fraction-valued mean or an empty positive-channel
population; averaging daily entropy scores would change the metric.

Each row additionally supplies the independently established
`independentRunningEpisodes` count alongside `plateAppearances`, complete
participation, date scope and applicable team-game exposure. Both counts must
be known; zero is distinct from missing. Positive running channel counts are
not the full eligible running population. The card shows the minimum actually
met. Scores carry `value: null`, `approximateValue`, and exact `channelCounts`;
both the preview and expanded table support this representation.

Source-proof recovery and corpus refresh remain separate prerequisites
described in [production readiness](../infra/PRODUCTION-READINESS.md).
