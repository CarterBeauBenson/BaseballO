# Daily game acquisition

This diagram describes the implemented operational path. NiFi schedules and observes the run; the guarded scripts preserve source bytes, enforce mapping preconditions, and load only validated RDF.

```mermaid
flowchart TB
    NIFI["NiFi 06:15 local trigger"] --> CMD["acquire-daily-games.ps1<br/>three-date lookback"]
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
    class SCHED,FEED source;
    class FINAL,PREFLIGHT,VALIDATE guard;
    class SRAW,SMAN,GRAW,GMAN,RUN,GRAPH storage;
    class Q,NQ failure;
```

The source JSON never receives helper fields. Root identifiers required by nested RML subjects are inserted only into an isolated mapping copy, and every run records the source and effective mapping hashes.
