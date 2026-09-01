# Source-specific Mermaid review shape

Solid edges are proposed executable RDF after explicit approval. Dashed edges
are blockers and must not appear in executable RML or authoritative RDF.

## Person identity and names

```mermaid
flowchart LR
    RESPONSE[MLB people response\ngeneric Descriptive ICE\ncontent-versioned]
    PERSON[Person\nstable MLB identity]
    PID[MLB person\nNon-Name Identifier]
    PREF[MLB person-ID\nReference System]
    NAME[Proper Name\nfrom `fullName`]
    NICK[Nickname\nfrom `nickName`]

    RESPONSE -->|is about| PERSON
    RESPONSE -->|has continuant part| PID
    RESPONSE -->|has continuant part| NAME
    RESPONSE -->|has continuant part| NICK
    PID -->|designates| PERSON
    PID -->|uses reference system| PREF
    PID -->|has text value| PIDVALUE[person ID lexical value]
    NAME -->|designates| PERSON
    NICK -->|designates| PERSON
    NAME -->|has text value| NTEXT[exact UTF-8-decoded text]
    NICK -->|has text value| KTEXT[exact UTF-8-decoded text]
```

Null name fields emit no Name. The literal is not case-folded, ASCII-folded,
or mojibake-repaired. The proof fixture must preserve `Eugenio Suárez` exactly.

## Height measurement without an invented process

```mermaid
flowchart LR
    RESPONSE[MLB people response\ngeneric Descriptive ICE]
    PERSON[Person]
    HEIGHT[Height Quality\nstable with bearer]
    MEASUREMENT[Measurement ICE\nresponse-versioned]
    VALUE[strictly positive decimal\ntotal inches]
    INCH[CCO Inch]

    RESPONSE -->|is about| PERSON
    RESPONSE -->|has continuant part| MEASUREMENT
    HEIGHT -->|inheres in| PERSON
    MEASUREMENT -->|is a measurement of| HEIGHT
    MEASUREMENT -->|has decimal value| VALUE
    MEASUREMENT -->|uses measurement unit| INCH
```

The source string must match the reviewed feet/inches grammar, convert by
`(12 * feet) + inches`, and yield a value greater than zero. There is
intentionally no Measurement Process, instrument, method, agent, or time node.

## Birth and date evidence without false temporal localization

```mermaid
flowchart LR
    RESPONSE[MLB people response\ngeneric Descriptive ICE]
    PERSON[Person]
    BIRTH[Birth Process\nstable Person-scoped identity]
    DATE[Calendar Date Identifier\nresponse-versioned]
    DAY[Day]

    RESPONSE -->|is about| PERSON
    RESPONSE -->|is about| BIRTH
    RESPONSE -->|has continuant part| DATE
    BIRTH -->|has participant| PERSON
    DATE -->|has date value| VALUE[xsd:date]
    DATE -->|designates| DAY
    BIRTH -.->|temporal localization relation absent| DAY
```

The dashed Birth-to-Day edge is not RDF. The response associates its Date
Identifier evidence with the Birth by being about the Birth and containing the
Date Identifier; it does not claim that the Process occupies the entire Day.

## Explicitly blocked fields

```mermaid
flowchart LR
    WEIGHT[`weight` bare integer]
    UNIT[Official evidence that unit is Pound]
    MASS[Mass Quality and Measurement ICE]
    BATSIDE[`batSide`]
    PITCHHAND[`pitchHand`]
    POSITION[`primaryPosition`]
    TEAM[`currentTeam`]
    NUMBER[`primaryNumber`]
    WORLD[Reviewed world-side structures\nand temporal scopes]

    WEIGHT -.->|unit unresolved| UNIT
    UNIT -.-> MASS
    BATSIDE -.-> WORLD
    PITCHHAND -.-> WORLD
    POSITION -.-> WORLD
    TEAM -.-> WORLD
    NUMBER -.-> WORLD
```

No generic field-shaped ICE is substituted for these missing structures.

## Detachable execution boundary

```mermaid
flowchart LR
    API[Transient MLB people JSON]
    MANIFEST[Persistent request/hash manifest]
    INPUT[Pre-RML source-contract validation\npresent IDs, dates, and height]
    RML[mlb-people RML]
    SHACL[Post-RML mlb-people SHACL\nemitted RDF only]
    STAGE[Module staging graph]
    STORE[(Persistent authoritative triple store)]
    QUARANTINE[Module quarantine]

    API --> INPUT
    INPUT -->|valid source payload| RML --> SHACL
    INPUT -->|malformed present selected value| QUARANTINE
    API --> MANIFEST
    SHACL -->|conforms| STAGE -->|atomic promotion| STORE
    SHACL -->|fails| QUARANTINE
```

The input gate can see malformed present source values before RML, including a
height that computes to zero. SHACL can validate only triples RML emitted and
cannot detect a present source value that the mapping omitted. Null and absent
optional values pass input validation and follow the reviewed no-emission
policy.

The lane does not map game participation or game-scoped roles. It has no RML
or SHACL dependency on another source module; canonical identities meet only
after independent promotion.
