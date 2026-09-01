# Accepted source-independent shapes

```mermaid
flowchart LR
    MOTION[Ball Motion Process]
    RELEASE[Release-local Speed Process Profile]
    PLATE[Plate-crossing Speed Process Profile]
    CONTACT[Post-contact Speed Process Profile]
    VECTOR[Framed Velocity Process Profile]
    MEAS[Measurement ICE]
    FRAME[Reference System ICE]

    MOTION -->|has occurrent part| RELEASE
    MOTION -->|has occurrent part| PLATE
    MOTION -->|has occurrent part| CONTACT
    MOTION -->|has occurrent part| VECTOR
    MEAS -->|is a measurement of| RELEASE
    MEAS -->|uses reference system| FRAME
```

```mermaid
flowchart LR
    TYPE[Reusable Nominal Measurement ICE]
    SYSTEM[Versioned provider Reference System]
    ACT[Particular Pitch or Batted-Ball Act]
    MOTION[Resulting Ball Motion Process]

    TYPE -->|uses reference system| SYSTEM
    TYPE -->|is a nominal measurement of| ACT
    ACT -->|precedes| MOTION
```

```mermaid
flowchart TB
    OFF[Offseason Process]
    QUIET[Free-Agent Quiet Period]
    OPEN[Open Free-Agency Period]
    ARB[Salary-Arbitration Period]
    INTL[International Signing Period]
    EVENTS[Qualifying offers, tenders, meetings, drafts, and exchanges]

    OFF -->|has occurrent part| QUIET
    OFF -->|has occurrent part| OPEN
    OFF -->|has occurrent part| ARB
    OFF -->|has occurrent part| INTL
    EVENTS -.->|temporal-region placement| OFF
```

The last edge is explanatory diagram notation, not a proposed object property.
Executable RDF must express temporal placement with accepted relations and
Temporal Regions.
