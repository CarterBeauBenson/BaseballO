# Existing runner patterns; R1 review only

All classes, relations and identity policies are already accepted. The change
requested here is their targeted addition where selected existing games lack
the supported facts.

```mermaid
flowchart LR
  PA[Plate Appearance]
  H[Process: personal runner history] -->|has occurrent part| E[Runner Resolution Episode]
  H -->|occupies temporal region| T[One-Dimensional Temporal Region]
  H -->|has participant| P[Person]
  E -->|occurrent part of| PA
  E -->|has occurrent part| A[Baserunning Act]
  E -->|has occurrent part| O[Safe, Out or Run Process]
  A -->|has agent| P
  A -->|realizes| R[Baserunner Role]
  R -->|inheres in| P
  C[Batted Ball Play Process] -->|has occurrent part| O
  W[Walk or Hit By Pitch Process] -->|causes| A
  I[Baseball Event Record] -->|is about| E
  I -->|is about| A
```

The personal history is an instance of BFO Process (`BFO_0000015`), with a
One-Dimensional Temporal Region (`BFO_0000038`). The contact containment uses
`BFO_0000117`; the award cause uses `cco:ont00001803`; the explicit agent uses
`cco:ont00001833`. Alternatives identify the existing types selected by current
mappings, not proposed common superclasses. Contact containment and award
causation apply only when their respective existing selectors support them.
No placement, history or clock is asserted merely because a diagram contains
the corresponding node. Endpoint designations and identifiers reuse the
existing Safe Decision and segment-origin maps listed in the scope inventory.
