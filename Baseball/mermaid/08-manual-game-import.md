# Manual game import

This is the active operational path. NiFi observes only a local directory and makes no external HTTP request.

```mermaid
flowchart TB
    USER["Locally supplied game JSON"] --> INBOX["pipeline/inbox/games"]
    INBOX --> GET["NiFi GetFile"]
    GET --> NAME["Assign UUID staging filename"]
    NAME --> STAGE["Byte-identical local staging file"]
    STAGE --> IMPORT["import-game-json.ps1"]
    IMPORT --> HASH["SHA-256 content archive"]
    HASH --> RAW["raw/games/{season}/{gamePk}/{sha256}.json"]
    IMPORT --> MANIFEST["Separate manual-import manifest"]
    IMPORT --> FINAL{"Document state Final?"}
    FINAL -->|No| ARCHIVE["Archive without mapping"]
    FINAL -->|Yes| PREFLIGHT["Identity, collision, and source-shape preflight"]
    PREFLIGHT --> RML["Pinned RMLMapper"]
    RML --> VALIDATE["Turtle parse and source-count validation"]
    VALIDATE --> PUT["Fuseki named-graph PUT"]
    PUT --> GRAPH["graph/game/{gamePk}"]
    GET -->|Failure| Q["quarantine/manual-inbox"]
    IMPORT -->|Failure| Q

    classDef local fill:#e8f4ff,stroke:#2b6cb0;
    classDef guard fill:#fff8db,stroke:#b7791f;
    classDef storage fill:#e6fffa,stroke:#2c7a7b;
    classDef failure fill:#fff5f5,stroke:#c53030;
    class USER,INBOX,GET,NAME,STAGE local;
    class FINAL,PREFLIGHT,VALIDATE guard;
    class HASH,RAW,MANIFEST,ARCHIVE,GRAPH storage;
    class Q failure;
```

The source file is parsed for validation but never rewritten. Both the archive copy and the caller's original are checked against the pre-import SHA-256 hash.
