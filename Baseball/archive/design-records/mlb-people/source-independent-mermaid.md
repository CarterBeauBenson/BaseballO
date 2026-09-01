# Source-independent review shapes

## Existing person and measurement pattern

```mermaid
flowchart LR
    PERSON[Person]
    HEIGHT[Height Quality]
    MASS[Mass Quality]
    HM[Measurement ICE]
    MM[Measurement ICE]
    BIRTH[Birth Process]
    DAY[Day]
    DATE[Date Identifier]
    NAME[Proper Name or Nickname]

    HEIGHT -->|inheres in| PERSON
    MASS -->|inheres in| PERSON
    HM -->|is a measurement of| HEIGHT
    MM -->|is a measurement of| MASS
    HM -->|uses measurement unit| HUNIT[Linear Measurement Unit]
    MM -->|uses measurement unit| MUNIT[Mass Measurement Unit]
    BIRTH -->|has participant| PERSON
    BIRTH -.->|day-level temporal localization; exact relation unresolved| DAY
    DATE -->|designates| DAY
    NAME -->|designates| PERSON
```

All solid nodes and relations in this shape already exist. The values and units
are directly asserted on the Measurement ICE only if the shared ICE foundation
is accepted.

The dashed Birth-to-Day edge is a blocker. A reported date establishes that
the Birth occurred sometime within the designated Day; it does not establish
that the Birth Process occupied that entire Day. Executable mapping must wait
for an accepted temporal-containment or localization pattern.

## Laterality stops at missing world-side structure

```mermaid
flowchart LR
    PERSON[Person]
    BATTER[Batter Act]
    PITCH[Pitch Act]
    PLATE[Home Plate]
    ORIENT[Spatial Orientation]
    BODY[Bodily Component]
    BATGAP[Unresolved persistent batting-laterality structure]
    PITCHGAP[Unresolved pitching-hand laterality structure]
    CLASS[Generic Nominal Measurement ICE]
    REF[Reference System instance]

    PERSON -.-> BATGAP
    BATTER -.-> BATGAP
    PLATE -.-> BATGAP
    ORIENT -.-> BATGAP
    PERSON -.-> PITCHGAP
    PITCH -.-> PITCHGAP
    BODY -.-> PITCHGAP
    CLASS -.->|target withheld| BATGAP
    CLASS -.->|target withheld| PITCHGAP
    CLASS -->|uses reference system| REF
```

Dashed edges are review questions, not proposed relations or executable RDF.
No field-specific ICE class stands in for either missing structure. The solid
reference-system edge depends on prior acceptance of the ICE-direct foundation.

## Primary-position target remains unresolved

```mermaid
flowchart LR
    CLASS[Generic Nominal Measurement ICE]
    PERSON[Person]
    CUSTOMARY[Customary Player Role]
    ROSTER[Roster designation]
    GAMEROLE[Game-scoped role realization]

    CLASS -.->|possible target| PERSON
    CLASS -.->|possible target| CUSTOMARY
    CLASS -.->|possible target| ROSTER
    CLASS -.->|does not automatically entail| GAMEROLE
```

## Source-ownership decision

```mermaid
flowchart LR
    GAME[MLB game payload\ncurrent assertion owner]
    PEOPLE[Standalone people endpoint\ncoverage candidate only]
    GAP[Explicit future ownership/coverage decision]
    STORE[Authoritative triple store]

    GAME --> STORE
    PEOPLE -.-> GAP -.-> STORE
```

The dashed people route cannot become a NiFi/RML lane without a new accepted
ownership decision.
