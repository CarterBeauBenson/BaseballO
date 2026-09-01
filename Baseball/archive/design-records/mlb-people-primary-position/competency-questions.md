# Competency questions

| ID | Question | Candidate answer |
| --- | --- | --- |
| POSITION-01 | What is a baseball position? | A Baseball Position Description: a Descriptive ICE about a Person and one or more Roles, Dispositions, or Qualities borne by that Person. |
| POSITION-02 | Is the position itself a Role? | No. Roles and Dispositions are real members of the described cluster; the position description is about them and their bearer. |
| POSITION-03 | What does `primary` establish? | The provider's selected summary description at the response grain. It does not establish that every Game realizes the cluster or that the description held for the Person's whole career. |
| POSITION-04 | What minimum clusters are supported? | Pitcher descriptions concern Pitcher Role and Throwing Side Disposition; Catcher descriptions concern Catcher Role, Baseball Fielding Disposition, and Throwing Side Disposition; other fielding descriptions concern Fielder Role, Baseball Fielding Disposition, and Throwing Side Disposition; designated-hitter descriptions concern Batter Role and Batting Side Disposition. |
| POSITION-05 | How are game observations used? | Game Acts may realize the relevant Role or Disposition and may corroborate or conflict with the provider description without being inferred for every Game. |
| POSITION-06 | What happens for composite or unsupported codes? | A source-specific reviewed table must state the exact cluster. Unknown codes quarantine; no free-text inference or code-shaped Role class is permitted. |

## Negative tests

- A Baseball Position Description never realizes a Role or Disposition.
- A position code never types the Person as a position.
- `primaryPosition` does not create a team-stint boundary.
- The people source does not invent Player Acts.
- Position-specific ICE subclasses are admitted only for source-independent
  baseball position concepts, never mechanically per provider field.
