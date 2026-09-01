# Field selection and proposed terms

| Term or evidence | Disposition | Consequence |
| --- | --- | --- |
| `BaseballRosterStatusAct` | proposed class | Shared source-independent genus for grounded declarative roster-status Acts. |
| `BaseballPlayerReleaseAct` | proposed class | Team-agent Act preceding Loss of exact team Player Role. |
| `BaseballPlayerReleaseDecisionICE` | proposed class | Directive ICE output of the Release Act and about the affected Player Role. |
| `FreeAgencyDeclarationAct` | proposed class | Person-agent declaration/election preceding Gain of exact Major League Free Agent Role. |
| `FreeAgencyDeclarationDecisionICE` | proposed class | Directive ICE output of the declaration and about the gained Role. |
| `RetirementDeclarationAct` | proposed class | Person-agent declaration preceding Loss of the supported active Role. |
| `RetirementDecisionICE` | proposed class | Directive ICE output of the retirement declaration and about the lost Role. |
| Assigned/Recalled/Optioned/Outrighted/Selected | unresolved world kinds | Information classification only in first RML pass. |
| DFA/Waiver/Suspension temporary Roles | unresolved realizability and identity | Do not admit or map until separately grounded. |
| Status Change/Acquired/Obtained | unresolved provider categories | Information-only; no free-text guessing. |

## Proposed class accounts

Each proposed class has one named parent and later overlay restrictions that
state the same structure as its definition.

- **Baseball Roster Status Act** - parent: Act of Declarative Communication.
  Definition: an Act of Declarative Communication that has output a Directive
  Information Content Entity and precedes a Gain of Role or Loss of Role
  affecting a Player Role or Major League Free Agent Role.
- **Baseball Player Release Act** - parent: Baseball Roster Status Act.
  Definition: a Baseball Roster Status Act that has a Baseball Team as agent
  and precedes a Loss of Role affecting a Player Role borne by a Person.
- **Baseball Player Release Decision ICE** - parent: Directive Information
  Content Entity. Definition: a Directive Information Content Entity that is
  output of a Baseball Player Release Act and is about the Player Role affected
  by its subsequent Loss of Role.
- **Free Agency Declaration Act** - parent: Baseball Roster Status Act.
  Definition: a Baseball Roster Status Act that has a Person as agent and
  precedes a Gain of Role affecting a Major League Free Agent Role inhering in
  that Person.
- **Free Agency Declaration Decision ICE** - parent: Directive Information
  Content Entity. Definition: a Directive Information Content Entity that is
  output of a Free Agency Declaration Act and is about the Major League Free
  Agent Role affected by its subsequent Gain of Role.
- **Retirement Declaration Act** - parent: Baseball Roster Status Act.
  Definition: a Baseball Roster Status Act that has a Person as agent and
  precedes a Loss of Role affecting an evidenced Player Role or Major League
  Free Agent Role inhering in that Person.
- **Retirement Decision ICE** - parent: Directive Information Content Entity.
  Definition: a Directive Information Content Entity that is output of a
  Retirement Declaration Act and is about the Role affected by its subsequent
  Loss of Role.

