# Web evidence assessment of the 21 shared metric gaps

Research date: 2026-09-08. All 21 register entries were assessed.
Twelve factual research questions below have supported answers. These include
stronger confirmation of earlier findings as well as new findings; they are
not twelve newly admitted graph contracts. No complete live-admission gate is
closed solely by this research. The remaining work is identified separately
for every shared gap, so settled baseball facts do not need another user vote.

## Resolved factual questions

### R01 — What determines a useful lead?

The initial second-base lead is constrained by returning against a pickoff.
Primary and secondary leads have different timing and mechanics. Coaching
adjusts them for the runner and defenders rather than prescribing one universal
distance. [Doug Bernier's coaching guide](https://probaseballinsider.com/baseball-instruction/base-running/how-to-take-a-lead-at-1st-and-2nd-base/).

ABCA instruction specifically relates lead length to the runner's return
reaction and the pitcher's quickness. It recommends practice against live
pitchers and adaptation of technique.
[Al Figone, ABCA](https://www.abca.org/magazine/magazine/2016-1_Winter/The_Hot_Corner_How_to_Incorporate_BallintheDirt_Reads_in_Baserunning_Drills.aspx).

**Consequence for review:** the user's returnability direction has a concrete
coaching anchor. A fixed-radius substitute is unsupported. The remaining
ontology question is how that criterion determines this larger Site's extent
and identity at the relevant time, not whether coaches use returnability.

### R02 — Can advancing on a loose pitch involve runner skill?

ABCA teaches anticipation, pitch reads, launch mechanics and practiced
decisions for taking bases on balls in the dirt.
[ABCA drill guidance](https://www.abca.org/magazine/magazine/2016-1_Winter/The_Hot_Corner_How_to_Incorporate_BallintheDirt_Reads_in_Baserunning_Drills.aspx).

**Consequence for review:** this supports the already accepted independent
running channel. Attribution to an individual observed episode still needs
evidence. The runner's contribution measure should not be presented as a
measurement of physical speed: decision-making and execution matter too.

### R03 — Is public runner-speed data available?

Yes. The public Sprint Speed table includes seasonal Sprint Speed and HP-to-1B
columns. Sprint Speed uses the fastest one-second window of qualifying runs,
aggregated for the season; the table supports CSV download.
[Official leaderboard](https://baseballsavant.mlb.com/sprint_speed_leaderboard).

**Consequence for review:** seasonal speed and home-to-first summaries are
identified source candidates. This closes their public-availability question,
not play-specific coverage or causation. A seasonal fast/slow split would be an
analytical choice, not proof that speed caused an individual error.

### R04 — Is any lead-distance data public, and is it enough?

The public Basestealing Run Value product defines Lead Distance Gained between
the pitcher's first movement and release. It provides aggregate filters and
CSV download. Its opportunity population is explicitly restricted.
[Official basestealing documentation](https://baseballsavant.mlb.com/leaderboard/basestealing-run-value).

A 2026 preprint models pickoff and steal probabilities using lead distance,
context and player skill. Its authors explicitly identify their raw play-level
lead tracking as proprietary. Version 2 was submitted August 16, 2026.
[Powers et al., data availability section](https://arxiv.org/html/2601.15608v2).

**Consequence for review:** public summaries exist; the investigated paper
does not supply an open event-level location source. Its probabilistic model
does not establish guaranteed returnability. This is a bounded finding about
these resources, not a claim that no other provider could supply tracking.

### R05 — Can pitch-call totals supply exact strike states?

Timer violations can add a ball or strike without a pitch.
[MLB pitch-timer rules](https://www.mlb.com/glossary/rules/pitch-timer).
Caught foul tips are strikes, including strike three.
[MLB foul-tip definition](https://www.mlb.com/glossary/rules/foul-tip).

The checked-in MLB path inventory already contains event-level `count.strikes`,
event `index`, `isPitch` and PA `about.isComplete`. These are owning-lane source
fields, not a reason to import duplicate counters from another provider.

**Consequence for review:** distinguish an ordered count-state update from a
delivered pitch. Recovery counts the accepted nonterminal pitches; automatic
updates and operative corrections require separate handling. The existing
pitch-only helper must not receive such updates disguised as pitches. Its
future live adapter needs an explicit contract for these cases. No exact-state
mapping or completed-PA classification is inferred from field names alone.

### R06 — Does a strikeout establish an out?

An uncaught third strike can leave the batter safe while retaining the strikeout
statistic.
[MLB strikeout definition](https://www.mlb.com/glossary/standard-stats/strikeout).

**Consequence for review:** require the operative runner resolution for damage.
The accepted -1/4 example assumes the batter actually is out. No new credit
for uncaught-third-strike advancement is selected here.

### R07 — Does every interrupted turn create a PA?

No PA is credited when a baserunning out ends the inning during an unfinished
batting turn.
[MLB plate-appearance definition](https://www.mlb.com/glossary/standard-stats/plate-appearance).

**Consequence for review:** the accepted one-PA eligibility rule needs completed
PA evidence, not just an `allPlays` record or a Batter Act. Use the existing
per-game reported PA count as a reconciliation candidate, not as a substitute
for a reviewed relationship to the actual batting participation.

### R08 — Are scoring codes identical to actual running outcomes?

No. Rule 9.07(f) permits a caught-stealing charge when an error leaves the
runner safe; 9.07(h) excludes certain outs advancing on escaped pitches.
[2026 Official Baseball Rules, 9.07](https://mktg.mlbstatic.com/mlb/official-information/2026-official-baseball-rules.pdf#page=133).

**Consequence for review:** resolve runner identity, actual terminal state and
credited process separately from scorer classification. Do not derive damage
from CS totals or treat the independent-running channel as an SB-code filter.

### R09 — Can an appeal revise inning-ending consequences?

Rule 5.09(c) allows an apparent fourth-out appeal to take precedence when
determining the operative out and its scoring effect.
[2026 rules, 5.09(c)](https://mktg.mlbstatic.com/mlb/official-information/2026-official-baseball-rules.pdf#page=63).

**Consequence for review:** a displayed third-out count is not sufficient to
finalize the admitted consequence. Retain the existing three-out arithmetic
bound while resolving the operative outcome before input. Never feed four
attributed outs into the kernel or select an appeal outcome by array order.

### R10 — Can defensive credits reconstruct the act sequence?

No. Rule 9.10 limits a fielder to one assist in a rundown even when that fielder
throws or deflects repeatedly.
[2026 rules, 9.10](https://mktg.mlbstatic.com/mlb/official-information/2026-official-baseball-rules.pdf#page=138).

**Consequence for review:** official credit lists cannot establish the number
or complete order of intentional acts. Distinct observed act and agent evidence
is required for the accepted four-act example. A source may support some
defensive participation without supporting a complete defensive path.

### R11 — Are foul calls categorically unreviewable?

Reviewable: specified fair/foul calls beyond corner umpires' set positions,
plus fan interference.
[MLB replay categories](https://www.mlb.com/glossary/rules/replay-review).

**Consequence for review:** the category question is settled; exact eligibility
must use the official category conditions. RDR still needs a selected denominator
and complete operative-outcome identities. A `foul` string alone is insufficient.

### R12 — Are pitch challenges the same population as traditional replay?

MLB's ABS dashboard documents the 2026 ball/strike challenge system and provides
its own challenge metrics. Its displayed overturn-rate denominator is challenges, not all
institutional outcomes in a game.
[Official ABS dashboard](https://baseballsavant.mlb.com/abs),
[metric definitions](https://baseballsavant.mlb.com/abs-metrics-documentation).

**Consequence for review:** identify mechanism and season in the evidence
selection. A public ABS dashboard is not evidence that our admitted mapped
review population covers ABS completely. The existing AV scope stays explicit;
neither ABS nor replay success rates define the custom RDR denominator.

## What remains for each shared gap

This table specifies remaining work rather than re-opening accepted answers.
"Model" means a world-side relation, identity, temporal or attribution decision;
"evidence" means source coverage and its graph proof. Ordinary engineering
within accepted semantics remains Codex's responsibility.

| Gap | Research contribution | Remaining work |
| --- | --- | --- |
| ATTRIBUTION | R02, R03, R06, R08 distinguish skill, summaries, classifications and actual outcomes. | Model: any speed-based error credit; interference deferred. Evidence: accepted attribution cases and their complete consequences. |
| BOUNDARY_STATE | R01, R04 anchor returnability and locate data limitations. | Model: larger Site identity/extent and time-qualified location. Evidence: the relevant observation; aggregate distance is insufficient. |
| PATH_IDENTITY | R08, R09 constrain terminal outcomes. Personal lifetime already accepted. | Model/evidence: demonstrable continuous personal path and its parts; replacement transition. |
| OPERATIVE_OUTS | R06, R08, R09 settle why K/CS/count labels are insufficient. | Evidence/model: distinct final resolutions and correction/appeal precedence; out attribution. |
| COMPLETENESS | R05, R07, R10 identify specific insufficiencies. | Evidence: participant, PA, event, outcome and correction coverage; source-owned SHACL after graph review. |
| TFS | Inherits the findings above. | Resolve its shared dependencies once; no separate formula vote needed. |
| REFERENCE_POPULATION | R07 supports completed-PA selection; accepted cutoff already settled. | Evidence: game type, season/cutoff, completed membership and full admitted coverage. |
| PAQ_A_STATE | Resources do not define this custom comparison metric. | User choice: PA-start or immediately pre-consequence cohort; then evidence for that boundary. |
| OFFENSIVE_ELIGIBILITY | R07 distinguishes completed PAs from interrupted turns. Minimum already accepted. | Evidence: complete PA and contribution coverage. Model: resolve rare mid-turn substitutions versus official statistical attribution before admitting them. |
| INDEPENDENT_EPISODES | R02, R08 support runner contribution and distinguish scoring codes. | Model/evidence: independent episode and beneficiary identities, mixed-event attribution. |
| INDEPENDENT_SCORE | R02 supports the positive channel; comparator below informs scope. | User choice: positive weights, additivity and net-score meaning. Negative damage is already accepted. |
| CHANNEL_EPISODES | R08 reinforces why one source label is not an episode. Unit already accepted. | Evidence: stable play identity and positive channel attribution. |
| EXACT_PITCH_COUNTS | R05 identifies source counters and non-pitch count updates. | Model/evidence: operative ordered count-state contract; pitches versus automatic updates and interrupted turns. |
| DEFENSIVE_ACTS | R10 rules out reconstructing acts from assist counts. Grain already accepted. | Model/evidence: distinct intentional acts and causally active agents. |
| DEFENSIVE_ORDER | R10 establishes the credit list is insufficient. | Evidence/model: complete supported precedence, including repeated actions. |
| RUN_CONTINUITY | R09 identifies why final scoring validity matters. Lifetime already accepted. | Model/evidence: continuity across PAs, substitutions and operative terminal score. |
| SUPPORT_ATTRIBUTION | R02 supports independent running contribution. Own-runner inclusion already accepted. | Model/evidence: actual support links to the scoring path, not game co-participation or RBI counts. |
| OPERATIVE_REVIEW | R09, R12 distinguish operative corrections and review mechanisms. | Model/evidence: exact affected outcome and review input/output links. |
| OUTCOME_POPULATION | R11, R12 settle inclusion candidates and mechanism distinctions. | User choice: the distinct outcome denominator; evidence: complete season-specific eligibility. |
| ROLE_POPULATION | Four kinds and actual realization already accepted; a web definition cannot certify game evidence. | Evidence/model: complete actual game-scoped realizations, especially Fielder; no new role kinds required. |
| PAQ21_ELIGIBILITY | R05, R07, R10 identify the relevant applicability evidence limits. Exclusion policy already accepted. | Evidence: known applicability versus unknown information and the complete applicable reference population. |

## Numerical weights: evidence does not choose the custom metric

Statcast's basestealing measure accounts for opposing pitcher/catcher context,
values gains and losses, and includes opportunities without an attempt. Its
documented translation uses +0.2 runs per advance and -0.45 per out. Those
units and population differ from our trajectory fractions.
[Official basestealing method](https://baseballsavant.mlb.com/leaderboard/basestealing-run-value).

Its extra-bases model uses runner speed, positions, fielding distances and
throwing strength to estimate opportunity-specific success. It covers batted
ball advances and excludes steals.
[Official extra-bases method](https://baseballsavant.mlb.com/leaderboard/baserunning).

Inference: these are useful external comparison methods. Neither selects our
increasing base weights nor supplies a speed-caused-error rule. The proposed
additive fractions remain a user decision. They would measure weighted
advancement, not empirical run expectancy or physical Speed.

## Concrete next review package

1. **Location and continuity:** finish the larger Site's extent/identity and
   temporal account, and the supported personal trajectory links. R01 and R04
   supply the evidence basis and its current limitations.
2. **Attribution and outcomes:** preserve settled progress/damage policies;
   specify the exact graph contract for actual outcomes, supported contribution,
   count corrections, appeals and rare mid-turn substitutions. Keep speed/error
   and interference choices explicitly unresolved.
3. **Populations and values:** decide PAQ-A's boundary, RDR's denominator and
   positive running weights. All other previously accepted population/counting
   choices remain accepted; implementation needs evidence, not repeated votes.

After the required model review, engineering can implement source-owned
constraints and focused fixtures. Public web statements alone do not authorize
new ontology assertions or demonstrate that a game graph meets those contracts.

The [research index](web-gap-assessment.json) links these twelve answers to all
21 gap IDs. The central register retains each live prerequisite while exposing
which factual questions are resolved. No ontology, RML, SHACL, Mermaid, semantic
pin, raw evidence or runtime schedule was changed by this research.

Focused verification: all 21 gap references, twelve finding sections and local
document links resolve. All seven existing metric Explorer/API tests pass with
the updated register. No calculation or ingestion test run was required for
these documentation and research-metadata changes.
