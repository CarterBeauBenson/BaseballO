# Existing world-side pattern for review

All nodes are instances of accepted classes. Relations use accepted BFO/CCO
terms; arrows do not introduce predicates or a new identity criterion.

```mermaid
flowchart LR
  PA[Plate Appearance]
  P[Pitch Act]
  F[Foul Ball Process]
  S[Strike Process]
  J[Strike Judgment Act]
  D[Strike Decision ICE]
  R[Strike Rule]
  E[Baseball Event Record]
  P -->|occurrent part of| PA
  F -->|occurrent part of| PA
  S -->|occurrent part of| PA
  S -->|has occurrent part| J
  J -->|has input| R
  J -->|has output| D
  D -->|is about| S
  E -->|is about| P
  E -->|is about| F
  E -->|is about| S
  E -->|is about| J
  E -->|is about| D
```

The full existing physical/contact, location, participation and rule pattern
remains in effect; this diagram identifies the counted-strike portion being
selected. M4 additionally requires the existing actual Bunt Attempt Act and
contact structure. Neither a source count nor a review record replaces these
world-side processes. No separate-event order follows from this diagram.

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
