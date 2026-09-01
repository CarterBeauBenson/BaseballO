# Game, season, and team-context accepted ontology design record

Status: **accepted by the ontologist on 2026-08-28**.

This record preserves three connected modeling decisions stated by the
ontologist during the ground-up ontology repair. It is recorded before their
ontology and proposal consequences are implemented.

## Accepted decisions

1. A Baseball Game is a BFO Process. It is temporally extended and has
   Baseball Acts and other processes as occurrent parts. Being governed or
   prescribed by a plan or ruleset does not make the whole game a Planned Act.
2. A Baseball Season is a BFO Process. A temporally extended Baseball Season
   Phase is likewise modeled on the process side. A Baseball Season Plan may
   prescribe those processes without changing their ontological category.
3. Team membership needed for MLB transaction modeling does not require a new
   Baseball Roster Membership Role. Existing occupation-role instances carry
   the organizational context. For example, Aaron Judge is a Yankee during an
   interval when the Player Role he bears has the New York Yankees as its
   organizational context.

## Authorized consequences

- Repair the accepted Baseball Game taxonomy, definition, and axioms so that
  the named parent is BFO Process while its acts and physical or institutional
  processes remain occurrent parts.
- Model the proposed Baseball Season and Baseball Season Phase as BFO
  Processes, with the Season Plan kept as a distinct Directive Information
  Content Entity.
- Remove the proposed Baseball Roster Membership Role and express relevant
  transaction effects through existing occupation roles, their organizational
  contexts, and their temporal stases or changes.

No new object property is authorized by this decision.
