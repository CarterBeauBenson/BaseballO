# Existing award pattern reused by W3

All terms are already accepted. The two result alternatives use their existing
classes; neither creates a new common superclass or relation.

```mermaid
flowchart LR
  PA["Plate Appearance"] -->|"has occurrent part: BFO_0000117"| Result["Walk Process OR Hit By Pitch Process"]
  Result -->|"is cause of: cco:ont00001803"| Run["Baserunning Act"]
  Rule["Applicable Baseball Rule / Process Regulation"] -->|"requires: cco:ont00001974"| Run
  Run -->|"is required by: cco:ont00001807"| Rule
  Record["Existing runner record"] -->|"is about: cco:ont00001808"| Result
  Record -->|"is about: cco:ont00001808"| Rule
```

The selected runner act retains its existing agent, persistent Baserunner Role,
resolution, Safe judgment/decision, destination and temporal dependencies.
An earlier pitch, steal, timer judgment, substitution or placement remains a
distinct event. A completed review supports the final operative award; this
selection does not assert the review's earlier call or new judgment identity.
Provider counters do not establish multiple actual pitches or judgments.
