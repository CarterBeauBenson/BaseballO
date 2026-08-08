# Guarded external game acquisition

The command-line acquisition path runs only when the caller supplies explicit
external-data approval. The unattended NiFi schedule remains disabled and is
not implied by a manually approved acquisition run.

```mermaid
flowchart TB
    APPROVAL["Explicit caller approval"] --> CMD["acquire-daily-games.ps1<br/>date or guarded lookback"]
    PARKED["Unattended NiFi schedule disabled"] -.-> NIFI["NiFi 06:15 local trigger"]
    NIFI -.-> CMD
    CMD --> SCHED["MLB v1 schedule"]
    SCHED --> SRAW["raw/schedules/{date}/{sha256}.json"]
    SCHED --> SMAN["schedule acquisition manifest"]
    SCHED --> FINAL{"Schedule state Final?"}
    FINAL -->|No| SKIP["Do not request or map"]
    FINAL -->|Yes| FEED["MLB v1.1 feed/live"]
    FEED --> GRAW["raw/games/{season}/{gamePk}/{sha256}.json"]
    FEED --> GMAN["game acquisition manifest"]
    GRAW --> PREFLIGHT["Final state, identity, collision,<br/>and source-shape preflight"]
    PREFLIGHT --> RML["Pinned RMLMapper"]
    RML --> VALIDATE["Turtle parse plus game,<br/>plate-appearance, and pitch counts"]
    VALIDATE --> PUT["Fuseki named-graph PUT"]
    PUT --> GRAPH["graph/game/{gamePk}"]
    CMD --> RUN["daily run summary"]
    CMD -->|Failure| Q["quarantine/acquisition"]
    NIFI -->|Non-zero output| NQ["quarantine/nifi/games-daily"]

    classDef source fill:#e8f4ff,stroke:#2b6cb0;
    classDef guard fill:#fff8db,stroke:#b7791f;
    classDef storage fill:#e6fffa,stroke:#2c7a7b;
    classDef failure fill:#fff5f5,stroke:#c53030;
    classDef parked fill:#f3f4f6,stroke:#4b5563,stroke-dasharray: 5 5;
    class SCHED,FEED source;
    class FINAL,PREFLIGHT,VALIDATE guard;
    class SRAW,SMAN,GRAW,GMAN,RUN,GRAPH storage;
    class Q,NQ failure;
    class PARKED,NIFI parked;
    class APPROVAL,CMD guard;
```

The source JSON never receives helper fields. Root identifiers required by nested RML subjects are inserted only into an isolated mapping copy, and every run records the source and effective mapping hashes.
