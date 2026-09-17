# Nineteen public metrics: implementation and release status

**Count-history follow-up:** the [complete-game repair](../benchmarks/metrics/count-history-completion-2026-09-16/README.md)
admits all 81 official PAs in game 823585 through source SHACL, B1, count
validation, canonical Jena extraction and exact SQL. It fixes no-pitch
intentional walks, the foul-tip-bunt identity lookup, terminal-review prefix
scope and already reconciled pinch-runner prefixes. Shared request calculations
preserve exact results; the dashboard now leads with the actual populated
player-leaderboard count. These proofs do not establish complete live or season
populations, and the remaining work below is still open.

**Latest diagnostic:** the [shared-blocker repair](../benchmarks/metrics/dashboard-shared-blockers-2026-09-16/README.md)
separates the now-working SQL service from player rankings. The one available
review aggregate is not a player leaderboard. It fixes PB/WP running evidence
consumption, fielder's-choice-out contact selection and virtual-ball intentional
walks, with real RML/Jena/SQL proofs. Current source admissions, complete season
references and the exact remaining attribution/defensive/review cases are
listed there. The dashboard is not yet fully populated.

Seventeen public metrics now have connected calculation and SQL serving paths.
D1's bounded defensive projection, source conformance, promotion provenance
and materializer are implemented; complete defensive populations and order
remain unproven. The two review player producers still need graph/population
integration. Connected paths do not mean seventeen populated leaderboards:
each requires complete source/graph, period, eligibility and qualification
admission. All twenty calculation kernels exist; Role Realization Breadth is
the backend-only twentieth metric and is not another public card.

The September 16 live check confirmed the August 25 NiFi refresh completed and
the API returned all 19 cards from the SQL build. The selected schedule covered
all 15 games, but six official-PA admissions were withheld and no player
leaderboard was populated. The [focused follow-up](../benchmarks/metrics/dashboard-admission-fixes-2026-09-16/README.md)
repairs zero-count pinch hitters after pitching changes/mound visits, event-level
scoring before a nonscoring batting result, and an empty strikeout record beside
an explicit safe wild-pitch advance. All six affected sources now reconcile.
Game 823826 passes current RML/source SHACL plus B1, counted-run and
runner-resolution admissions. The new NiFi request owns fresh population
validation and serving publication; those checks are not a claim that all
player histories or leaderboards are complete.

The subsequent [C1/B2 coverage repair](../benchmarks/metrics/runner-history-coverage-2026-09-16/README.md)
raises complete source histories from 2 to 8 of the 15 unchanged August 25
fixtures (292 to 360 personal histories). Game 823098 proves all 70 PA
contributions and all five scoring histories through Jena and exact SQL,
including isolated player means for six batting metrics and both run metrics.
PA-start ambiguity remains separately withheld; this developer result does not
assert that the live date range or reference season is ready.

The [subsequent record/review proof](../benchmarks/metrics/runner-records-review-subjects-2026-09-16/README.md)
raises complete source histories to **9 of 15** (363 personal histories).
Game 822773 passes RML/source SHACL with 35 histories and 83 episode links.
Canonical review extraction now follows the shared decision subject to the
pitch and its unique actual batting participation; two real affected batters
survive exact SQL retention. Substituted/ambiguous participation remains
unassigned. This closes a bounded affected-player extraction gap, not the
separate review-mechanism, complete-population or qualification gates.

| Public metric | Player producer | Remaining work before complete live results |
| --- | --- | --- |
| Plate Appearance Contribution | Implemented conditionally | Complete attributed PA inputs and selected schedules; supported independent prefixes stay separate |
| Plate Appearance Quality | Implemented conditionally | Every reference-season contribution input and independent schedule through cutoff |
| Situation-Adjusted PAQ | Implemented conditionally | Same complete season, admitted immediate base/out states and at least two reference observations per applicable state |
| Offensive Reach | Implemented conditionally | Complete selected schedules, B1, runner census, supported attribution and contact continuations |
| Help Without Advancing | Implemented conditionally | Same complete progress population; pooled applicable PA denominator |
| Runner Out Rate | Implemented conditionally | Complete runner-on-base eligibility and attributed existing-runner outs; independent changes cannot be charged to the batter |
| Runner Loss per PA | Implemented conditionally | Same complete eligibility and outcome ownership; exact direct-loss weights retained |
| Scoring Opportunity Lost | Implemented conditionally | Complete admitted PA boundaries and attributed outs; actual ends and third-out stranding retained |
| Empty Games | Implemented conditionally | Complete official PAs and positive batting/running channels; retained game count |
| Empty Game Damage | Implemented conditionally | Complete Empty Game classification and negative PA contributions; successful independent steals are assigned to their runner across PAs. Separate independent damaging episodes, unknown running ownership and interrupted turns remain gated |
| Contribution Mix | Implemented conditionally | Complete positive play/channel inventory and separate running-attempt qualification |
| Two-Strike Extension Rank | Implemented conditionally | Complete pitch/count and B1 admissions for every reference-season game, plus independent schedules through the cutoff |
| Longest Defensive Sequence | Implemented; population gated | Complete act/agent/order admission and independent roster proof |
| Defenders Involved | Implemented; population gated | Complete act/agent admission and independent roster proof; order is a separate gate |
| Scoring History Length | Implemented conditionally | Every counted scoring history, source run/roster proof and selected schedule |
| Run Contributors | Implemented conditionally | Same complete scoring histories with supported contribution ownership |
| Replay Overturn Rate | Unfinished as a player producer | Pitch-review affected-player extraction and SQL retention implemented; other subjects, mechanisms, complete population and qualification remain |
| Outcomes Changed by Review | Unfinished | Complete eligible never-reviewed decisions, decision-time legal availability, operative outcomes, affected players and separate mechanisms |
| PAQ with Tie-Breakers | Implemented; defensive population gated | Admitted contribution, two-strike and defensive inputs; complete separate season references and selected participation |

