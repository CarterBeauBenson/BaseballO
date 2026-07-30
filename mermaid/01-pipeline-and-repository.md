# Pipeline and Repository

## Active data flow

```mermaid
flowchart LR
    SCHEDULE["MLB daily schedule"] --> API["MLB Stats API<br/>/feed/live"]
    API --> RAW["Immutable untouched JSON"]
    RAW --> RML["mappings/direct/<br/>mlb-direct.rml.ttl"]
    RML --> TURTLE["Validated Turtle RDF"]
    TURTLE --> FUSEKI["Jena Fuseki / TDB2"]
    FUSEKI --> QUERY["Reviewed canned SPARQL"]
    QUERY --> SITE["GitHub Pages interface"]

    ENRICH["No flattening<br/>No normalization<br/>No helper fields"] -. prohibited .-> RML

    classDef active fill:#d7f5df,stroke:#24733b,color:#102a18;
    classDef future fill:#e8eef9,stroke:#4f6fa8,color:#17233a;
    classDef prohibited fill:#fde2e2,stroke:#a33,color:#4a1111;
    class SCHEDULE,API,RAW,RML,TURTLE,FUSEKI active;
    class QUERY,SITE future;
    class ENRICH prohibited;
```

## Repository roles

```mermaid
flowchart TB
    ROOT["BaseballO repository"]
    ROOT --> ONT["ontology/<br/>active TBox"]
    ROOT --> MAP["mappings/"]
    MAP --> DIRECT["direct/<br/>active RML"]
    MAP --> POLICY["policies/<br/>approved modeling and IRIs"]
    ROOT --> SCHEMA["source-schema/<br/>observed source contract"]
    ROOT --> MERMAID["mermaid/<br/>mapping review"]
    ROOT --> DATA["data/raw/<br/>untouched development feed"]
    ROOT --> SCRIPTS["scripts/<br/>active acquisition and operations"]
    ROOT --> FUTURE["sparql, web, tests<br/>planned stages"]
    ROOT --> ARCHIVE["archive/<br/>preprocessing prototype and prior ontology"]

    POLICY -->|"governs"| DIRECT
    ONT -->|"supplies classes and relations"| DIRECT
    SCHEMA -->|"describes JSON paths"| DIRECT
    DATA -->|"development input"| DIRECT

    classDef active fill:#d7f5df,stroke:#24733b,color:#102a18;
    classDef reference fill:#fff2cc,stroke:#997a00,color:#3d3100;
    classDef archive fill:#eeeeee,stroke:#777,color:#333;
    class ONT,DIRECT,SCRIPTS active;
    class POLICY,SCHEMA,MERMAID,DATA reference;
    class ARCHIVE archive;
```

The archived Stage 1 prototype is intentionally outside the active path because it enriches the input before mapping.
