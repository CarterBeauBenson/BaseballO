# Competency questions and mapping contract

Draft answers below are proposed for M1/M2 only. They do not record acceptance.
Namespace `base:` is `https://baseballontology.org/`; `cco:` is
`https://www.commoncoreontologies.org/`; `obo:` is
`http://purl.obolibrary.org/obo/`. All terms already exist in the pinned ontology.

## M1: counted fouls

**CQ1. Does an ordinary foul increment the institutional strike count?**
Emit the existing `base:StrikeProcess`, `base:StrikeJudgmentAct` and
`base:StrikeDecisionICE` pattern when a final, reconciled event sequence
supports an increment from one strike to two. Retain the existing first-strike
foul mapping and ordinary foul structure. This proposal adds no general
numeric count-state representation.

The new second-strike gate requires:

- `isPitch=true`, ordinary foul call `F`, and the existing bunt gate false;
- one unambiguous stable pitch `playId`, one PA, and a complete reconciled
  prefix of play events in that PA;
- the immediately preceding source event has strike count 1 and this event
  has strike count 2, with equal ball counts;
- valid integer counters, unique event indexes and supported temporal order;
  a previous event's end must not be later than this event's start;
- no unresolved review, substitution, counter correction, reset or unexplained
  event in the prefix. Non-pitch records must be accounted for; filtering them
  out before comparing counts is prohibited.

First-event defaults cannot supply a missing preceding count for this added
case. A final flag alone does not prove a complete prefix. E1 source authority
and its reconciliation requirements remain in force. Source indexes identify
the rows to reconcile; no new BFO precedence is inferred from their numbers.

**CQ2. Does a two-strike foul create another strike?** No. A 2-to-2 ordinary
foul retains its Foul Ball Process but produces no additional strike under M1.
Missing or contradictory preceding evidence withholds this added mapping;
it does not turn a foul into a strike by default. Foul bunts, foul tips,
automatic strikes and overturned calls are outside this extension.

**Identity and graph contract.** Reuse the existing pitch-scoped
`process/strike/{playId}`, `judgment/strike/{playId}` and
`decision/strike/{playId}` IRIs under `data/game/{gamePk}/`. Reuse all existing
CountedFoulSource consumers, including the record's aboutness, strike-rule
input, field location and institutional foul/strike pattern. Do not mint a
second strike because two source records describe it. The Strike Process is
an occurrent part of its PA and has the Strike Judgment Act as an occurrent
part. That judgment has output the decision, which is about the Strike
Process. M1 does not change the previously admitted temporal relationship
within this existing pattern.

**Validation.** Source-to-context evidence independently inventories candidate,
admitted and withheld rows and reasons. Source SHACL requires the complete
typed strike/judgment/decision/PA pattern and unique output for each added
strike. Source-to-RDF reconciliation must match the exact admitted pitch IDs;
SHACL over RDF cannot establish the absence of an omitted source row.
Regression cases include 1-to-2, 2-to-2, non-pitch interruption, duplicate
indexes, missing counters, overlapping timestamps and unresolved review.

## M2: affirmed pitch reviews

**CQ3. What is reviewed?** An explicitly reviewed called pitch, not the PA's
terminal result by default. Require a unique pitch `playId`, an explicit
event-level `reviewDetails`, `inProgress=false`, `isOverturned=false`, and
operative call `B`, `*B` or `C` consistent with the event's ball/strike flags.
Withhold incomplete, contradictory, swung-at or overturned cases from M2.
A reviewed pitch need not be the final pitch of its PA.

**CQ4. What are the original and operative decisions?** For this bounded
affirming case, the final explicit Ball/Strike content and explicit unchanged
disposition support the same content for the original decision. The two ICEs
remain distinct. No original content is reconstructed by negating an
overturned result. This rule does not expand the current overturn contract.

**CQ5. Does the review create a second counted pitch result?** No. Reuse the
existing `judgment/{ball|strike}/{playId}` individual as the **operative review
judgment**, additionally typing it
`base:BallAffirmingBaseballReplayReviewAct` or
`base:StrikeAffirmingBaseballReplayReviewAct` and explicitly
`base:BaseballReplayReviewAct`. Its existing `decision/{ball|strike}/{playId}`
output additionally receives `base:BaseballReplayDecisionICE`. The counted
Ball/Strike Process and its judgment/output remain one operative pattern.

