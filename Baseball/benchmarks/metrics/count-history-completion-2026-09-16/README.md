# Count-history completion and dashboard accuracy

Game **823585 now has all 81 official plate appearances admitted for Recovery**:
43 are two-strike eligible and 38 are known ineligible. Current RML passes the
full source SHACL profile. Independent B1 and pitch/count proofs pass Jena;
the canonical query and exact SQL retention agree. The separate interrupted
turn remains outside the official-PA population. This is a complete one-game
input proof, not a complete-season percentile or live leaderboard claim.

## Fixed implementation defects

- A fully evidenced intentional walk represented by four virtual-ball records
  is a walk with zero delivered pitches. Source SHACL proves that zero census;
  serving preserves the PA as known ineligible for the two-strike metric.
  Missing history alone still cannot establish zero pitches. Extra pitches,
  count awards, strikes, conflicting outcomes and unauthenticated census
  metadata are rejected.
- The count validator now uses the already mapped foul-tip identity for both
  `T` and `O` calls. It previously looked for a nonexistent generic strike
  individual for an `O` call.
- The counted-foul selector applies M1's prefix scope. A reconciled terminal
  field review no longer suppresses an earlier foul. The final field-review
  event remains outside the admitted count prefix; earlier unsupported reviews,
  overlapping bounds and contradictory counts remain blockers. Game 823826
  PA 55 now has the correct 1, 2, 2 strike history through Jena and SQL.
- A pinch-runner replacement already reconciled by the accepted C3 contract
  can supply a count-neutral prefix. Both the outgoing and incoming personal
  histories must carry the exact replacement witness. This reuses the accepted
  identity and unchanged-count evidence; a substitution label alone, a pinch
  hitter, changed actors, bounds or base, and incomplete histories do not pass.
  In 823585 PA 35 this closes the last omitted counted foul. The first whole-game
  check exposed this omission after the intentional-walk repair; the final
  whole-game proof passes both fixes together.
- Request-local evaluation shares the common evidence inventory and progress
  projection across cards. Admission still runs independently for each metric.
  Copies prevent one card's completeness annotations from reaching another;
  evidence cannot cross a request or graph scope. All 20 backend results match
  separate calculations exactly. One real-game comparison took 1.06 seconds
  versus 1.31 seconds; this is not a production latency guarantee.
- The dashboard's primary summary now reports **populated player leaderboards
  out of 19**. A scoped review aggregate or a result with no qualified player
  rows cannot inflate that number. Role breadth remains backend-only.

No ontology, object property, RML text, metric formula, qualification minimum
or source schedule changed. The only protected implementation artifact changed
is the context builder, under the existing accepted counted-foul and C3
contracts. Its runtime pin was updated; the semantic freeze remains unratified.
The separate PA-start boundary/stasis restrictions are unchanged.

## Verification and deployment boundary

[The focused results](result.json) record source/RDF hashes, the complete-game
admissions, exact SQL equality, the two repaired PAs, the terminal-review case
and 97 passing focused Python/web tests. The independent player reducers still
require complete selected schedules and the accepted season reference.

The existing NiFi recovery queue already contains January 1–September 15, 2026
behind the active August 25 batch. It will run the current committed components
through the normal proof, source refresh and SQL publication stages. No second
full-season job was added and the healthy build was not interrupted.

The [shared-blocker inventory](../dashboard-shared-blockers-2026-09-16/README.md)
still identifies mixed contact/error ownership, independent-event coverage,
complete defensive populations and review-player integration. Additional count
prefixes also remain outside the implemented selection. These are remaining
work; this repair does not claim all 19 live player leaderboards are populated.
