# MLB transactions source-specific Mermaid

These diagrams are the pre-RML review contract. Solid arrows are proposed RDF
assertions. Dotted arrows marked **conditional** are emitted only when their
source value is non-null. Red dashed arrows are explicitly blocked.

## Provider grouping and content-versioned row

```mermaid
flowchart LR
    TXID["Non-Name Identifier<br/>text = transaction id"]
    TXIDTEXT["transaction id lexical form<br/>xsd:string"]
    TXIDREF["MLB transaction identifier<br/>Reference System instance"]
    GROUP["Grouping DICE<br/>stable per provider id"]
    ROW["Row or leg DICE<br/>content-versioned"]
    PERSON["Canonical Person"]
    FROM["Canonical Baseball Team<br/>fromTeam"]
    TO["Canonical Baseball Team<br/>toTeam"]

    TXID -->|designates| GROUP
    TXID -->|has text value| TXIDTEXT
    TXID -->|uses reference system| TXIDREF
    GROUP -->|has continuant part| ROW
    ROW -.->|is about, conditional person.id| PERSON
    ROW -.->|is about, conditional fromTeam.id| FROM
    ROW -.->|is about, conditional toTeam.id| TO
```

The grouping is an information entity, not a world-side act. The optional Team
edges state what the row mentions; they do not state movement, agency,
affiliation, or role change.

## Row classification and description

```mermaid
flowchart LR
    ROW["Row or leg DICE"]
    TYPE["Nominal Measurement ICE<br/>text = exact typeCode"]
    TYPECODE["typeCode<br/>xsd:string"]
    TYPEREF["MLB transaction type<br/>Reference System instance"]
    DESCRIPTION["Descriptive ICE<br/>text = exact description"]
    DESCRIPTIONTEXT["description<br/>xsd:string"]

    TYPE -->|is a nominal measurement of| ROW
    TYPE -->|has text value| TYPECODE
    TYPE -->|uses reference system| TYPEREF
    DESCRIPTION -.->|is about, conditional description| ROW
    DESCRIPTION -.->|has text value, conditional description| DESCRIPTIONTEXT
```

The pinned MLB transaction-type code list validates the `typeCode` and
`typeDesc` pair. `typeDesc` does not create a second type and does not select a
world-side class.

## Three date fields without invented process boundaries

```mermaid
flowchart LR
    ROW["Row or leg DICE"]
    DATE["Calendar Date Identifier<br/>date"]
    EFFECTIVE["Calendar Date Identifier<br/>effectiveDate"]
    RESOLUTION["Calendar Date Identifier<br/>resolutionDate"]
    DATEVALUE["date<br/>xsd:date"]
    EFFECTIVEVALUE["effectiveDate<br/>xsd:date"]
    RESOLUTIONVALUE["resolutionDate<br/>xsd:date"]
    DAY1["Day"]
    DAY2["Day"]
    DAY3["Day"]
    KEY1["Non-Name Identifier<br/>field key: date"]
    KEY2["Non-Name Identifier<br/>field key: effectiveDate"]
    KEY3["Non-Name Identifier<br/>field key: resolutionDate"]
    KEYTEXT1["date<br/>xsd:string"]
    KEYTEXT2["effectiveDate<br/>xsd:string"]
    KEYTEXT3["resolutionDate<br/>xsd:string"]
    FIELDREF["MLB transaction field-key<br/>Reference System instance"]
    PROCESS["Any world-side Process"]

    ROW -->|has continuant part| DATE
    ROW -->|has continuant part| EFFECTIVE
    ROW -.->|has continuant part, conditional| RESOLUTION
    DATE -->|has date value| DATEVALUE
    EFFECTIVE -->|has date value| EFFECTIVEVALUE
    RESOLUTION -.->|has date value, conditional| RESOLUTIONVALUE
    DATE -->|designates| DAY1
    EFFECTIVE -->|designates| DAY2
    RESOLUTION -.->|designates, conditional| DAY3
    KEY1 -->|designates| DATE
    KEY2 -->|designates| EFFECTIVE
    KEY3 -.->|designates, conditional| RESOLUTION
    KEY1 -->|has text value| KEYTEXT1
    KEY2 -->|has text value| KEYTEXT2
    KEY3 -.->|has text value, conditional| KEYTEXT3
    KEY1 -->|uses reference system| FIELDREF
    KEY2 -->|uses reference system| FIELDREF
    KEY3 -.->|uses reference system, conditional| FIELDREF
    DATE -. blocked: no boundary claim .-> PROCESS
    EFFECTIVE -. blocked: no boundary claim .-> PROCESS
    RESOLUTION -. blocked: no boundary claim .-> PROCESS
```

