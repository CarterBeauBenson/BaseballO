# Source-independent Mermaid

## Angle Quality

```mermaid
flowchart LR
    OBJECTS[Material entities, sites, or process history]
    LINE1[Fiat Line 1]
    LINE2[Fiat Line 2]
    POINT[Shared Fiat Point]
    ANGLE[Angle Quality\nRelational Quality]
    MICE[Angle Measurement ICE]
    UNIT[Angular Measurement Unit]
    REF[Spatial Reference System]

    OBJECTS -.->|source-specific grounding unresolved| LINE1
    OBJECTS -.->|source-specific grounding unresolved| LINE2
    LINE1 -->|has continuant part| POINT
    LINE2 -->|has continuant part| POINT
    ANGLE -->|inheres in| LINE1
    ANGLE -->|inheres in| LINE2
    MICE -->|is a measurement of| ANGLE
    MICE -->|uses measurement unit| UNIT
    MICE -->|uses reference system| REF
```

The dotted grounding edges are deliberately unresolved and do not propose an
object property. A source-specific design must replace them with accepted
relations supported by the relevant material geometry. Unit and reference
system edges depend on prior acceptance of `ice-direct-values-and-units`.

## Distance Quality

```mermaid
flowchart LR
    RELATUM1[Material entity or site 1]
    RELATUM2[Material entity or site 2]
    POINT1[Fiat Point 1]
    POINT2[Fiat Point 2\nnonidentical]
    DIST[Distance Quality\nRelational Quality]
    MICE[Distance Measurement ICE]
    UNIT[Linear Measurement Unit]
    REF[Spatial Reference System]

    RELATUM1 -.->|source-specific grounding unresolved| POINT1
    RELATUM2 -.->|source-specific grounding unresolved| POINT2
    DIST -->|inheres in| POINT1
    DIST -->|inheres in| POINT2
    MICE -->|is a measurement of| DIST
    MICE -->|uses measurement unit| UNIT
    MICE -->|uses reference system| REF
```

## Explicitly unresolved directed component

```mermaid
flowchart LR
    P1[Intercept Fiat Point]
    P2[Center-of-Mass Fiat Point]
    AXIS[Coordinate System Axis]
    GAP[Unresolved signed displacement quality]
    MICE[Signed component Measurement ICE]

    P1 -. required relatum .-> GAP
    P2 -. required relatum .-> GAP
    AXIS -. required direction and sign convention .-> GAP
    MICE -. blocked until world-side account is accepted .-> GAP
```
