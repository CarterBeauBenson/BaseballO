# Daily scheduled external game acquisition

The user-authorized acquisition runs every day at 05:00 Eastern inside the
source-owned `MLB Game` NiFi group. It does not require an attached monitor.

```mermaid
flowchart TB
    APPROVAL["Explicit user authorization"] --> TRIGGER["NiFi daily 05:00 Eastern trigger"]
    TRIGGER --> DATES["Prior Eastern calendar day"]
    DATES --> RELEASE["Require current bounded proof"]
    RELEASE --> SCHED["MLB v1 schedule"]
    SCHED --> STEMP["Transient schedule FlowFile"]
    STEMP --> FINAL["Validate response and select Final games"]
    FINAL --> BATCH["Compact expected-game batch manifest"]
    FINAL --> SPLIT["One request per final game"]
    SPLIT --> FEED["MLB v1.1 feed/live"]
    FEED --> GSTAGE["Transient exact game JSON"]
    GSTAGE --> RML["Source-owned RML"]
    RML --> SHACL["Source-owned SHACL"]
    SHACL --> PROMOTE["Recoverable authoritative/index promotion"]
    PROMOTE --> EVIDENCE["Immutable promotion evidence"]
    EVIDENCE --> CLEAN["Delete transient game JSON and serialized RDF"]
    TIMER["NiFi pending-batch check<br/>every 15 minutes"] --> READY{"All expected games promoted<br/>after batch creation?"}
    BATCH --> READY
    EVIDENCE --> READY
    READY -->|No| WAIT["Return; check later"]
    READY -->|Yes| SQL["Run approved SPARQL once<br/>and atomically promote SQLite build"]
    SCHED -->|Failure| SQ["source-local schedule quarantine"]
    RML -->|Failure after retries| GQ["source-local game quarantine"]
    SHACL -->|Failure after retries| GQ
    PROMOTE -->|Failure after retries| GQ

    classDef source fill:#e8f4ff,stroke:#2b6cb0;
    classDef guard fill:#fff8db,stroke:#b7791f;
    classDef storage fill:#e6fffa,stroke:#2c7a7b;
    classDef failure fill:#fff5f5,stroke:#c53031;
    class SCHED,FEED source;
    class RELEASE,FINAL,READY guard;
    class STEMP,BATCH,GSTAGE,PROMOTE,EVIDENCE,CLEAN,SQL storage;
    class SQ,GQ failure;
    class APPROVAL,TRIGGER,DATES,TIMER guard;
```

The source JSON never receives helper fields. Root identifiers required by
nested RML subjects are inserted only into an isolated mapping copy, and every
run records the source and effective mapping hashes. The schedule response is
not persisted as raw JSON; only its hash, date range, and expected final-game
identifiers remain in the compact batch manifest. A game response is discarded
only after successful graph-pair promotion and cleanup evidence.
