# Source-independent Mermaid

```mermaid
flowchart TB
    SEASON[Baseball Season\nProcess]
    SEGMENT[Baseball Season Segment\nProcess]
    PHASE[Baseball Season Phase\ncontains some Baseball Game]
    PRE[Baseball Preseason Phase]
    REG[Baseball Regular Season Phase]
    POST[Baseball Postseason Phase]
    ALLSTAR[Baseball All-Star Phase]
    OFF[Baseball Offseason Segment\nno Game required]
    OFFTIME[Temporal Interval occupied by\nBaseball Offseason Segment]
    QUIET[Major League Free-Agent Quiet Period]
    SICE[Reusable Season-Segment\nNominal Measurement ICE]
    SSYS[Versioned MLB Season-Segment\nReference System]

    SEGMENT -->|occurrent part of| SEASON
    PHASE -->|subclass of| SEGMENT
    PRE -->|subclass of| PHASE
    REG -->|subclass of| PHASE
    POST -->|subclass of| PHASE
    ALLSTAR -->|subclass of| PHASE
    OFF -->|subclass of| SEGMENT
    OFF -->|occupies temporal region| OFFTIME
    QUIET -->|interval contained by| OFFTIME
    SEGMENT -->|is measured by nominal| SICE
    SICE -->|uses reference system| SSYS
```

```mermaid
flowchart TB
    TX[Baseball Transaction Period\nTemporal Interval]
    QUIET[Major League Free-Agent Quiet Period]
    OPEN[Major League Open Free-Agency Period]
    ARB[Major League Salary-Arbitration Period]
    INTL[Major League International Signing Period]
    OFFTIME[Temporal Interval occupied by\nBaseball Offseason Segment]
    PLAYTIME[Temporal Interval occupied by a\npreseason or playing-season Process]
    ACT[Transaction Act Process]
    ACTTIME[Temporal Interval occupied by\nthe Transaction Act]
    RULE[Baseball Rule]
    IDENTIFIER[Temporal Interval Identifier]
    TICE[Reusable Transaction-Period\nNominal Measurement ICE]
    TSYS[Versioned MLB Transaction-Calendar\nReference System]

    QUIET -->|subclass of| TX
    OPEN -->|subclass of| TX
    ARB -->|subclass of| TX
    INTL -->|subclass of| TX
    QUIET -->|interval contained by| OFFTIME
    OPEN -.->|may overlap| OFFTIME
    ARB -.->|may overlap| PLAYTIME
    INTL -.->|may overlap| PLAYTIME
    TX -->|is subject of| RULE
    TX -->|is designated by| IDENTIFIER
    RULE -->|prescribes| ACT
    ACT -->|occupies temporal region| ACTTIME
    ACTTIME -->|interval contained by| TX
    TX -->|is measured by nominal| TICE
    TICE -->|uses reference system| TSYS
```

Dashed overlap edges are review explanations, not proposed object properties.
Executable temporal claims must use occupied Temporal Regions and accepted
interval relations.
