# Source-independent shape

```mermaid
flowchart LR
  D[Baseball Position Description]
  P[Person]
  R[Fielder Role]
  F[Baseball Fielding Disposition]
  T[Throwing Side Disposition]

  D -->|is about| P
  D -->|is about| R
  D -->|is about| F
  D -. when evidenced .->|is about| T
  R -->|inheres in| P
  F -->|inheres in| P
  T -. when evidenced .->|inheres in| P
```

The description does not establish an exclusive outfield-only Role or kind.
