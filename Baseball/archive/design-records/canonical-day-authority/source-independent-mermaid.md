# Source-independent Mermaid

```mermaid
flowchart LR
    PREV[Earlier canonical Day]
    DAY[Canonical Day]
    NEXT[Later canonical Day]
    DATE[Calendar Date Identifier]
    PROCESS[Date-bounded Process or Stasis]
    REGION[Process Temporal Region]
    SOURCE[Source record ICE]
    GRAPH[Source-owned daily named graph\noperational container]

    PREV -->|precedes| DAY
    DAY -->|precedes| NEXT
    DATE -->|designates| DAY
    PROCESS -->|occupies temporal region| REGION
    REGION -->|temporal part of| DAY
    SOURCE -->|has continuant part| DATE
    GRAPH -.->|contains RDF assertions about| PROCESS
```

The dotted graph edge is operational notation, not an ontology property. Days
remain source-neutral. Each source lane owns its own daily graph product; the
triple store is the integration boundary.

