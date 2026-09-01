# Direct game import fallback

This is a focused developer fallback and parity path, not an active NiFi
inbox. It reads a local completed-game response and makes no external HTTP
request. Routine acquisition uses the source-owned `MLB Game` NiFi group.

```mermaid
flowchart TB
    USER["Locally supplied completed-game JSON"] --> IMPORT["import-game-json.ps1"]
    IMPORT --> HASH["Verify and archive<br/>byte-identical source"]
    HASH --> FINAL{"Document state Final?"}
    FINAL -->|No| ARCHIVE["Archive only"]
    FINAL -->|Yes| PREFLIGHT["Dependency, identity, collision,<br/>and source-shape preflight"]
    PREFLIGHT --> RML["Pinned RMLMapper"]
    RML --> VALIDATE["Turtle parse, source counts,<br/>and authoritative SHACL"]
    VALIDATE --> LOAD{"ForceRdfLoad?"}
    LOAD -->|No| RDF["Validated local RDF"]
    LOAD -->|Yes| PUT["Fuseki named-graph PUT"]
    PUT --> INDEX["Build, SHACL-check,<br/>and compare query index"]
    INDEX --> GRAPH["Authoritative/index graph pair"]
    PREFLIGHT -->|Failure| FAIL["Developer command fails closed"]

    classDef local fill:#e8f4ff,stroke:#2b6cb0;
    classDef guard fill:#fff8db,stroke:#b7791f;
    classDef storage fill:#e6fffa,stroke:#2c7a7b;
    classDef failure fill:#fff5f5,stroke:#c53031;
    class USER,IMPORT local;
    class FINAL,PREFLIGHT,VALIDATE,LOAD guard;
    class HASH,ARCHIVE,RDF,PUT,INDEX,GRAPH storage;
    class FAIL failure;
```

The source file is parsed for validation but never rewritten. The archive copy
and caller's original are checked against the pre-import SHA-256 hash. This
command does not substitute for NiFi scheduling, proof release, retry,
quarantine, provenance, or corpus materialization.
