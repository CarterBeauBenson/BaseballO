# Lead-offs, running speed and replay research

Researched 2026-09-08. Findings inform the open review; they do not admit new
ontology terms, identity policies, source mappings or a speed-based error rule.

Follow-up: the [assessment of all 21 gaps](web-gap-assessment.md) adds twelve
resolved factual questions, public lead summaries, scoring edge cases and a
precise remaining-work inventory.

## Lead-offs

Doug Bernier's coaching instruction bases the initial second-base lead on
whether the runner can return against a pitcher pickoff. It also distinguishes
primary and secondary leads, adjusts positioning for fielders, and emphasizes
balance and returning after the catcher secures the ball. Its distance ranges
are coaching guidelines, not universal boundaries.
[Primary coaching source](https://probaseballinsider.com/baseball-instruction/base-running/how-to-take-a-lead-at-1st-and-2nd-base/).

The Australian Baseball Federation coaching manual likewise distinguishes
primary leads from balanced secondary movements after pitcher commitment.
See printed pages 124-126 of the
[Level 4 manual](https://www.baseballqueensland.com.au/wp-content/uploads/2019/10/Level-4-Manual.pdf).

Inference for the proposal: this supports the user's practical returnability
criterion, but does not supply an invariant radius. Returnability depends on
the runner, posture, reaction and the relevant defensive action. A measured
distance alone cannot establish it. A successful or failed return on one play
also cannot establish a general capacity by itself.

Preserve the existing base Site located in the larger Site and the user's
preferred located-at account. Remaining review must specify the larger Site's
extent and identity, the relevant return conditions, and temporal qualification
of location. This research does not introduce a Relational Quality, replace
location with recognized safety, or change Mermaid.

## Running speed and error pressure

Public Statcast data provides a seasonal Sprint Speed leaderboard with CSV
download. Sprint Speed measures the fastest one-second window on qualifying
runs; seasonal values aggregate selected qualifying performances. It is not a
measurement of every reach-on-error play.
[Official Sprint Speed leaderboard](https://baseballsavant.mlb.com/leaderboard/sprint_speed).

Statcast also publishes running split leaderboards with season, batting-side
and opportunity filters. Their availability does not prove that event-level
splits can be joined to every error in our corpus.
[Official running splits](https://baseballsavant.mlb.com/leaderboard/running_splits).

MLB notes that fast runners can pressure fielders into errors.
[Home-to-first explanation](https://www.mlb.com/glossary/statcast/home-to-first).

Local inspection found no admitted baserunning speed measurement in the active
MLB-game mapping or serving schema. The bounded MLB field inventory contains
pitch and batted-ball speeds, which measure different processes. The existing
Statcast field-selection inventories do not establish a runner-speed mapping.
There is currently no executable Statcast source module in `sources/`.

Inference: speed is potentially useful evidence of defensive pressure. Seasonal
speed alone cannot establish that speed caused an individual error, or justify
a fast/slow cutoff. Play-specific timing, actual defensive opportunities,
coverage and a reviewed attribution model remain necessary. Retain the accepted
error/FC progress exclusions while this is unresolved. Interference credit is
separately deferred by the user.

## Replay

Foul calls can be reviewable depending on location and category; fan
interference is reviewable.
[Current MLB review categories](https://www.mlb.com/glossary/rules/replay-review).

For exact category wording, consult that current official page. Do not infer
review eligibility from the string `foul` alone or silently restrict the
outcome population to out/safe and ball/strike. A complete RDR denominator must
still specify eligible outcome identities, scope and the applicable season's
review mechanism. Researching categories does not admit that denominator.

## Source selection before any extension

This is a preliminary selection inventory, not a new source contract. The
existing authoritative payload takes precedence even for unmapped fields.

| Candidate | Selection | Remaining evidence |
| --- | --- | --- |
| Stable player ID | Identity/join-only | Reuse the owning authority identity; establish provider join. |
| Season, game and play identifiers | Identity/join-only | Establish actual endpoint grain and supported event joins. |
| Seasonal Sprint Speed | Genuinely additional | Population, unit, aggregation scope, coverage and missingness; no event-specific causal inference. |
| Seasonal HP-to-1B summary | Genuinely additional | Public table identified in follow-up R03; establish aggregation and join scope. |
| Published running splits | Genuinely additional | Endpoint grain, elapsed-time origin, units and join scope. |
| Play-specific home-to-first elapsed time | Unresolved | Public event-level availability and coverage have not been established. |
| Aggregate Lead Distance Gained | Genuinely additional | Public product identified in follow-up R04; aggregate scope does not locate an individual at a metric boundary. |
| Play-specific lead distance | Unresolved | The investigated paper's raw tracking is proprietary; open endpoint coverage remains unestablished. |
| Return-to-base capacity | Unresolved | No admitted observation or reviewed estimation model establishes it. |
| Existing pitch and batted-ball speeds | Already supplied | Owning MLB mapping coverage where relevant; not runner-speed substitutes. |
| Expected batting output using speed internally | Unresolved for this purpose | A model output does not expose the runner's observed speed or error causation. |

Relevant local inventories:
`sources/mlb-game/schema/mlb-feed-path-inventory.csv`,
`archive/design-records/statcast-nonduplicate/field-selection-inventory.md`,
and `proposals/statcast-core-motion-contact/field-selection-inventory.md`.
Public field documentation is available in the
[Statcast CSV reference](https://baseballsavant.mlb.com/csv-docs).
