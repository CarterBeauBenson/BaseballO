# Source-specific Mermaid

Status: **under review — design only**

Solid edges form a candidate using existing vocabulary. Dotted lines expose
remaining identity and temporal questions; they do not propose relations.

## Actual player-Site structure and Stasis

```mermaid
flowchart LR
    FIELD[Baseball Field Site]
    SITEA[Field-relative Site A]
    SITEB[Field-relative Site B]
    FIELDERA[Fielder Person A]
    FIELDERB[Fielder Person B]
    STASIS[Generic Stasis]
    INTERVAL[Temporal Interval]
    PITCH[Pitch Act]
    SITEQ[QUESTION\nWhat evidence identifies Sites and\nrelative geometry?]
    TIMEQ[QUESTION\nHow does the alignment interval relate\nto setup, release, and the Pitch Act?]

    FIELD -->|has continuant part| SITEA
    FIELD -->|has continuant part| SITEB
    FIELDERA -->|located in| SITEA
    FIELDERB -->|located in| SITEB
    FIELDERA -->|participates in| STASIS
    FIELDERB -->|participates in| STASIS
    SITEA -->|participates in| STASIS
    SITEB -->|participates in| STASIS
    STASIS -->|occupies temporal region| INTERVAL
    SITEA -.-> SITEQ
    SITEB -.-> SITEQ
    INTERVAL -.-> TIMEQ
    PITCH -.-> TIMEQ
```

The generic Stasis is a candidate only if the preserved location condition and
its interval are supported. It does not realize a Role or Function.

## Provider nominal classifications

```mermaid
flowchart LR
    RECORD[Statcast row\nDescriptive ICE]
    PITCH[Pitch Act]
    STASIS[Defensive-location Stasis\ncandidate target]
    INFIELD[Nominal Measurement ICE\ninfield category]
    OUTFIELD[Nominal Measurement ICE\noutfield category]
    INREF[Versioned infield-alignment\nReference System]
    OUTREF[Versioned outfield-alignment\nReference System]
    INVALUE[exact provider token]
    OUTVALUE[exact provider token]
    TARGETQ[QUESTION\nOne complete Stasis or separate\ninfield/outfield subset Stases?]

    RECORD -->|is about| PITCH
    RECORD -->|is about| STASIS
    INFIELD -->|is a nominal measurement of| STASIS
    INFIELD -->|uses reference system| INREF
    INFIELD -->|has text value| INVALUE
    OUTFIELD -->|is a nominal measurement of| STASIS
    OUTFIELD -->|uses reference system| OUTREF
    OUTFIELD -->|has text value| OUTVALUE
    INFIELD -.-> TARGETQ
    OUTFIELD -.-> TARGETQ
    STASIS -.-> TARGETQ
```

If actual Sites and Stasis cannot be established, these solid classification
edges must be removed before review rather than redirected to the source row,
Pitch, Team, or players.
