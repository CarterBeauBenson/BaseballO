# Authorized metric fixes: developer evidence

This directory records focused checks and one asynchronous recovery submission.
It does not certify a populated dashboard or a complete season.

## Contribution, Reach and Help

[contribution-result.json](contribution-result.json) records the fresh
`tests/prove_contribution_inputs.py` run on checked-in game 566279 and its
previously validated RML graph. It passed runner-boundary, B1 and
runner-resolution admissions, canonical Jena extraction and exact SQL retention:

- 79/79 contribution scores; 77/79 immediate comparison states.
- Six complete isolated one-game player summaries: Contribution, Runner Out
  Rate, Runner Loss, Opportunity Lost, Offensive Reach and Help Without Advancing.
- Public selected-range results remain withheld without the independent schedule.

The report retains all six player populations and proof hashes; the large PA
input array is omitted from this compact copy. Reach and Help use admitted
batter contributions without requiring classification of unrelated running.

## Automatic award beside an affirmed review

[automatic-award-review-result.json](automatic-award-review-result.json) records
`tests/prove_automatic_award_review.py` on actual game 824087. Its newly generated
RML graph passed canonical source SHACL: 29,295 triples, 73 PAs, 267 delivered
pitches, one automatic award, zero withheld automatic awards. The strict mapper
now safely omits nonexistent neighboring-pitch edges.

PA 32 retains a clock strike before a separately reviewed, affirmed called
strike. Canonical Jena extraction and SQL agree on the count history 1, 2, 2, 2;
there are three delivered pitches and one two-strike extension step. The
automatic award contributes zero pitches.

The separate complete-game pitch-count admission correctly remains withheld.
The report verifies that every SHACL failure belongs to exactly the four
unapproved M3/M4 foul cases, rather than the repaired award or an affirmed pitch
review. No draft foul mapping was enabled. The mapped graph's raw hash is
retained; normalizing the edited RML file's line endings subsequently preserves
its canonical content hash `a67dbfc25c191c8b89cbb9a38b4e3a3f348374e37180679a6c7c99f69e4088a9`.

## Focused regressions

- 39 recovery-worker tests passed, including actual `materialization` stage
  naming, Windows seven-digit timestamp ordering, and explicit audited reopening.
- Five automatic-award selection tests and the actual strict-RML optional-neighbor
  regression passed; negative review cases remain withheld.
- 29 contribution/progress/SQL tests passed during implementation.
- 26 PAQ-2.1, defensive/review player-summary, contribution and SQL tests passed
  after adding the numerical reducers. These overlap the preceding tests.
- The source runtime-admission check passed with the existing frozen/unratified
  status preserved. Only the accepted Q5 context/RML pins changed.

Numerical defensive/review/PAQ-2.1 fixtures do not establish source coverage or
connect those five remaining source adapters. See
[the current readiness table](../../../serving/METRIC-READINESS.md).

## NiFi handoff

[recovery-submission.json](recovery-submission.json) retains the failed plan's
audit and the verified obsolete-implementation error. The corrected helper
queued `waiting-proof` for the already requested 2026-08-25 range. It dispatched
no processor itself. The existing NiFi worker owns the idle check, full proof,
serving rebuild and subsequent backfill. Submission is not completion; the
original quarantine remains intact and the daily acquisition schedule is unchanged.
