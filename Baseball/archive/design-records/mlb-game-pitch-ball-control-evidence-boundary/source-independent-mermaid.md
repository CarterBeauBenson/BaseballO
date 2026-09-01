# Source-independent evidence boundary

```mermaid
flowchart LR
    RECORD["Scoring classification record"] -->|is about| JUDGMENT["Scorer judgment act"]
    JUDGMENT -->|has output| DECISION["Scoring decision ICE"]
    JUDGMENT -->|occurrent part of| INSTITUTIONAL["Passed-ball or wild-pitch process"]
    INSTITUTIONAL -->|prescribed by| RULE["Baseball rule"]
    RECORD -. "does not establish" .-> PHYSICAL["Pitch-ball control failure process"]
```

The dotted edge is a prohibition, not an RDF assertion. A future source may support the physical process independently, but the MLB-game scoring classification does not.
