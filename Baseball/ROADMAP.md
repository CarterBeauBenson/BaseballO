# BaseballO roadmap

This is the ordered continuation plan. Current metric gaps and the last verified
publication are in [metric readiness](serving/METRIC-READINESS.md). Runtime
queues and build progress belong to NiFi's owner records, not this work queue.
The [previous roadmap](archive/operational-history/2026-09-23/ROADMAP.md) is
retained as history; its completed setup tasks and superseded design questions
are not instructions to repeat that work.

## Fixed architecture and scope

```text
Authorized source ingestion: API -> RML -> source SHACL -> authoritative Fuseki
Metric serving: existing RDF -> SPARQL and calculations in NiFi -> prepared SQL -> UI
```

Authoritative RDF is persistent. Reviewed game query indexes and SQL products
are derived and replaceable. Seven detachable MLB source modules own acquisition,
validation, promotion, retry, quarantine and provenance. Cross-source work begins
at the triple store. The dashboard's SQL owner is independent of source ingestion,
the legacy report builder and authority SQL.

Metric, performance and UI work starts from existing promoted RDF. A missing
input is a precisely recorded gap. An approved source addition preserves unrelated
RDF; a full RDF rebuild requires explicit authorization. The September 17 batch's
permission is not a standing rebuild instruction.

## 1. Complete the nineteen metrics: execution plan

Updated October 5, 2026. The measured starting publication remains
`20261005T031625Z-dashboard-5c27e45118a5` (October 5 at 03:30 UTC).
This section supersedes the older metric work lists and pending-publication
statements in the historical readiness notes. It is the single continuation
plan; use [metric readiness](serving/METRIC-READINESS.md) for dated measurements
and [the gap register](sparql/metrics/gap-register.json) for accepted meanings.

### Starting point and finish line

All 2,429 regular-season games and rosters are present, and the selected schedule
is complete. The recorded authorized RML backlog is clear: 754 selected history
cases complete, no pending inspections or recorded repair failures. That closes
that execution backlog, not every metric's evidence requirements. The current
full-season dashboard has five populated cards and fourteen without rankings;
none reports a complete population. Successful SQL publication is not completion.

The delivery target is all nineteen full-season player metrics, with correct
selected-range values, automatic top fives, names, qualification and working
details. Every applicable observation must be accounted for. A genuinely
inapplicable observation is distinct from an unknown one; an empty qualifying
population must be established rather than manufactured. If a required fact
cannot be supported under accepted meanings, that metric remains explicitly
blocked and the overall nineteen-metric goal stays open. A documented blocker
or an operationally successful build does not satisfy this finish line.

Preserve the settled decisions: selected-period averages except Empty Games as
a count; no appearance minimum for that count, including zero totals; nearest
whole-number 3.1 PA per team game for batting rates/averages; the accepted other
participation minima; exact fractions with display-only rounding; separate
review mechanisms; and backend-only Role Realization Breadth. Contribution Mix
retains its accepted pooled channel calculation. Percentiles use the complete
eligible regular-season reference through the reporting cutoff, never just the
displayed subset. Do not reopen these choices or lower thresholds to fill cards.

### Execution order and dependencies

Start with M0 and M1, then M2 and M3. M4 and M5 are independent offensive work.
M6 and M7 must also be completed, but cannot hold up publication of supported
offense. M8 runs separately for each reference family as its own inputs become
complete. M9 applies at every publication and again to the finished season.
NiFi retains the existing shared memory limit; these are work streams, not an
instruction to launch additional simultaneous heavy workers or new source lanes.

