# Placement adjudication and third-out history completion

The user's [placement decision](../../../archive/design-records/extra-inning-placement-adjudication/README.md)
was published in `fc88d16` before executable changes. No ontology file, new
class, object property, raw source byte or NiFi schedule was changed.

## Closed cases

- **823585, top 10:** Hamilton's placement is a distinct
  BaseballAdjudicationAct with a BaseballDecisionICE. His personal whole
  contains that adjudication and zero movement episodes, ending as stranded
  at the supported third out. Placement supplies no running or batting credit.
- **823826, top 8, PA 61:** the tracker no longer treats last observed bases
  as live occupancy after the reconciled third out. Gasper's history ends
  there without an invented first-to-second advance or an Out assigned to him.
  Conflicting live occupancy and pitches after the third out remain rejected.

The [source census](source-census.json) now reconciles **15/15** August 25
fixtures and **415 personal histories**, retaining all **409** prior selected
identities and episode allocations. There are eight placement adjudications
and one zero-movement history. This is bounded fixture coverage, not a claim
about every historical game or all 19 dashboard metrics.

Rule 7.01(b)(2) identifies the plate umpire's placement verification duty;
5.09(e) establishes retirement after three legal outs. See the
[2026 Official Baseball Rules](https://mktg.mlbstatic.com/mlb/official-information/2026-official-baseball-rules.pdf)
and the decision package's field selection inventory.

## Graph and serving checks

[Six isolated actual-RML cases](one-history-rml.json) preserve action,
replacement, placement and upheld-review identities, including Hamilton's
zero-movement whole. Exact source-owned SHACL checks the placement judgment,
decision, runner, base, rule, source record and complete part inventory.
Negative tests reject missing placement/output, incorrect person/base,
fictional running or Safe typing, and an invented named agent.

The [full-game RML results](full-game-rml.json) pass authoritative Jena SHACL:

| Game | RDF triples | Histories | Movement episodes | Placement adjudications |
| --- | ---: | ---: | ---: | ---: |
| 823585 | 34,764 | 33 | 54 | 2 |
| 823826 | 39,905 | 37 | 70 | 4 |

Exact history admission is **admitted, populationComplete=true** for
[823585](history-admission-823585.json) and
[823826](history-admission-823826.json).

Scoring History Length resolves every counted run through the canonical Jena
query and exact SQL retention: [five runs](scoring-depth-823585.json) and
[ten runs](scoring-depth-823826.json), including isolated player means.
The movement query excludes only the positively identified placement
adjudication. Unknown other parts remain visible and withhold an incomplete
history instead of silently shortening it. A zero-movement whole remains in
the authoritative source census without becoming a scoring contribution.

Focused source-history, SHACL, real-RML, movement-query, run-construction and
SQL tests pass. Existing assertions that expected these closed cases to remain
withheld were updated; live-occupancy and invalid-placement rejection remain
explicitly tested. A stale SQL test now checks exact evidence retention and
the separate player-admission gate instead of equating raw diagnostic and
public-player gap lists. No production admission gate was weakened.

## Separate contributor-attribution debt

The [Run Contributors audit](run-contributors-audit.json) resolves 11 of these
15 runs and still rejects four. These are implementation coverage issues,
not missing personal histories, missing provider records or questions for the
user to re-answer:

| Game / scoring PA | Exact remaining implementation issue |
| --- | --- |
| 823585 / 81 | Error movement on a fielder's-choice result has no supported contributor channel; the settled exclusion must be carried through without inventing contact causality. |
| 823826 / 38 | The scoring runner entered on the fielder's-choice-out in PA 35; that entry's contributor classification is not connected. |
| 823826 / 73 | The passed-ball scoring movement is absent from this metric's independent-running channel. |
| 823826 / 78 | The wild-pitch scoring movement shares the uncaught-strikeout event; its particular runner attribution must be retained rather than attributing it to the batter. |

The all-metrics scoring proof stopped at this contributor gate. The separately
successful depth proof above is explicitly limited to Scoring History Length.
Independent PA-start, defensive, review and season-population work is not
certified by this runner-history completion. Live promotion, SQL refresh and
the repository gate remain NiFi-owned and asynchronous; no public dashboard
readiness is asserted by these developer proofs.