The provider field keys distinguish the generic date identifiers without new
field-specific classes. None of the three dates is a process boundary or
temporal extent in this release.

## Deterministic identity

```mermaid
flowchart LR
    ID["provider transaction id"]
    GROUPIRI["stable grouping IRI"]
    CONTENT["selected semantic members<br/>with explicit nulls"]
    RFC["RFC 8785 canonical JSON<br/>UTF-8"]
    HASH["SHA-256 lowercase hex"]
    ROWIRI["content-versioned row IRI"]
    CHILDREN["type, description, and date IRIs<br/>row IRI plus fixed role token"]

    ID --> GROUPIRI
    CONTENT --> RFC
    RFC --> HASH
    HASH --> ROWIRI
    ROWIRI --> CHILDREN
```

The selected members are `id`, `personId`, `fromTeamId`, `toTeamId`, `date`,
`effectiveDate`, `resolutionDate`, `typeCode`, `typeDesc`, and `description`.
No response index, retrieval timestamp, or request window contributes to row
identity.

## The only conditional world-side assertion

```mermaid
flowchart LR
    CODES["Pinned MLB transaction-type<br/>code-list snapshot"]
    MATCH{"exact reviewed<br/>Death code match?"}
    PERSONID{"non-null person.id<br/>and canonical join?"}
    ROW["Row or leg DICE"]
    PERSON["Person"]
    DEATH["CCO Death"]

    CODES --> MATCH
    MATCH -->|yes| PERSONID
    PERSONID -->|yes| DEATH
    DEATH -->|has participant| PERSON
    ROW -->|is about| PERSON
    ROW -->|is about| DEATH
```

If either gate fails, the row remains at the information layer and no Death is
minted. The date identifiers remain unbound to the Death boundary.

## Accepted classes intentionally not instantiated

```mermaid
flowchart LR
    TRADEROW["Row classified by Trade code"]
    TRADE["Baseball Personnel Trade Act<br/>accepted class"]
    ROLES["Persistent team-scoped Player Roles<br/>and stint identity"]
    NUMBERROW["Row classified by Number Change code"]
    ASSIGN["Uniform Number Assignment Act<br/>accepted class"]
    CODE["Structured number Code Identifier<br/>and reviewed bearer"]

    TRADEROW -. blocked until role and stint identity .-> TRADE
    ROLES -. required evidence .-> TRADE
    NUMBERROW -. blocked because number is prose only .-> ASSIGN
    CODE -. required evidence .-> ASSIGN
```

## Detachable asynchronous lane

```mermaid
flowchart LR
    API["MLB transactions API<br/>plus transactionTypes code list"]
    JSON["Transient response bytes"]
    INPUT["Pre-mapping input and code-list validation<br/>required IDs and dates valid<br/>known typeCode and matching typeDesc"]
    MAP["Future mlb-transactions RML"]
    RDF["Emitted source RDF"]
    SHACL["Future source-owned SHACL gate<br/>validates emitted RDF"]
    PROMOTE["Graph-pair promotion"]
    KG["Persistent authoritative RDF"]
    MANIFEST["Persistent hashes, manifests,<br/>reports, and provenance"]
    QUARANTINE["Source-owned quarantine and retry"]

    API --> JSON
    JSON --> INPUT
    INPUT -->|admitted rows only| MAP
    INPUT -->|fails before RML| QUARANTINE
    MAP --> RDF
    RDF --> SHACL
    SHACL -->|conforms| PROMOTE
    PROMOTE --> KG
    JSON --> MANIFEST
    INPUT --> MANIFEST
    SHACL --> MANIFEST
    SHACL -->|fails| QUARANTINE
```

NiFi will submit and supervise this lane independently. Normal execution is
asynchronous; a healthy run does not require interactive monitoring. The
pre-mapping gate owns every check that requires the transient JSON or pinned
code list. SHACL validates only emitted RDF and is not expected to discover a
source value that RML omitted; the one-record fixture and source-to-RDF mapping
regression prove that mapping completeness before activation.