| Work | Depends on | Component owner | Completion evidence |
| --- | --- | --- | --- |
| M0: classify every exclusion | Current immutable publication | Existing dashboard build diagnostics | Every withheld player/game/metric has a specific cause, affected identity and repair owner |
| M1: official PA participation | M0 | MLB admission evidence, player projection | Every eligible player's PA census resolved; no unexplained null PA records |
| M2: progress and Empty Games | M1 plus affected progress facts | SPARQL, metric inputs, player projection | Complete progress/classification/channel products for applicable player-games |
| M3: contribution, outs and erosion | M1 plus affected boundary/resolution facts | SPARQL, contribution inputs, existing source evidence owner | Complete attributed PA scores and independent running losses |
| M4: scoring histories | M0; M2 attribution for contributor breadth | Run queries and scoring-history reducers | Every counted run has its supported history and contributors |
| M5: two-strike histories | M1, pitch/count evidence | Existing count admission and recovery reducer | Every PA classified for applicability; complete eligible pitch histories |
| M6: defensive acts and players | M0, accepted defensive evidence | Defensive admission, SPARQL and player projection | Complete relevant act/agent populations, independently of chronology |
| M7: review player products | M0, accepted review evidence | Review queries, reducers and SQL player products | Both review metrics wired through both mechanisms with correct denominators |
| M8: four season references | Per-family dependencies below | Reference products and SQL owner | Complete current-cutoff rank and player products for all four families |
| M9: publication, performance and UI | Each completed family; finally M1-M8 | Dashboard SQL owner and web interface | Published full-season results, exact details and bounded response times |

### M0. Classify exclusions once, using the owning evidence

Extend the existing build diagnostics instead of adding a release gate or a
second validation framework. Retain the game, PA/run/review/player identity,
reason and the relevant query/proof/product identities with each exclusion.
Group failures by shared cause and repair that cause across its affected set.
Use these distinct dispositions:

- Current evidence exists but the reader/publication did not consume it.
- A proof is absent or stale while the promoted graph and an appropriate retained
  source census are available: run the existing source-owned check on that graph.
- Accepted graph facts exist but SPARQL joins, calculation or SQL projection omit
  or misattribute them: repair the analytical component.
- A specific accepted fact is actually absent from the graph: identify the source
  witness and the exact existing mapping/approval for an additive repair.
- The fact or its meaning is unsupported: identify the exact evidence or named
  semantic decision still needed. Research factual questions before asking.

A retired local RDF export, missing proof file, withheld whole-game admission
and absent authoritative triple are different findings. Never translate one
into another automatically. Diagnosis starts from terminal NiFi evidence and
prepared SQL; bounded RDF queries answer specific unresolved questions. Do not
run a manual corpus-wide semantic validation pass.

### M1. Repair official PA participation first

There are 1,160 unknown player-game PA records across 236 games, affecting 629
players. Of these, **789 records across 15 games and 433 players have no individual
admission in published SQL**. Their existing evidence-worker checkpoints report
`retained-rdf-unavailable`, mostly from September 29. Diagnose this path first:

`824921, 824922, 824929, 824943, 824954, 824955, 824990, 824998, 825013,
825017, 825020, 825030, 825069, 825086, 825098`.

Compare each current promotion, retained independent census, proof receipt and
published product. Reuse the existing-graph admission path where supported;
remove any operational dependence on a retired local export. Do not infer a
complete source census solely from whatever rows a query returns. If a retained
witness is genuinely absent, record exactly what is absent before considering
any targeted source work. No blanket source reacquisition or RML rerun follows.

Then resolve the remaining 371 unknown rows by their recorded cause: substituted
batters, completed-result selection, player conformance/count mismatch, source
reconciliation and PA-inventory failure. Representative starting cases are
822701, 822702, 822760, 822780, 822800, 823565, 824295 and 824807. Apply the
already accepted PA-credit and substitution decisions. A roster proves who
participated; it does not by itself prove official PA credit. Verified zero PA
must remain different from unknown PA, and running eligibility remains separate.

