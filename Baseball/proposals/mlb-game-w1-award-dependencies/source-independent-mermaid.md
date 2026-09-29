# W2: existing award dependencies (review only)

All classes, relations and identities shown are already accepted. The requested scope is their missing instances for a W1-selected runner row.

```mermaid
flowchart LR
  PA[Plate Appearance]
  W[Walk Process] -->|causes| A[Baserunning Act]
  A -->|has agent| P[Person]
  E[Runner Resolution Episode] -->|has occurrent part| A
  E -->|has occurrent part| S[Safe Process]
  E -->|occurrent part of| PA
  S -->|has occurrent part| J[Safe Judgment Act]
  J -->|has output| D[Safe Decision ICE]
  D -->|is about| B[Base: first-base artifact]
  R[Baseball Event Record] -->|is about| E
  R -->|is about| A
```

The world-side anchor is the accepted runner-award-origin final decision and its existing episode/agent/destination maps. This does not introduce a relation, universal, persistent occupancy or personal-history identity.
