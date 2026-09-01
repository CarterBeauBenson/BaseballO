# Competency questions

These questions test the proposed meanings independently of any provider
field, RML triples map, or user-interface requirement.

## Teams, roles, venues, and time

1. Which organization is a Baseball Team, and which game-scoped Home Team Role
   or Away Team Role inheres in that organization for a particular game?
2. Can one Baseball Team instantiate both Home Baseball Team and Away Baseball
   Team across different games without making home or away an intrinsic kind
   of organization?
3. Which Facility bears a Baseball Game Hosting Function, without asserting an
   unreviewed direct relation to a Baseball Field Site or entailing that the
   function has been realized?
4. Which continuous Temporal Interval is occupied by a Baseball Game?
5. Which Temporal Instant is the first or last instant of the Temporal Region
   occupied by a Process that is an occurrent part of a Baseball Game?
6. Which Temporal Instant Identifier designates that instant and, under the
   separately reviewed ICE-direct-value foundation, bears its datetime literal?

## Coordinates and locations

7. What accepted Spatial Reference System supplies the interpretation for a
   field-relative coordinate tuple?
8. What Designative Information Content Entity designates a real field-relative
   Site, and what evidence establishes that the Site exists rather than merely
   appearing as a point in a provider display?
9. Can the coordinate content, its directly asserted values, the reference
   system it uses, the designated Site, the Baseball occupying the Site, and
   the ball-motion process remain distinct?
10. Which claims must remain withheld when coordinate axes, units, origin,
    orientation, temporal scope, or provider semantics are unresolved?

## Double plays and foul tips

11. Which Baseball Institutional Process has exactly two supported Out Process
    parts during one continuous play?
12. What independently defined institutional criterion and world-side
    ground-ball structure distinguish a Grounded Into Double Play Process from
    every other Double Play Process without defining a new Rule, Judgment,
    Decision, and Process only through one another?
13. Which Strike Process is also a Foul Tip Process, which Strike Judgment Act
    adjudicates it, and which Strike Decision ICE expresses the foul-tip
    decision?
14. Can contact, catching, judgment, decision information, communicated call,
    and counted Strike Process be queried as distinct entities?

## Challenges, motion, and replay

15. Which Challenge Act is also a Manager Act, and which is also a Player Act,
    without asserting two direct taxonomy parents?
16. Which Baseball Physical Process is also CCO Motion and has a Baseball as
    participant after a pitch, bat-ball contact, or throw?
17. Which replay-review act has ball-to-ball, strike-to-strike, out-to-out, or
    safe-to-safe input and output decisions?
18. Which replay-review act changes ball to strike, strike to ball, out to
    safe, or safe to out while remaining a judgment of the final counted kind?
19. Can affirming and overturning group membership be inferred from reviewed
    decision-pattern unions rather than asserted as a second direct parent?
20. Can the ontology express a replay-review act with reviewed input and output
    decision types without licensing an RML rule that synthesizes an
    unsupported original decision?

## Acceptance tests

21. Does each of the 31 classes have exactly one direct named parent, exactly
    one English label and definition, and at least one example plus an
    evidence-limiting comment?
22. Does every definition begin with the class label and use the explicit label
    of its proposed direct parent as the genus?
23. Do all proposed relations resolve to existing BFO or CCO properties, with
    their authoritative direction, domain, and range preserved?
24. Does the proposal place CCO literal-value, measurement-unit, and
    reference-system assertions directly on an ICE, without forcing that ICE
    to be an Information Bearing Entity, if the shared foundation is accepted?
25. Can the package be accepted, rejected, or revised without changing any
    executable artifact?
26. Do the four proposed supporting classes have one named parent, aligned
    definitions and axioms, complete annotations, and no new object property?
