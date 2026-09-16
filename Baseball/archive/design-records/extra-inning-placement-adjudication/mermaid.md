# Decision diagrams before executable mapping

These render the user's named placement decision using the existing C1 whole
and accepted adjudication pattern; they introduce no new class or relation.

```mermaid
flowchart LR
  H[Personal BFO Process] -->|has occurrent part| J[Baseball Adjudication Act]
  H -->|has participant| P[Person]
  H -->|is occurrent part of| I[Half Inning]
  J -->|is prescribed by| R[Baseball Rule]
  J -->|has output| D[Baseball Decision ICE]
  D -->|is about| H
  D -->|is about| P
  D -->|is about| B[Second Base]
  H -->|has occurrent part, when evidenced| E[Runner Resolution Episode]
```

```mermaid
flowchart LR
  S[MLB runner_placed action] -->|C3 reconciliation| A[placement / inning / half / Person anchor]
  A -->|stable game-scoped identity| J[Distinct placement judgment and decision]
  A -->|existing lifetime hash| H[Personal process]
  S -->|source record is about| J
  M[Independent runner movement rows] -->|existing selection| E[Movement episodes only]
  E -->|existing membership| H
  O[Reconciled third out] -->|existing termination anchor| H
```
