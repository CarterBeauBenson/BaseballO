# Event Process Chain

## Intended ontology-first chain

```mermaid
flowchart LR
    PLAYER["Player"] -->|"agent in"| SWING["Swing Act"]
    SWING -->|"precedes"| CONTACT["Bat-Ball Contact Process"]
    CONTACT -->|"precedes"| MOTION["Batted-Ball Motion Process"]
    CONTACT -->|"precedes"| RESULT["Institutional result process<br/>for example Home Run Process"]
    RECORD["Baseball Event Record"] -->|"is about"| RESULT

    classDef act fill:#d7f5df,stroke:#24733b,color:#102a18;
    classDef process fill:#e8eef9,stroke:#4f6fa8,color:#17233a;
    classDef ice fill:#fff2cc,stroke:#997a00,color:#3d3100;
    class SWING act;
    class CONTACT,MOTION,RESULT process;
    class RECORD ice;
```

## Explicit shape in the current RML

```mermaid
flowchart LR
    PITCH["Pitch Act"] -->|"precedes"| SWING["Swing Act"]
    SWING -->|"precedes"| CONTACT["Contact Process"]
    CONTACT -->|"precedes"| MOTION["Batted-Ball Motion"]
    CONTACT -->|"precedes"| RESULT["Generic or specifically typed result"]

    PA["Plate Appearance"] -->|"has occurrent part"| RESULT
    RESULT_RECORD["Result Event Record"] -->|"is about"| RESULT

    classDef present fill:#d7f5df,stroke:#24733b,color:#102a18;
    classDef gap fill:#fde2e2,stroke:#a33,color:#4a1111,stroke-dasharray:5 5;
    class PITCH,SWING,CONTACT,MOTION,PA,RESULT,RESULT_RECORD present;
```

The mapping makes the batter agent of the Swing Act rather than agent of the result. Contact processes are now explicitly connected to the enclosing plate-appearance result through the same source-backed `playId` join used elsewhere, using temporal precedence rather than causation.