Owners: `sources/mlb-game/pipeline/admission-evidence*.py`, retained batting and
player-participation admissions, `serving/player_ranges.py:qualification`, and
the dashboard builder's individual-proof handoff. Repair selected records and
refresh only their affected SQL partitions. Complete this item when all 1,160
records have the correct supported counts or an established inapplicable status.
Any unresolved blocker keeps this item open and identifies the exact next action.

October 5 execution: the admission queue now prioritizes the fifteen missing
individual proofs before routine maintenance, with bounded attempts. The
retained single-batter adapter now recognizes the post-T1 producer actually
used by season promotions. It still requires complete single-batter membership,
reconciled totals and unchanged B1 SHACL. Source censuses for 822760 and 824921
now reach that existing check; this is not yet a claim of new runtime admissions.

An additional concrete case is 822701, PA 69: `other_out` records a different
runner's third out at home, with a 2-0 count and no ball in play. The batter's
turn is interrupted, not a completed official PA. The current interruption
whitelist omits this provider code. Apply the existing B1 interrupted-turn
criteria, retaining every structural and boxscore check; do not count the turn
or use this observation to admit other `other_out` outcomes indiscriminately.

### M2. Complete progress, Empty Games and contribution channels

After M1, address the independent progress exclusions: Offensive Reach currently
has 1,487 excluded player-game rows across 1,094 games; Help Without Advancing has
1,046 across 838. Empty Games has 404 classification exclusions across 324 games.
Contribution Mix has 5,783 channel exclusions across 1,643 games. These overlap
and must not be added together as distinct games or players.

Trace `suite-evidence.rq` and the attribution/movement queries into
`batting_progress_evidence`, `contact_progress_path`, `binary_help_inputs`, and
`player_ranges.project`. Reconcile supported same-play continuations, award
links, substituted batters and independent movements. Bind uncertainty only to
the players actually affected when those identities are supported. Keep the
fallback when they are not. Do not silently omit an unresolved PA.

Preserve accepted error/FC progress exclusion, independent runner credit,
confirmed hit-and-run treatment, one contribution per play/channel, and actual
runner states. For Empty Games, a supported qualifying positive can establish
that the game was not empty; establishing that no qualifying positive occurred
requires the complete applicable census. No-PA games are ineligible for the count.
Publish the four independent products as each completes; they do not need
season percentiles or complete defensive populations.

October 5 diagnosis: game 822679, PA 65 has a first-to-second runner movement
whose record says `Balk`, without structured balk attribution. The RML selector
only handles a final PA result of `balk`; the checked-in game 566279, PA 12
independently demonstrates a balk before a later walk. The concrete
[BK1 proposal](proposals/mlb-game-balk-runner-attribution/README.md) requests
the narrow event/runner selection and additive repair. Its named approval is
pending. Do not substitute literal matching in SPARQL or SQL for that pattern.

### M3. Complete PA contribution, runner loss and damage

The contribution projection excludes 11,360 player-game rows across 1,848 games
apart from the common PA-credit exclusions. Whole-game boundary evidence is
withheld in 1,233 games; runner-resolution evidence in nine. Distinguish the
536 missing/stale boundary-proof cases from actual boundary or history defects.
Use existing per-PA evidence where it certifies that PA; a failure elsewhere in
the game must not automatically erase its supported result.

Reconcile immediate pre-consequence origins, actual ending states, operative
outs, award attribution, supported overlapping intervals, replacement/placement
acts and independent events. Use existing accepted meanings for actual-end-state
erosion, stranded runners at the third out, shared independent outs and confirmed
failed hit-and-runs. Do not infer strategy from a strikeout/caught-stealing pair
alone, invent timestamps, or credit independent progress to the batter.

Owners: boundary/resolution admission, `runner_boundary_states`,
`contribution_game_inputs`, `contribution_players` and the prepared player
projection. Complete Plate Appearance Contribution, Runner Out Rate, Runner Loss
per PA and Scoring Opportunity Lost. Finish Empty Game Damage after M2 supplies
classification, including every applicable independent negative running episode
once. Its current 4,917 damage exclusions across 1,464 games need exact underlying
causes, not one blanket damage flag.

