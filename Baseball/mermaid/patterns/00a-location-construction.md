# Shared act-location construction

```mermaid
flowchart LR
    RAW["Raw game root<br/>gameData.venue.id"] --> HARNESS["run-rml.ps1<br/>resolves root marker only in<br/>temporary effective mapping"]

    HARNESS --> ACTMAP["Batter, Pitch, Swing, or Runner Act map"]
    ACTMAP --> ACT["Act individual"]
    ACT -->|"occurs at<br/>cco:ont00001918"| FIELDIRI["/venue/{venue.id}/baseball-field"]

    RAW --> VENUESOURCE["VenueSource<br/>$.gameData.venue"]
    VENUESOURCE --> FIELDMAP["BaseballFieldSiteMap"]
    FIELDMAP --> FIELD["same /venue/{id}/baseball-field IRI<br/>a BaseballFieldSite"]
    FIELDIRI -.->|"IRI equality merges nodes"| FIELD

    VENUESOURCE --> VENUEMAP["VenueMap"]
    VENUEMAP --> VENUE["/venue/{id}<br/>a BaseballVenue"]
    FIELD -->|"located in<br/>BFO_0000171"| VENUE

    FIELD -.->|"no finer site asserted"| COARSE["Whole-field location only"]

    classDef source fill:#e8eef9,stroke:#4f6fa8,color:#17233a;
    classDef act fill:#d7f5df,stroke:#24733b,color:#102a18;
    classDef location fill:#f3e8ff,stroke:#805ad5,color:#2d1b4e;
    classDef gap fill:#fde2e2,stroke:#a33,color:#4a1111,stroke-dasharray:5 5;
    class RAW,HARNESS,ACTMAP,VENUESOURCE,FIELDMAP,VENUEMAP source;
    class ACT act;
    class FIELDIRI,FIELD,VENUE location;
    class COARSE gap;
```

## Evaluation

Every mapped act uses the same location design. The act map does not join to
`BaseballFieldSiteMap`; it constructs the expected field-site IRI directly.
`BaseballFieldSiteMap` independently emits that same IRI from `VenueSource`, so
RDF identity joins the references.

For nested play, pitch, and runner sources, `$.gameData.venue.id` is not local
to the iterator record. The execution harness resolves the audited root marker
in a temporary mapping copy. This is an implementation dependency, not source
mutation.

The relation directions are sound, but the location is coarse: every act
occurs at the entire baseball-field site. Base sites, fair/foul territory, the
mound, and home plate are not selected from the current source mapping.
