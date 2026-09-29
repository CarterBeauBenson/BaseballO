# Existing award pattern for W1

All classes and relations below are already accepted. W1 introduces no terms.
The diagram describes the award's referents independently of provider row counts.

```mermaid
flowchart LR
  PA["Plate Appearance"] -->|"has occurrent part: BFO_0000117"| W["Walk Process"]
  W -->|"is cause of: cco:ont00001803"| R["Baserunning Act"]
  Rule["Applicable Baseball Rule / Process Regulation"] -->|"requires: cco:ont00001974"| R
  R -->|"is required by: cco:ont00001807"| Rule
  Record["Existing runner record"] -->|"is about: cco:ont00001808"| W
  Record -->|"is about: cco:ont00001808"| Rule
```

Existing Person agency, persistent Baserunner Role realization, runner resolution,
Safe judgment/decision, base and temporal structures remain their own accepted
patterns. They are prerequisites, not facts supplied by a VB counter sequence.
W1 adds only the missing award/rule links selected by the contract, including
their existing record provenance and rule identifiers.

A preceding mound visit and runner replacement are distinct from this award.
Their source records can establish that no pitch or count change occurred in
the prefix without becoming parts of the Walk Process or realizing its roles.
Four provider counter rows do not establish four judgments or four pitches.
