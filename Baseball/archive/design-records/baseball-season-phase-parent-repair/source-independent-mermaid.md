# Source-independent Mermaid

The solid chain is the accepted asserted hierarchy. The dotted edge is the
redundant direct assertion to remove.

```mermaid
flowchart BT
    PHASE[Baseball Season Phase]
    SEGMENT[Baseball Season Segment]
    PROCESS[BFO Process]

    PHASE -->|subclass of| SEGMENT
    SEGMENT -->|subclass of| PROCESS
    PHASE -. redundant direct assertion removed .-> PROCESS
```

After removal, a reasoner still entails that every Baseball Season Phase is a
BFO Process through Baseball Season Segment.