This is the M2 identity decision requiring acceptance: the existing pitch
judgment denotes the operative adjudication, which is the review adjudication
in this admitted case. It does not denote both the initial and review acts.

Create a distinct original judgment and original decision, scoped by game and
stable pitch ID:

- `data/game/{gamePk}/review/pitch/{playId}/judgment/on-field`;
- `data/game/{gamePk}/review/pitch/{playId}/decision/on-field`;
- `data/game/{gamePk}/review/pitch/{playId}/process/on-field`;
- `data/game/{gamePk}/review/pitch/{playId}/result`;
- `data/game/{gamePk}/event-record/review/pitch/{playId}`.

The original judgment is a `base:ReviewedOnFieldUmpireJudgmentAct` and the
applicable Ball/Strike Judgment Act. It has output the original decision,
typed `base:ReviewedOnFieldBaseballDecisionICE` and the applicable Ball/Strike
Decision ICE. It is an occurrent part of its separate original
`base:BaseballInstitutionalProcess`. The review has input that original
decision and output only the operative decision. Its original judgment
precedes the review because this is an explicit completed reconsideration;
no exact review timestamp is invented from the pitch timestamp.

Both decisions are about the same existing `base:PitchBallMotionProcess`,
in addition to their respective institutional processes. This identifies the
particular subject matter without an `affectsPlayer` or `reviewOfPitch`
property. The existing pitch judgment's umpire agency/role assertions are
not automatically transferred to the review: retain them on the original
on-field judgment; assert review agency only when independently supported.
Unidentified review officials are not replaced with the challenger or software.

The result ICE is `base:AffirmingBaseballReplayReviewDispositionICE`, is output
of the review, and is about both decision ICEs. Decision output cardinality
is checked among Baseball Decision ICEs; the separate disposition output
does not constitute a second decision. The review event record is about the
review, original judgment, both decisions, disposition and exact pitch.

**CQ6. How are duplicate and separate reviews handled?** Two different pitch
IDs in one PA identify separate reviews. Repeated evidence about the same
pitch must reconcile to one review. Preserve existing play-level review
identities when they concern a different out/safe outcome. If both the PA
narrative and pitch record describe this same pitch review, use the existing
PA-scoped review identity instead of creating a competing review individual;
the existing operative pitch judgment must be joined to that canonical
review identity during context construction. Do not emit `owl:sameAs` as a
substitute for resolving the identity. Ambiguous correspondence, multiple
reviews of one pitch or incompatible dispositions withhold that review.

**CQ7. Who is the affected player?** Follow the reviewed decision's subject
matter to the pitch and actual batting act/person, using accepted motion,
PA containment and role/agency relations. A completed PA's final matchup
cannot overwrite an earlier actor after a substitution. Withhold player
assignment until that pitch's batter is supported. The reviewed outcome can
still be represented without assigning a public player score.

`reviewDetails.player` is evidence to investigate challenge initiation. M2
does not assert a challenge agent or classify a review mechanism solely from
that field or undocumented `reviewType` tokens. The inspected catcher must
not receive the hitter's outcome statistics. Challenge counts remaining at
game end do not establish eligibility at each prior pitch. Mechanism-specific
eligibility and the Review Dependence denominator remain separate work.

**Validation.** Source SHACL requires distinct original/operative decisions
and judgments, exactly one original decision input and operative decision
output, matching affirmed content, the same pitch-motion subject matter,
and the existing operative counted-process pattern. No original judgment may
also be the review. Reconciliation detects duplicate review representations,
preserves unaffected play-level reviews and checks exact source-to-RDF
membership. Tests cover the two nonterminal reviews in game 824315, two
reviews within one PA, duplicated narrative/event evidence, incomplete and
overturned reviews, conflicting flags, and substituted batting participation.

## Engineering after acceptance

Implement both contracts through the existing context/RML/source-SHACL path.
No direct JSON-to-SQL bypass, new source module or NiFi topology is proposed.
Update only the admitted MLB artifacts' exact pins after their checks; global
ratification and unrelated frozen meanings remain untouched. One-record and
one-game proofs precede NiFi-owned bounded corpus work. Mapping proof must not
be reported as completed Recovery Quality or a complete review denominator.