October 5 diagnosis also separates outdated source expectations from missing
RDF. `pa-boundary-admission.py:prove` always prefers the promotion's original
boundary census to an available later source witness. In 824218, the individual
proof retains the old PA 5 review failure while the newer whole-game boundary
check does not. Reconcile this evidence handoff using the current, hash-bound
source census and unchanged PA SHACL. Preserve original provenance and successful
checks; do not rebuild runner histories merely because that reader used an older
census. Remaining replacement and zero-episode failures still need their own
actual source/graph diagnosis.

### M4. Finish both scoring-history metrics

Scoring History Length has 200 excluded player-game records across 44 games;
Run Contributors has 1,608 across 897. Only two games have withheld whole-game
run admission. That mismatch makes it necessary to inspect the analytical path,
not assume another large source-ingestion problem.

Reconcile each counted run to one personal history and its runner. Depth counts
supported state changes; contributor breadth counts distinct supported offensive
contributors, including the scoring runner's own contributions. Preserve their
separate requirements so an unknown contributor does not invalidate a known
history length. Examine 822685 for depth, 822682 for breadth and the existing
824295 run-census diagnostic first, then apply each generic repair to its bucket.
Exit when every eligible scoring history and contributor set is accounted for
in the current selected-range player aggregates.

### M5. Finish two-strike eligibility and pitch histories

The published count admissions are 857 admitted and 1,572 withheld. The latter
include 905 missing/stale-proof flags and 431 mapping-coverage flags; codes can
overlap. Read the current producer reports before treating either as missing
RDF. Confirm that the approved foul, substitution, review, automatic-count and
no-pitch-award fixes are consumed by the count query and reducer.

Diagnose examples 823812 (proof), 824218 (coverage), 822755 (count/order), 822754
(nonpitch count event), 824533 (completed result), and 822748 (empty count history).
Keep an inapplicable PA separate from a missing applicable history, and exclude
the terminal pitch from the accepted extension count. Reuse supported event
sequence evidence without inventing strict timestamp order. Prepare this family
independently of contribution and defense; its reference can publish first.

### M6. Resolve the actual defensive population failures

All 2,429 published defensive admissions are withheld: 1,592 carry missing/stale
proof flags, and 837 carry incomplete-population flags. There are also 481
conformance issue occurrences. These are proof outcomes, not evidence that the
MLB provider lacks all defensive facts.

First reconcile the latest D1/Q6 additions and their scoped reports with the
full-population admission reader. A successful scoped addition cannot certify
a whole game, but a retired receipt must not conceal current facts. Examine
823486 (proof), 823244 (population), and 823649 (conformance), using the recorded
expected/observed act and agent identities to locate the exact loss.

Then correct accepted field/throw/catch/tag selection, graph joins, duplicate
identity or player projection defects in their owning component. Preserve the
complete applicable resolution census. Do not fabricate unobserved acts from
an outcome label or count only the successfully mapped subset.

**Defensive Acts is the accepted distinct-act count, not ordered chain depth.**
Its current kernel already counts overlapping distinct acts; missing chronology
must not become a prerequisite again. Defenders Involved counts distinct agents.
Reuse accepted persistent roles internally without exposing role machinery in
the UI. Complete these two products and the applicable defensive input to
PAQ with Tie-Breakers. Any truly unsupported act identity is a named semantic
or evidence blocker, not an excuse to block independent offensive work.

### M7. Implement both review player products end to end

This is unfinished integration, not just delayed validation: the prepared-range
reader currently returns `REVIEW_PLAYER_POPULATION` for both public review IDs.
The reducers and pitch-review subject extraction exist, but do not supply a
complete player population. Implement the missing query-to-product-to-reader
path instead of retrying that hard-coded unavailable result.