The settled meanings, minima, averages, Empty Game count, separate review
mechanisms and backend-only role handling remain unchanged. No object
properties or ontology terms were introduced.

The [September 16 serving integration](../benchmarks/metrics/defensive-paq21-adapters-2026-09-16/README.md)
connects the defensive graph inventory and exact player means to SQL, retaining
independent roster and order gates. PAQ with Tie-Breakers joins exact PA
identities, ranks Recovery across all eligible season PAs first, then ranks
the applicable PAQ-2.1 population before taking selected-period player means.
These consumers have no public evidence-submission path. NiFi now produces
the owning source's hash-bound defensive admission before promotion. The
[real D1 proof](../benchmarks/metrics/d1-defensive-mapping-2026-09-16/README.md)
verifies 20 acts and all 107 contact plays through Jena and SQL. Only 13
simple-catch plays have complete act evidence; the entire game remains
withheld for defensive player means. Partial evidence cannot shrink a ranking
denominator or fabricate a supported order.

[D1](../archive/design-records/mlb-game-defensive-acts/README.md) and
[M3/M4](../archive/design-records/mlb-game-counted-foul-completion/README.md)
were explicitly accepted and published in `e4166c1`. M3/M4 is implemented;
the [real-game proof](../benchmarks/metrics/m3-m4-mappings-2026-09-16/README.md)
closes all four named omissions and admits the complete 73-PA, 267-pitch
count history of game 824087. D1 is also implemented with the bounded proof above.

The subsequent Empty Game Damage correction stops treating a fully evidenced
successful steal as missing damage evidence. Its runner's game is not empty,
including when the steal occurs during another batter's PA. The batter gets
no steal credit, and other players' empty-game damage remains calculable.
Conflicting contact/running attribution is rejected. Unknown movements,
independent outs and interrupted turns still withhold the affected population.
Focused SQL tests compare Empty Game Damage against the Empty Games count and
retain the independent schedule requirement.

The [placement and third-out completion](../benchmarks/metrics/runner-placement-completion-2026-09-16/README.md)
closes both remaining personal-history fixture cases. All **15/15** August 25
games now reconcile **415 histories**, preserving all 409 prior selected keys.
Placement is a distinct adjudication and supplies no movement credit. Both
full-game source profiles pass Jena; Scoring History Length resolves all
15 counted runs across games 823585 and 823826 through exact SQL. The same
proof isolates four **Run Contributors attribution** cases involving excluded
fielder's choices/errors and independent passed-ball/wild-pitch running; these
are implementation coverage debt under settled policies, not missing source
records or a request for semantic approval. The linked audit lists exact PAs.

The following paragraphs retain the earlier checkpoints for comparison.

