# Implemented shape and retained gaps

The [generated catalog](patterns/README.md) describes the current RML maps and
their exact graph patterns. This overview summarizes those implementations;
it does not replace source-owned validation or claim complete API coverage.

| Implemented pattern | Boundary retained |
| --- | --- |
| Distinct acts, physical processes, judgments, decisions, calls, results, records, times, sites, roles and artifacts | A counted outcome alone does not establish every physical act |
| Persistent person-and-role identities; game-scoped home/away team roles | Source evidence still controls realization and temporal boundaries |
| Bunt acts from supported pitch codes or in-play bunt trajectories | A `sac_bunt` result alone is an institutional classification, not evidence of the physical act |
| D1 defensive performances with actual agents, persistent Fielder Roles and reconciled credits | Credits alone do not establish separate performances or strict order; complete defensive populations remain conditional |
| Counted ordinary fouls and foul bunts under M1/M3/M4 | Prefix counts, identity and participation must reconcile; a held two-strike ordinary foul adds no strike |
| Replay decisions, reviews and operative-outcome evidence | Particular officials, original decisions and complete eligible review populations require their own evidence |
| Runner episodes, personal histories and supported boundaries | Ambiguous or incomplete histories remain withheld; Q7 isolates the specifically approved zero-episode case |
| Explicit timer count awards and distinct extra-inning placement adjudication | No physical pitch, movement or positive running credit is inferred from an administrative placement |
| Institutional passed-ball/wild-pitch classifications and uncaught-third-strike patterns | No physical control failure or safe/out resolution is inferred solely from those labels |

The field-relative hit-coordinate pattern is disabled pending its source and
modeling decisions. Other advisory events and unhandled cases remain
field-level coverage debt, not permission to invent a class or an assertion.

See the [mapping boundaries](../sources/mlb-game/mapping/README.md#conservative-source-boundaries),
[D1 implementation](../sources/mlb-game/review/defensive-acts.md), and
[Q7 targeted addition](../sources/mlb-game/pipeline/TARGETED-HISTORY-ADDITION.md).
The [metric readiness record](../serving/METRIC-READINESS.md) separates concrete
count, runner-boundary, defense and review gaps from fixes awaiting SQL publication.

Historical fixture success belongs to its recorded mapping fingerprint and
dated evidence. Current counts come from the generated catalog; current runtime
outcomes come from the owning NiFi stage. Neither successful graph promotion nor
implemented arithmetic establishes a complete player leaderboard.