Inventory existing accepted RDF for completed traditional reviews and ball/strike
challenges separately: reviewed decision and subject, affected player, mechanism,
initial and operative outcome, and completion disposition. Cover supported
nonpitch subjects too. The affected player is not automatically the challenger
or final batter. Deduplicate the reviewed decision at the accepted grain.

Replay Overturn Rate needs the complete eligible completed-review denominator.
Outcomes Changed by Review additionally needs eligible decisions that were never
reviewed, decision-time availability and evidence that review changed the
operative outcome. Do not substitute one denominator for the other. For ABS,
MLB's [official documentation](https://baseballsavant.mlb.com/abs-metrics-documentation)
requires an adverse called pitch and an available challenge, excluding
position-player pitching and technical outages. This source was checked October
4; it informs the evidence inventory and does not license inventing missing
historical availability. Consult the [official replay rules](https://www.mlb.com/glossary/rules/replay-review)
for traditional reviewability; preserve already accepted modeling decisions.

Use `review_player_evidence`, `summarize_review_players`, the existing review
policies, SQL game/player products and separate mechanism leaderboards. Trace
unrepresented requirements through existing retained source evidence before
claiming source absence. If a genuinely new modeled assertion is required,
prepare that exact named decision while finishing independently supported
review work. Do not silently redefine these metrics or enable a new Statcast
source module as a shortcut.

### M8. Prepare the four complete season reference products

| Reference metric | Required completed inputs |
| --- | --- |
| Plate Appearance Quality (`paq-2`) | M1 and M3 |
| Situation-Adjusted PAQ (`paq-a`) | M1, M3 and supported immediate base/out cohorts |
| Two-Strike Extension Rank (`recovery-quality`) | M1 and M5 |
| PAQ with Tie-Breakers (`paq-2.1`) | M1, M3, M5 and M6; retain its separate applicability population |

The measured publication contains only one early-cutoff recovery player
reference and no full-season reference product for these four cards. The October
5 implementation accepts a complete set of individual B1 admissions: all players,
the full PA inventory and an exact match to the RDF roster. It prepares the
affected contribution/recovery inputs from retained RDF query results in SQL,
without rewriting the whole-game proof. Count, boundary, resolution and defense
requirements remain independent. Individual proof changes refresh the affected
season references; input changes refresh the affected player partition.

This path still needs NiFi publication and complete family inputs. Published
game 824302 currently has the complete individual batting census and admitted
boundaries despite a withheld whole-game batting proof. Other games must satisfy
the same requirements; the reference never shrinks to passing players or games.

Once each family is complete, NiFi calculates its exact ranks and prepares the
matching player aggregates for the reporting cutoff. Preserve ties, PAQ-A's
accepted small-cohort behavior, PAQ-2.1 applicability and its lexicographic
comparison. Changing display dates must select/pool retained results without
recomputing a season or changing the intended comparison population. Diagnose
missing input, missing prepared reference and wrong cutoff/key as separate errors.

### M9. Publish incrementally and verify the actual user experience

The existing Dashboard SQL owner refreshes affected game/family/player/reference
products and publishes its immutable candidate atomically. Reuse unchanged RDF
bindings and calculated products. A presentation or scheduler edit must not
invalidate semantic admissions or trigger RML. Keep the report builder, authority
SQL and source lanes independent. Record the code version and build actually
serving the page; code on `dev` alone does not prove runtime deployment.

Investigate broad invalidation and empty rebuilds using existing progress timings:
the latest build reused all 2,444 active game products, yet spent about 241 seconds
on snapshot capture and 543 seconds on input refresh. Remove unnecessary work
through scoped identities/event handling and supported proof reuse, without
relabeling stale evidence as current. Keep original proof hashes and outcomes.
This performance task must not delay a correct partial publication.

For each released family, compare the full-season card and detail results from
the same publication. At the end check the default season, a month, a week, an
arbitrary cross-month range and a range with no eligible observations. Verify:

- Automatic loading and top five by the selected period, with real player names;
  clicking a card shows the same ranking, values, denominator and qualification.
- Correct means/counts, ties, full-range exposure (including team changes), zero
  PA versus unknown PA, count metrics without rate minima, and separated review
  mechanisms. No silent date narrowing or missing-observation deletion.
- Clear distinctions among incomplete evidence, not applicable, no qualifiers
  and a real zero. Public explanations use baseball concepts; detailed backend
  evidence remains available for diagnosis without cluttering cards.
- Full-season and custom-range requests read prepared SQL only. The last observed
  custom range took 22.4 seconds; inspect its query plan and move expensive
  reconstruction/decoding into the existing NiFi build. Engineering target:
  at most 2 seconds for warm data responses and 5 seconds for a first load on
  this host. Record actual end-to-end timings and remaining misses.
- Browser interaction, not just HTTP success. Browser automation was unavailable
  at the last check, so visual/card-click verification remains an explicit task.
- One owning-stage incremental refresh and failure/retry demonstrates that new
  results appear without losing the last usable publication or replaying sources.

Use a focused regression for each substantive repaired cause, including a case
that must remain unresolved. NiFi runs the applicable existing conformance and
publication checks asynchronously. Do not add a giant manual final validation
suite or restore GitHub checks. Finish with live qualified-player counts,
remaining exclusions and matching card/detail results for every metric.

### Nineteen-card accountability

These are full-season baseline ranked-player counts, not targets to manufacture.
A high player count is not proof of correct coverage; one qualified player is
not completion of a season population.

| Public metric | Current ranked players | Closing work |
| --- | ---: | --- |
| Plate Appearance Contribution | 0 | M1, M3, M9 |
| Plate Appearance Quality | 0 | M1, M3, M8, M9 |
| Situation-Adjusted PAQ | 0 | M1, M3, M8, M9 |
| Offensive Reach | 1 | M1, M2, M9 |
| Help Without Advancing | 3 | M1, M2, M9 |
| Runner Out Rate | 0 | M1, M3, M9 |
| Runner Loss per PA | 0 | M1, M3, M9 |
| Scoring Opportunity Lost | 0 | M1, M3, M9 |
| Empty Games | 204 | M1, M2, M9 |
| Empty Game Damage | 0 | M1, M2, M3, M9 |
| Contribution Mix | 0 | M1, M2, M9 |
| Two-Strike Extension Rank | 0 | M1, M5, M8, M9 |
| Defensive Acts | 0 | M6, M9 |
| Defenders Involved | 0 | M6, M9 |
| Scoring History Length | 196 | M4, M9 |
| Run Contributors | 9 | M2 attribution, M4, M9 |
| Replay Overturn Rate | 0 | M7, M9 |
| Outcomes Changed by Review | 0 | M7, M9 |
| PAQ with Tie-Breakers | 0 | M1, M3, M5, M6, M8, M9 |

### Authorization and continuation rules

Engineering under accepted semantics proceeds without another permission round:
SPARQL/SQL corrections, source-owned SHACL implementing accepted meanings,
proof consumption, targeted derived-product updates, runtime reconciliation and
UI fixes. Reuse the user's recorded narrow RML approvals when they cover the
identified repair; do not ask again for implementation files or SHACL bookkeeping.

A genuinely new ontology term, identity policy or modeling assumption needs the
user's named decision. New object properties remain prohibited. An actually
missing graph fact requires a source witness and an exact, authorized additive
scope; whole-game replacement is not a substitute. Keep new source acquisition
and source expansion explicit. Spring training, exhibitions and WBC remain out
of active work. No RDF/database rebuild, no raw-source-to-SQL shortcut, no new
validation bureaucracy and no changing semantic pins on the user's behalf.

After a focused fix, publish `dev` and let its NiFi owner run. Continue independent
items instead of stopping after one diagnosis or waiting on a healthy worker.
Update this plan's work-item status only from published evidence. Do not announce
completion until the full nineteen-card finish line above has been met.

## 2. Keep operation incremental and recoverable

The [September 24 skeptical review](serving/ARCHITECTURE-REVIEW.md) records the
repaired request-time RDF fallback, cross-product fallback and missing/corrupt
dashboard publication recovery. Its remaining engineering concerns are shared
report/dashboard imports and calculation fingerprints that invalidate more
game work than the changed metric requires. These are engineering boundaries,
not requests for new source ingestion or semantic review.

- Diagnose recorded source or serving failures from terminal evidence, repair
  their cause and use the owning bounded retry. Do not monitor healthy runs.
- Tune the existing current/repair/historical queue priorities and bounded
  workers from recorded timings and memory limits. Source SHACL already reuses
  one Jena load per game while retaining each profile's report.
- Keep dashboard, full-report, authority SQL, repository evidence and RDF recovery
  independent. Preserve the published product when its replacement fails.
- Complete the remaining recovery acceptance work in
  [production readiness](infra/PRODUCTION-READINESS.md) and
  [RDF recovery](infra/RDF-RECOVERY.md): real backup/export/restore evidence,
  recovery objectives and the remaining host/configuration recovery scope.
- Keep acquisition at 05:00 Eastern and the user-authorized 15-minute batch
  checker. NiFi owns the bounded repair timers; their recorded queue state,
  rather than an old roadmap snapshot, determines whether they have work.

The configured NiFi-port migration fix, shared provisioning helpers, authority
lock recovery and report checkpointing are implemented. Their old roadmap
entries are not open implementation tasks. See the
[operational delivery record](infra/OPERATIONS-IMPROVEMENTS.md).

## 3. Extend legacy Explorer SQL only when useful

The legacy Explorer is separate from `/metrics`. Its contract still admits
PAQ-1/Good At Bat and supporting options to SQL; other families retain their
existing SPARQL routes pending family-specific result equivalence.

- Complete a family's row, filter, aggregation and date-scope equivalence before
  admitting that family to SQL. Existing shared grains and all 56 static DSQ
  tables are implemented candidates, not universal route admission.
- Add fact-to-fact bridge modules only for a concrete supported question and
  prove its equivalence through the existing owner.
- Preserve RDF/SQL timing evidence at matching corpus fingerprints.
- Keep official date/game-type provenance explicit. Accepted season-phase RDF
  is already available as a fallback and consistency check; a wholly RDF-only
  historical classification still needs coverage/equivalence evidence.

## 4. Review source and ontology gaps independently

Use the single [proposal catalog](proposals/README.md) for remaining MLB field
coverage, temporal role histories and future-source decisions. Operationally
successful ingestion does not establish complete API mapping. Existing-field
coverage debt stays in its source lane; do not reacquire or remap a season
because a metric exposes one omitted case.

The ontologist owns classes, axioms, identity policies and genuinely new modeling
assumptions. New object properties are prohibited. Existing ontology curation
debt remains recorded in [governance](governance/README.md), including unresolved
structural findings; documentation cleanup does not settle those decisions.

Statcast's rejected implementation remains retired. Fresh field inventories and
review-only geometry/process-profile designs need explicit acceptance before a
new detachable module is implemented. Weather and travel/rest remain later,
separate source families.

## Working and publishing

Use `dev`, fetch before publishing, and commit and push completed in-scope work
under [AGENTS.md](../AGENTS.md). Git was reauthorized on September 8. Never push
directly to `main`, rewrite published history or restore GitHub validation
without explicit authorization.

Use only the smallest useful developer check for changed behavior. Documentation
changes require diff review and `git diff --check`. NiFi's separate Repository
Evidence observer owns aggregate validation. Continue independent authorized
work when a semantic gap blocks one source assertion; do not make the entire
project wait on it.
