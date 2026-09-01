# Decision inventory

| Term or pattern | Disposition | Consequence |
| --- | --- | --- |
| `BaseballGame` | accepted existing-term repair | Change the direct named parent from CCO Planned Act to BFO Process and align the definition with the accepted overlay. |
| `BaseballAct` | accepted reuse | Keep Acts as occurrent parts of a Baseball Game. |
| `BaseballPhysicalProcess` | accepted reuse | Keep physical processes as occurrent parts of a Baseball Game. |
| `BaseballInstitutionalProcess` | accepted reuse | Keep institutional processes as occurrent parts of a Baseball Game. |
| `BaseballRule` | accepted reuse | A Rule may prescribe a Game; this does not determine the Game's process subtype. |
| `BaseballSeason` | draft-package correction only | Use BFO Process as the proposed parent; later implementation still requires acceptance of the complete MLB-organizations package. |
| `BaseballSeasonPhase` | draft-package correction only | Use BFO Process as the proposed parent and occurrent-part structure; later implementation remains blocked on complete package review. |
| `BaseballSeasonPlan` | draft-package correction only | Keep the Plan as a distinct Directive ICE that may prescribe Season processes. |
| `PlayerRole` and other team-scoped Occupation Roles | accepted reuse | Use `has organizational context` with a Baseball Team. |
| Stasis of Role | accepted reuse | Use the stasis and its Temporal Interval to represent persistence of the team-scoped Occupation Role. |
| `BaseballRosterMembershipRole` | rejected draft candidate | Remove it from the transaction proposal; it duplicates the intended team context already carried by Occupation Roles. |

No new object property is proposed or authorized.
