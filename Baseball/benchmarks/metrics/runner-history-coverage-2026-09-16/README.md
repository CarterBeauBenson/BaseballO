# Runner-history coverage and real player results

Against the unchanged August 25 source fixtures, complete C1 histories now
cover **8 of 15 games**, up from 2. Supported personal histories increase
from **292 to 360**. The [source comparison](coverage.json) names every game,
source hash, before/after count and remaining issue. This is developer source
evidence, not a claim that eight live dashboard selections are complete.

## Implemented corrections

- C1 checks actual pitch/movement time bounds across PA boundaries. Overlapping
  PA headers no longer erase independently ordered personal histories. Each
  overlap remains a `boundaryIssues` entry; separate PA-start admission still
  withholds the game's boundary-dependent scores. Actual event overlap rejects C1.
- Completed terminal tag and first-base reviews can account for final runner
  effects when narrative, structured disposition, review type and terminal
  in-play evidence agree. Every final movement, out, score and base must still
  reconcile. Original calls and affected-player review statistics are not inferred.
  Pitch-count review admission remains separate.
- Explicit defensive-indifference and pickoff-error movements remain existing
  generic episodes in the personal history. They do not create new classes or
  batting credit. Defensive indifference does not earn a stolen base under
  [MLB's glossary](https://www.mlb.com/glossary/standard-stats/stolen-base).
- An on-field delay is neutral only with unchanged counts and no movement,
  scoring, out, review, substitution or count award.
- A supported independent prefix stays separate from a later B2 contact. In
  game 823098 PA 45, Julio Rodriguez's steal remains outside the subsequent
  single. Its safe, scoring and terminal-out resolutions belong to that contact;
  all four episodes remain in their personal histories. The
  [owning shape](contact-admission.shapes.ttl) rejects adding the steal to the contact.

These implement the already accepted
[E1/C1 contract](../../../archive/design-records/metric-source-c1-operation-2026-09-14/review.json)
and [B2 contract](../../../archive/design-records/contact-play-continuation-membership/review.json).
No ontology term, object property, identity policy or RML template changed.
Existing RML emits the expanded supported membership. The context pin was
updated under the published C1 decision; the freeze remains unratified.

## Real-game graph and SQL proof

Game **823098**, unchanged source hash
`d8e4a976ef2af31a4b15557d2c768b7b20b86a064aa7684202e019d5bb885148`:

- [RML/source SHACL](rml-proof.json): 28,286 triples; 70 PAs; 259 pitches;
  89 runner resolutions; 21 personal histories; 40 episode memberships.
- Official-PA, runner-resolution, PA-start/award and
  [contact-continuation](contact-admission.json) admissions pass against that
  exact RDF. Its one mixed contact continuation is admitted, with none withheld.
- [Contribution proof](contribution-sql.json): **70/70 PAs resolve**. Canonical
  Jena extraction and SQL agree exactly. Isolated one-game player means cover
  Contribution, Runner Out Rate, Runner Loss, Opportunity Lost, Offensive Reach
  and Help Without Advancing. Immediate comparison states cover 68/70 PAs.
- [Scoring proof](scoring-sql.json): **5/5 scoring runs resolve** for both
  Scoring History Length and Run Contributors, with exact SQL retention and
  isolated one-game player means.

Both public date-range requests remain withheld without independent schedule
admission. No one-game fixture is presented as a complete MLB date or reference
season. Source values are validation inputs; calculations follow RDF -> query -> SQL.

## Focused verification

Thirty-three tests passed across `test_runner_history_coverage`,
`test_reconciled_runner_histories`, `test_runner_history_effects`,
`test_contact_continuation` and `test_walkoff_runner_boundary` in the owning
module. Cases include conflicting/pending reviews, actual event overlap,
uncertain PA starts, missing movements, extra contact members and false delays.

The walk-off test retains RML, positive/adversarial SHACL, query and exact SQL
assertions. Its formerly unbounded RDFLib query now uses production Jena with
a 60-second timeout; the five-test module completed in 28.4 seconds.

Whole-game checks use `run-rml.ps1 -DeveloperEvidenceRoot ... -ShaclEngine jena`,
the contact admission CLI, and existing `prove_scoring_run_players.py` and
`prove_contribution_inputs.py` helpers. NiFi owns repeatable validation and
serving refresh; no manual corpus promotion or routine SQL rebuild was run.

## Remaining gaps

Seven fixtures still have incomplete histories: replacements, placed runners,
action-event lifetime anchors/out-count scopes, the empty strikeout companion
at C1 scope, and other review effects remain unresolved. PA-header overlaps
still block affected start states. Complete personal histories therefore do
not imply complete batting eligibility or comparison states.

The five defensive/review-dependent player integrations and complete date/season
populations remain unfinished. The existing queued NiFi recovery checks artifact
freshness and must regenerate an older proof before releasing the refresh.
This report does not claim asynchronous promotion or 19 live leaderboards finished.
