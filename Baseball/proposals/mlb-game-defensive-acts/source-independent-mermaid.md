# D1 world-side shape (review only)

```mermaid
flowchart LR
  Play["Batted Ball Play Process"]
  Act["Particular Fielding / Catch / Throw / Tag Attempt"]
  Person["Person acting as defender"]
  Role["Persistent Fielder Role"]
  Later["Separately supported later defensive Act"]
  Record["Baseball Event Record"]
  Act -->|"occurrent part of: BFO_0000132"| Play
  Act -->|"has agent: cco ont00001833"| Person
  Act -->|"realizes: BFO_0000055"| Role
  Role -->|"inheres in: BFO_0000197"| Person
  Act -.->|"precedes, only when supported: BFO_0000063"| Later
  Record -->|"is about: cco ont00001808"| Act
```

All labels resolve to accepted terms. The disjunction in the Act box is a
review illustration, not a new class. A catch and its Fielding Attempt
supertype identify one particular; separate throws have distinct identities.
Temporal precedence is not inferred from diagram placement or source order.
