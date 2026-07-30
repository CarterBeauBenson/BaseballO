# Triples-Map Families

All 121 triples maps are represented below as five functional families. Counts are derived from the current RML file.

```mermaid
flowchart LR
    SOURCE["37 logical sources"]

    SOURCE --> CONTEXT["Context and identity<br/>24 maps"]
    SOURCE --> PLAY["Play hierarchy and results<br/>27 maps"]
    SOURCE --> PITCH["Pitch-event structures<br/>53 maps"]
    SOURCE --> RUNNER["Runner structures<br/>16 maps"]
    SOURCE --> FIELDING["Fielding role trigger<br/>1 map"]

    CONTEXT --> C1["Game, teams, venue, people,<br/>roles, identifiers, names"]
    PLAY --> C2["Inning, half inning, plate appearance,<br/>time, generic and specific results"]
    PITCH --> C3["Pitch act and record, calls, swing,<br/>contact, fair/foul, batted-ball motion"]
    RUNNER --> C4["Baserunning act, resolution process,<br/>event record, safe/out/run"]
    FIELDING --> C5["Career FielderRole only"]

    C1 --> RDF["Ontology-aligned RDF"]
    C2 --> RDF
    C3 --> RDF
    C4 --> RDF
    C5 --> RDF

    classDef source fill:#e8eef9,stroke:#4f6fa8,color:#17233a;
    classDef mapped fill:#d7f5df,stroke:#24733b,color:#102a18;
    classDef partial fill:#fff2cc,stroke:#997a00,color:#3d3100;
    class SOURCE source;
    class CONTEXT,PLAY,PITCH,RUNNER mapped;
    class FIELDING,C5 partial;
```

## Map-count accounting

| Family | Count | Included logical-source groups |
| --- | ---: | --- |
| Context and identity | 24 | root, teams, venue, players, officials |
| Play hierarchy and results | 27 | canonical plays, last play, eleven filtered result types |
| Pitch-event structures | 53 | all pitches, batted pitches, and pitch-call filters |
| Runner structures | 16 | generic runner source and five outcome filters |
| Fielding | 1 | fielding-credit records used only to trigger Fielder Roles |
| **Total** | **121** | |

The large pitch family is deliberate reuse of source records for distinct process individuals, but it makes pitch call-code coverage and event-chain review especially important.
