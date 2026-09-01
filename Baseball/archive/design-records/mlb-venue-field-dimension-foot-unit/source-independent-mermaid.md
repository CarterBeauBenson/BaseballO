# Accepted unit shape and retained geometry gate

Solid edges are accepted. Dotted edges mark source-specific grounding that
remains unresolved and therefore cannot appear in RML yet.

```mermaid
flowchart LR
    RELATUM1[Material entity or site 1]
    RELATUM2[Material entity or site 2]
    POINT1[Fiat Point 1]
    POINT2[Fiat Point 2]
    DIST[Distance Quality]
    MICE[Distance Measurement ICE]
    VALUE[Decimal literal]
    FOOT[CCO Foot Measurement Unit\ncco:ont00001714]

    RELATUM1 -.->|exact grounding unresolved| POINT1
    RELATUM2 -.->|exact grounding unresolved| POINT2
    DIST -->|inheres in| POINT1
    DIST -->|inheres in| POINT2
    MICE -->|is a measurement of| DIST
    MICE -->|has decimal value| VALUE
    MICE -->|uses measurement unit| FOOT
```

The shape applies to each of the five MLB field-dimension values. A later
source-specific Mermaid must replace both dotted groundings and state the
configuration and effective-time policy before executable mapping.
