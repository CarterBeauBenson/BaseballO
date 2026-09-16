# Named decisions and source graph contract

All capitalized domain terms below already exist in BaseballO. Reuse the
accepted counted-foul subject identities and relations. There is no proposed
general count-state ICE, new predicate, or inferred physical pitch.

## M3: fully reconciled ordinary-foul prefixes

May the existing one-to-two ordinary-foul mapping admit these additional
prefix records when their entire history remains reconciled?

1. A non-pitch stolen-base report with unchanged ball/strike count, one
   resolved runner/event join, compatible safe advance, and no out, review,
   substitution, score or counter correction. It changes the runner's state,
   not the batter's count. It receives no batter contribution credit.
2. A pitching substitution before any pitch or automatic count award, with
   explicit 0-0 counts, distinct identified incoming/outgoing rostered pitchers,
   no batter replacement, and actual subsequent pitch agency reconciled to
   the incoming pitcher. This does not admit arbitrary mid-count substitutions
   or equate statistical credit with actual participation.
3. A completed, explicitly identified MJ pitch-result review with consistent
   final called-ball/strike flags and the single operative count increment.
   Require `inProgress=false`, explicit Boolean disposition, stable pitch ID,
   agreement of duplicate PA/event review records, and complete prefix counts.
   The final call may be affirmed or overturned. This uses the accepted E1
   operative-history criterion; it does not infer an original call or expand
   M2's original/operative review-judgment mapping.

The subsequent ordinary foul must still be non-bunt F, have a stable unique
pitch ID, preserve balls, and increment strikes exactly from one to two.
All source events remain inventoried. Unresolved effects, ambiguous identity,
inconsistent counters, overlapping event bounds, unknown review state, and
unexplained transitions continue to withhold the prefix. Source indexes are
join keys, not strict BFO precedence assertions. Existing admitted cases stay
unchanged. A two-to-two ordinary foul never gains another Strike Process.

## M4: explicitly counted foul bunts

May a final, fully reconciled L (Foul Bunt) event with supported actual bunt
participation instantiate the existing counted Strike Process, judgment and
decision pattern when source strikes increase by exactly one?

Require one actual Pitch Act, Bunt Attempt Act, Bat-Ball Contact Process and
Foul Ball Process with existing participants, roles and record support; a
stable unique pitch ID; consistent explicit call/strike flags; unchanged ball
count; and a complete operative prefix. A prior zero count may come from the
positively reconciled PA beginning. A two-to-three foul bunt also requires
the supported terminal strikeout judgment; it must not manufacture an Out
Process merely from the third strike. A first/second foul bunt is not a
strikeout. Missing or contradictory support withholds the case.

## Full reused pattern and validation

Under `https://baseballontology.org/data/game/{gamePk}/`, reuse
`process/strike/{playId}`, `judgment/strike/{playId}` and
`decision/strike/{playId}`. There is one operative counted strike, not one per
description. Preserve PA containment, field location, the Foul Ball Process,
existing Strike Rule input, judgment output, decision aboutness and source
record support. Do not infer judgment agents or review timing from the pitch.

The source-owned SHACL profile must require the full typed structure and
exact source-to-RDF membership for all admitted M3/M4 instances. The selection
inventory must retain withheld cases and reasons. Mutation checks must reject
missing judgment/decision/rule/record links, incorrect agency, duplicate
strikes, neutral-event count changes and unsupported review states. Complete
one-record proofs precede a one-game RDF/SHACL proof, which precedes any NiFi
corpus refresh. Existing metric and population gates remain in effect.
