# Existing world-side pattern; proposed boundary identification

```mermaid
flowchart LR
  Old["Outgoing person's personal Process"] -->|"BFO_0000057 has participant"| A["Person A"]
  New["Incoming person's distinct personal Process"] -->|"BFO_0000057 has participant"| B["Person B"]
  Old -->|"BFO_0000117 has occurrent part"| E1["A's supported Runner Resolution Episode"]
  New -->|"BFO_0000117 has occurrent part"| E2["B's supported Runner Resolution Episode"]
  Old -->|"BFO_0000132 occurrent part of"| Half["Half Inning"]
  New -->|"BFO_0000132 occurrent part of"| Half
  Old -->|"BFO_0000199 occupies temporal region"| T1["A's Temporal Interval"]
  New -->|"BFO_0000199 occupies temporal region"| T2["B's Temporal Interval"]
```

All nodes and relations use the accepted C1 vocabulary. No new replacement
relation connects the two Processes or Persons. Source evidence identifies
the end of one and beginning of the other. This picture does not assert
strict precedence between their full temporal extents. Placement uses the
same single-person pattern with independently supported later episodes.
