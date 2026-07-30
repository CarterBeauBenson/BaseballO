# Runner scores from an origin state

```mermaid
flowchart LR
    SOURCE["RunnerScoreOriginSource<br/>not out; end = score;<br/>start is not 1B, 2B, or 3B"] --> ACTMAP["RunnerScoreOriginActMap"]
    SOURCE --> RESMAP["RunnerScoreOriginResolutionMap"]
    SOURCE --> RECORDMAP["RunnerScoreOriginRecordMap"]

    ACTMAP --> ACT["/runner-act/score/{runner}/{playIndex}/{eventType}/origin<br/>a BaserunningAct"]
    ACT -->|"has agent"| RUNNER["Runner person"]
    ACT -->|"realizes"| ROLE["BaserunnerRole"]
    ROLE -->|"inheres in"| RUNNER
    ACT -->|"occurs at"| FIELD["BaseballFieldSite"]
    ACT -->|"occurrent part of"| GAME["BaseballGame"]

    RESMAP --> RUN["/runner-resolution/score/{same key}/origin<br/>a RunnerResolutionProcess<br/>a RunProcess"]
    RUN -->|"asserted: preceded by"| ACT
    RUN -->|"has participant"| RUNNER
    RUN -->|"occurs at"| FIELD
    RUN -->|"occurrent part of"| GAME

    RECORDMAP --> RECORD["/runner-record/score/{same key}/origin"]
    RECORD -->|"is about"| RUN
    RECORD -->|"dcterms:identifier"| TYPE["details.eventType"]
    FIELD -->|"located in"| VENUE["BaseballVenue"]

    ACT -.->|"no plate-appearance link"| PA["PlateAppearance"]
    ACT -.->|"score embedded in act IRI"| BAKED["Outcome-dependent act identity"]

    classDef source fill:#e8eef9,stroke:#4f6fa8,color:#17233a;
    classDef act fill:#d7f5df,stroke:#24733b,color:#102a18;
    classDef outcome fill:#fff2cc,stroke:#997a00,color:#3d3100;
    classDef gap fill:#fde2e2,stroke:#a33,color:#4a1111,stroke-dasharray:5 5;
    class SOURCE,ACTMAP,RESMAP,RECORDMAP source;
    class ACT act;
    class RUN,RECORD outcome;
    class PA,BAKED gap;
```

## Evaluation

This branch exists because the runner record lacks a normal base in
`movement.start`. It uses the literal path segment `origin` to keep the
composite identity distinct. The act/result separation is semantically useful,
but `/score/` still makes the act identity dependent on its successful outcome.
The broad filter also groups every non-1B/2B/3B start value into one origin
pattern and therefore deserves testing against more source shapes.
