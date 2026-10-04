# Existing personal-history pattern

This repeats the accepted C1/C3 structure; it introduces no term or relation.

```mermaid
flowchart LR
  History[Personal Process] -->|"has participant: BFO_0000057"| Person[Person]
  History -->|"occurrent part of: BFO_0000132"| Half[Half Inning]
  History -->|"occupies temporal region: BFO_0000199"| Interval[Temporal Interval]
  History -->|"has occurrent part: BFO_0000117"| Episode[Runner Resolution Episode]
  Episode -->|"has occurrent part: BFO_0000117"| Running[Baserunning Act]
  Episode -->|"has occurrent part: BFO_0000117"| Out[Out Process]
```

The reviewed final pitch/count or pickoff evidence selects existing episodes
and their personal whole. The C3 boundary token is a serialization identity,
not a new node or relation. Neither a review nor an associated pitch is made
part of this runner history merely because it supports source reconciliation.
