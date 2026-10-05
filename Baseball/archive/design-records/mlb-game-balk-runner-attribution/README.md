# BK1: attribute separately recorded balk advances

Accepted by Carter Beau Benson on October 5, 2026: **Approve and Approve**,
in direct response to the named EG1 and BK1 requests. This is existing MLB-game mapping coverage, not a new source.

The metric policy already includes balk advances in independent running. The
current RML types a Balk Process only when the PA's final result is `balk`.
A separately recorded balk before a strikeout or walk therefore has ordinary
runner facts but no structured balk attribution. The serving reader must not
recover that meaning from a display label.

## Accepted decision

1. Represent an explicitly recorded, operative balk within a PA with the
   existing `BalkProcess`, its existing `UmpireJudgmentAct`, a
   `BaseballDecisionICE`, and the existing `BalkRule`. Keep the PA's eventual
   batting result separate. No new class or predicate is proposed.
2. Reuse the existing runner record's `is about` links to identify the exact
   balk process, judgment, decision and Baserunning Act. Several runner rows
   joined to one source event share that event's process and judgment; they
   do not create a balk per runner. Do not assign the pitcher in the action
   record as the umpire or guess which umpire made the call.
3. Apply the accepted independent-running metric policy to these supported
   advances. They do not become positive batting credit. Preserve actual-end-
   state erosion and the independent attribution of a later batting result.
4. Add only the missing selected facts and their existing dependencies to
   affected promoted games, then refresh their derived products. Apply the
   same generic selector to future games. No graph replacement, full rebuild
   or blanket source reacquisition is part of BK1.

The proposed world-side pattern is in
[the review diagram](source-independent-mermaid.md). The named approval authorizes executable RML/source-selection changes and
their scoped semantic pins after this decision is published.

## Evidence and exact selection

Checked-in, unchanged witness: `Baseball/data/raw/game-566279.json`, PA 12,
event 5, SHA-256
`e36caf73ff54d6eeac29dba350d5d37001e769eaaf4c1a9e5eac4763ad2630c2`.
The final batting result is a walk. Runner 488671 advances from first
to second on the earlier `balk` action, joined by `details.playIndex=5`.
The action is explicitly nonpitch, with action identity
`a05f90a9-c21a-4e07-a4e0-7660dd0beb46`. The later walk is a different event.
The action's player 621381 is the pitcher, not evidence of umpire identity.

The October 5 read-only diagnosis also found the serving failure in game
822679, PA 65: runner 543760's first-to-second movement has a record with the
value `Balk` but no structured independent-running binding. The final result
is a strikeout. That label diagnoses the omission; it is not sufficient by
itself to authorize a repair. NiFi must retain an exact source witness before
adding facts for a particular game. No season-wide affected count is claimed.

The proposed selector requires:

- A unique action event within its PA, an explicit `balk` event type and
  `isPitch=false`, plus its source event identity. Missing or conflicting
  identities remain unresolved; array position alone is not a new act identity.
- An exact runner-row/event join, explicit runner identity, occupied origin
  base, safe next-base or scoring destination, and matching `balk` movement
  classification. Existing runner identity, episode and resolution patterns
  remain unchanged. Do not infer an advance for an omitted runner row.
- The existing operative-event/review reconciliation. A pending, reversed or
  ambiguous decision cannot be treated as the final balk merely because the
  text mentions one. A balk waived by subsequent play is outside this selector.
- No conflicting contact, steal, walk or other attribution for the selected
  segment. Distinct earlier/later segments retain their own meanings. Do not
  generalize BK1 to `forced_balk`, arbitrary clock violations, or an extra base
  taken beyond the award without a separately reviewed source selection.
- Existing T1 clock handling. Missing or contradictory times remain missing;
  this proposal does not manufacture timestamps or change history eligibility.

MLB's [balk glossary](https://www.mlb.com/glossary/standard-stats/balk)
confirms the one-base award. The [2019 official rules](https://content.mlb.com/documents/2/2/4/305750224/2019_Official_Baseball_Rules_FINAL_.pdf),
Rule 6.02(a)'s penalty and approved rulings, distinguish an enforced balk from
a play proceeding without reference to the balk, and from additional running
beyond the protected base. These rules support the selection exclusions;
they do not identify an event or umpire in an individual game.

## Field inventory

| Existing field | Classification | Use |
| --- | --- | --- |
| `gamePk`, PA index | Identity/join-only | Existing game and PA scope |
| Event index, action identity, runner `playIndex` | Identity/join-only | Exact event/movement join and shared event identity |
| Action and runner `eventType=balk` | Already supplied; mapping debt | Select the existing Balk Process pattern |
| `isPitch`, count, completion/review evidence | Already supplied | Distinguish this event from the later completed batting result |
| Runner identity, origin, destination, out/scoring flags | Already supplied | Reuse existing runner facts and check the exact supported advance |
| Action `player` | Already supplied | Pitcher evidence only; never substitute it for umpire identity |
| Description and event label | Duplicate description | Diagnostic only; never a semantic join |
| Event times | Already supplied | Reuse T1 behavior; no synthetic times |

## Implementation after acceptance

Record and publish the named decision first. Extend the MLB-game context and
RML with the reviewed source selector and existing pattern. Add its exact
constraints to that source's existing validation ownership; no new cross-source
gate. Use the checked-in witness and counterexamples for a focused regression.
NiFi then owns a bounded one-game check and the inventory of retained eligible
cases, additive promotion, retries and future ingestion. Preserve unrelated RDF.

Extend the existing runner-movement SPARQL and independent-running reader to
consume the structured pattern. Refresh only affected query indexes, metric
inputs and SQL player/reference products through their current owners. Verify
that the runner gets the accepted independent contribution, the batter gets
none of that advance, and the later batting result remains distinct. BK1 does
not establish complete PA boundaries, complete season references, defensive
populations or review denominators.
