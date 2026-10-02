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
