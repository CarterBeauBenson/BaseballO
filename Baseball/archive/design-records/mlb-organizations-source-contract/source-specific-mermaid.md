# Source-specific Mermaid review shape

Solid edges are proposed executable RDF after explicit approval. Dashed edges
are blockers and must not appear in RML or authoritative RDF.

## Organization identity, names, and record provenance

```mermaid
flowchart LR
    RESPONSE[MLB organizations response\ngeneric Descriptive ICE\ncontent-versioned]
    TEAM[Baseball Team]
    LEAGUE[CCO Organization\nidentified as MLB league]
    DIVISION[CCO Organization\nidentified as MLB division]
    TID[MLB team Non-Name Identifier]
    LID[MLB league Non-Name Identifier]
    DID[MLB division Non-Name Identifier]
    TREF[MLB team-ID\nReference System]
    LREF[MLB league-ID\nReference System]
    DREF[MLB division-ID\nReference System]
    TNAME[Proper Name]
    LNAME[Proper Name]
    DNAME[Proper Name]

    RESPONSE -->|is about| TEAM
    RESPONSE -->|is about| LEAGUE
    RESPONSE -->|is about| DIVISION
    RESPONSE -->|has continuant part| TID
    RESPONSE -->|has continuant part| LID
    RESPONSE -->|has continuant part| DID
    RESPONSE -->|has continuant part| TNAME
    RESPONSE -->|has continuant part| LNAME
    RESPONSE -->|has continuant part| DNAME
    TID -->|designates| TEAM
    LID -->|designates| LEAGUE
    DID -->|designates| DIVISION
    TID -->|has text value| TIDVALUE[team ID lexical value]
    LID -->|has text value| LIDVALUE[league ID lexical value]
    DID -->|has text value| DIDVALUE[division ID lexical value]
    TID -->|uses reference system| TREF
    LID -->|uses reference system| LREF
    DID -->|uses reference system| DREF
    TNAME -->|designates| TEAM
    LNAME -->|designates| LEAGUE
    DNAME -->|designates| DIVISION
    TNAME -->|has text value| TTEXT[exact Unicode `name`]
    LNAME -->|has text value| LTEXT[exact Unicode `name`]
    DNAME -->|has text value| DTEXT[exact Unicode `name`]
```

A particular response is about only the entities actually present in it; this
union shape does not require every response to contain all three resource
kinds. League and Division are generic Organizations. Their provider kind and
identity are carried by the identifier/reference-system pattern, not by a new
field-shaped ontology class.

## Season, Plan, reviewed Phases, and date evidence

```mermaid
flowchart LR
    RESPONSE[MLB league-season response\ngeneric Descriptive ICE]
    LEAGUE[CCO Organization\nMLB league identity]
    PLAN[Baseball Season Plan]
    SEASON[Baseball Season]
    REGULAR[Baseball Season Phase\nregular-season key]
    POST[Baseball Season Phase\npostseason key]
    SID[MLB season-code\nNon-Name Identifier]
    SREF[MLB season-code\nReference System]
    DATE[Calendar Date Identifier\nresponse-versioned]
    FIELDKEY[seasonDateInfo field-key\nNon-Name Identifier]
    FIELDREF[MLB season-date-field\nReference System]
    DAY[Day]

    RESPONSE -->|is about| LEAGUE
    RESPONSE -->|is about| PLAN
    RESPONSE -->|is about| SEASON
    RESPONSE -->|has continuant part| SID
    RESPONSE -->|has continuant part| FIELDKEY
    SID -->|uses reference system| SREF
    SID -->|designates| SEASON
    SID -->|has text value| SIDVALUE[season-code lexical value]
    PLAN -->|prescribes| SEASON
    PLAN -->|prescribes| REGULAR
    PLAN -->|prescribes| POST
    REGULAR -->|occurrent part of| SEASON
    POST -->|occurrent part of| SEASON
    PLAN -->|has continuant part| DATE
    FIELDKEY -->|uses reference system| FIELDREF
    FIELDKEY -->|designates| DATE
    FIELDKEY -->|has text value| FIELDVALUE[exact seasonDateInfo field key]
    DATE -->|has date value| VALUE[xsd:date]
    DATE -->|designates| DAY
```

The regular-season or postseason node and its edges exist only when the exact
reviewed start/end pair is valid and non-null. Other date keys still produce
Plan-part Date Identifiers but no Phase. The shape deliberately has no edge
from Day or Date Identifier to Phase: the pinned ontology lacks a reviewed
relation expressing the intended boundary without overclaiming temporal
occupation.

## Explicitly blocked institutional edges

```mermaid
flowchart LR
    TEAM[Baseball Team]
    LEAGUE[CCO Organization\nMLB league identity]
    DIVISION[CCO Organization\nMLB division identity]
    SEASON[Baseball Season]
    GAP[Reviewed temporalized affiliation\nor snapshot pattern absent]

    TEAM -.->|team-league affiliation blocked| GAP
    TEAM -.->|team-division affiliation blocked| GAP
    DIVISION -.->|division-league relation blocked| GAP
    GAP -.-> LEAGUE
    GAP -.-> DIVISION
    GAP -.-> SEASON
```

Nesting, a shared season request, or an IRI identity scope does not replace the
missing relation. No solid affiliation edge is authorized.

## Detachable execution boundary

```mermaid
flowchart LR
    API[Transient MLB organization JSON]
    MANIFEST[Persistent request/hash manifest]
    INPUT[Pre-RML source-contract validation\npresent IDs and dates]
    RML[mlb-organizations RML]
    SHACL[Post-RML mlb-organizations SHACL\nemitted RDF only]
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

The input gate can see malformed present source values before RML. SHACL can
validate only triples RML emitted; it cannot detect a source value that the
mapping omitted. Null and absent optional values pass input validation and
follow the reviewed no-emission policy.

This lane has no RML or SHACL dependency on `mlb-game`, `mlb-people`,
`mlb-venues`, or `mlb-transactions`. Cross-source equivalence is evaluated by
explicitly scoped SPARQL only after independent promotion.