[C3's accepted identity review](../archive/design-records/mlb-game-runner-boundary-anchors/README.md)
addresses non-pitch action, replacement and placed-runner boundaries without
pitch IDs. The user accepted all three C3 questions on September 16 and the
decision was published in `06cc732` before implementation. The
[C3 implementation proof](../benchmarks/metrics/c3-runner-boundaries-2026-09-16/README.md)
raises complete source histories to **12 of 15** fixtures, with **404 personal
histories** and all earlier whole identities preserved. Game 823989 passes
RML/source SHACL and exact history admission for 40 histories; all 14 scoring
histories also survive canonical query and exact SQL retention for Scoring
History Length. At that checkpoint, zero-episode placed runners, the two
non-pitch review cases, the third-out state conflict and separate PA-start
states were explicit gaps. No ontology terms or object properties were introduced.

The new NiFi-owned review inventory retains PA-level as well as event-level
records before transient input cleanup. In game 822773, the fifth `MJ`
observation is at PA 15, so the five observed records reconcile with the
reported ABS total. The current RDF retains three resolved reviews and two
supported affected batters. This is concrete mapping coverage debt, not absent
provider evidence. Inventory counters are diagnostic and never admit scores,
review mechanisms, original-call content or eligible-decision populations.

The [upheld runner-review follow-up](../benchmarks/metrics/live-refresh-runner-reviews-2026-09-16/README.md)
accounts for the explicit final effects of both non-pitch tag reviews without
adding review RDF or assigning a mechanism. Complete personal histories now
covered **13 of 15** fixtures and **409 histories**, with all prior identities
and episode allocations preserved. Game 825042 proves all nine scoring
histories through Jena and exact SQL for both Scoring History Length and Run
Contributors. The zero-episode placed runner and third-out base-state conflict
were still withheld then; the completion above closes both. Separate PA-boundary
and review-population gates are unchanged.

The same follow-up replaces slow grouped live graph counts with equivalent
fixed-graph aggregates. All independent graph-pair identity/count checks remain.
A 200-game live batch completed source/index counts in 8.23/2.52 seconds and
matched every promotion count. This addresses the observed 30-second query
timeouts in NiFi's corpus preflight; it does not certify a complete live build.

The new Recovery producer is proven from a complete real-game input set
(79 PAs, 282 pitches) through exact SQL retention. Complete-season ranking
and selected-range means have focused integration tests. The common percentile
engine also passes exact equivalence checks for all four rank metrics and a
20,200-observation scale case without a quadratic peer join.

## Concrete release gates

The eight metric SHACL profiles are registered in the owning module's
operational `pipeline/validation-profiles.json`. Exact ownership and inventory
checks cover both that registry and the existing pinned source contract.
The registration blocker is resolved without a protected catalog or freeze
change. The [unnecessary approval request was withdrawn](../archive/design-records/mlb-game-metric-profile-registration/disposition.md).

M3/M4 implementation and its bounded count-admission proof are complete. The Q5 case in game
824087 PA 32 is repaired: a later completed affirmed pitch review no longer
hides the earlier clock strike. Strict RML also handles an absent neighboring
pitch without failing. Source evidence presence,
mapping coverage, calculation implementation and live population admission
are separate states. The remaining population gates and two unfinished review integrations must
not be described as complete or blocked solely by absent provider evidence.

NiFi owns repeatable processing, correction invalidation, promotion and serving
refresh. No routine corpus acquisition, manual rebuild or healthy-run polling
was performed for this change. Its source schedule remains unchanged.

## Contribution and season-ranking implementation

The source-owned boundary proof checks the exact existing PA-start stases,
out counts and independently reconciled C1 history membership. Serving can
therefore preserve an unchanged runner through the PA and strand that runner
at the third out without manufacturing an Out Process. No RML, ontology,
object property, semantic freeze or approval status changed.

[The corrected real-game proof](../benchmarks/metrics/contribution-mixed-plays-2026-09-15/result.json)
passes source SHACL, canonical Jena extraction and exact SQL retention for
game 566279: **79 of 79 contribution scores resolve**. Its 31 personal histories
and all PA-start boundaries reconcile. The isolated one-game player summaries
for Contribution, Runner Out Rate, Runner Loss and Opportunity Lost match SQL.
No season or public date-range schedule is fabricated by this developer proof.

The [extended proof](../benchmarks/metrics/authorized-metric-fixes-2026-09-15/README.md)
also verifies Offensive Reach and Help Without Advancing through the same
complete contribution inputs and exact SQL retention. Their positive batting
population no longer depends on classifying unrelated independent running.
Empty Games and Contribution Mix still require their separate running census.

The three formerly withheld scores are now retained: PA 12 (balk then walk)
= 1/4 for the batter; PA 23 (steal then single) = 5/4 for the batter with the
steal kept separate and the contact beginning at second; PA 40 (fielder's
choice plus error) = 0 under the accepted positive-credit exclusion.
The award proof independently checks all expected causal/normative award
members before absence of an award link can exclude another movement.

PAQ can consume the complete contribution inputs once its season is admitted.
PAQ-A separately requires a supported immediate comparison state: 77 of the
79 have one. PAs 12 and 40 still lack sufficient graph ordering for that state;
this is not a reason to suppress their known contribution values. The existing
balk record is descriptive; the adapter does not convert its text into a new
causal assertion. Independent damage/positive-running classification is also
kept separate, so complete batting inputs do not falsely certify Empty Games.

The defensive producers are now connected as described above; their complete
populations remain gated. The two review producers still require integration
of their mechanism-specific evidence and complete populations.

## Remaining numerical player reducers

`summarize_defensive_players` computes each participating defender's mean over
distinct complete resolutions. Breadth needs agents; depth additionally needs
complete supported order. Duplicate superclass representations do not count
twice, while distinct repeated throws do. `summarize_review_players` computes
affected-player rates separately by mechanism and keeps eligible never-reviewed
decisions in the dependence denominator. `summarize_paq21_players` ranks each
complete season before selecting and averaging the requested PAs. Known
inapplicability excludes a PA; unknown applicability or a missing applicable
dimension does not become zero.

These reducers require independent source/graph population proofs and complete
participation including missed team games. They have no HTTP evidence-submission
path and do not certify their own source inputs. Defensive and PAQ-2.1 SQL
consumers are implemented; the review integration and complete input
populations remain unfinished. Q6's permission to use explicit
MLB descriptions and Q7's review eligibility policy are already settled; they
must not be asked again. Any new semantic assumption needed to interpret a
particular source case must be identified concretely rather than substituted
with a claim that the provider has no defensive evidence.
