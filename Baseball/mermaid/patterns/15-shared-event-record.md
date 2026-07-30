# Shared pitch event record

```mermaid
flowchart TB
    SOURCE["One playEvents[*] pitch object<br/>identified by playId"] --> RECORDMAP["PitchEventRecordMap"]
    RECORDMAP --> RECORD["/event-record/pitch/{playId}<br/>a BaseballEventRecord"]
    RECORD -->|"dcterms:identifier"| PLAYID["playId"]
    RECORD -->|"descriptive text"| DESCRIPTION["details.description"]

    RECORD -->|"is about: always"| PITCH["PitchAct"]
    RECORD -->|"is about: S/F/T/X/D/E"| SWING["SwingAct"]
    RECORD -->|"is about: B/*B/C/S/F/T"| CALL["BallProcess or StrikeProcess"]
    RECORD -->|"is about: F/T/X/D/E"| CONTACT["BatBallContactProcess"]
    RECORD -->|"is about: F"| FOUL["FoulBallProcess"]
    RECORD -->|"is about: T"| TIP["FoulTipProcess"]
    RECORD -->|"is about: X/D/E"| FAIR["FairBallProcess"]
    RECORD -->|"is about: hitData present"| MOTION["BattedBallMotionProcess"]

    RECORD -.->|"one record is not one mapped entity"| MANY["Many-about record pattern"]

    classDef source fill:#e8eef9,stroke:#4f6fa8,color:#17233a;
    classDef record fill:#f3e8ff,stroke:#805ad5,color:#2d1b4e;
    classDef act fill:#d7f5df,stroke:#24733b,color:#102a18;
    classDef process fill:#fff2cc,stroke:#997a00,color:#3d3100;
    class SOURCE,RECORDMAP source;
    class RECORD,MANY record;
    class PITCH,SWING act;
    class CALL,CONTACT,FOUL,TIP,FAIR,MOTION process;
```

## Evaluation

The repeated `*RecordAboutMap` triples all reuse the same event-record IRI.
That is coherent if the MLB pitch object is interpreted as one compound source
record describing several distinct aspects of an event. It would be incorrect
to assume one event record identifies exactly one act or process.

This shared node sometimes supplies the only explicit connection between
parallel institutional processes—for example, the foul-ball and strike
processes created from the same `F` call. Whether that is sufficient should be
decided separately from record identity.
