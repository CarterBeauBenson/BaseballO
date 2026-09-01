# Source-independent Mermaid

## Processes, planning, and blocked organization semantics

```mermaid
flowchart LR
    LEAGUE[League Organization candidate]
    DIVISION[Division Organization candidate]
    TEAM[Baseball Team\nOrganization]
    SEASON[Baseball Season\nProcess]
    GAME[Baseball Game\nProcess]
    PLAN[Baseball Season Plan\nPlan ICE]
    RULE[Baseball Rule]
    ORGGAP[Unresolved independent\nOrganization differentia]
    AFFGAP[Unresolved temporalized\naffiliation pattern]

    RULE -->|prescribes| GAME
    RULE -->|prescribes| SEASON
    SEASON -->|has occurrent part| GAME
    PLAN -->|prescribes| SEASON
    LEAGUE -.->|class blocked on| ORGGAP
    DIVISION -.->|class blocked on| ORGGAP
    TEAM -.->|affiliation requires| AFFGAP
    AFFGAP -.-> LEAGUE
    AFFGAP -.-> DIVISION
```

The dashed branches are blockers, not proposed RDF. `BaseballLeague` and
`BaseballDivision` are withheld because a Rule ICE cannot be made a continuant
part of an Organization and the observed nesting does not supply an independent
identity account. The pinned vocabulary's unqualified `is affiliated with`
relation also cannot by itself state which season an affiliation holds during,
and a Mermaid label cannot repair that gap. A later source-specific design must
use accepted Organization and temporalized-affiliation patterns.

No League participation in the Season Process is asserted. A particular Act of
Planning, its Agent, and any Organization participation require evidence of
those Processes; they are not inferred merely because a record nests season
data or because a Plan exists.

## Season plan and phase boundaries

```mermaid
flowchart LR
    PLAN[Baseball Season Plan\nDirective ICE]
    SEASON[Baseball Season\nProcess]
    PHASE[Baseball Season Phase\nProcess]
    INTERVAL[Temporal Interval]
    START[Start Date Identifier]
    END[End Date Identifier]
    STARTDAY[Start Day]
    ENDDAY[End Day]
    RECORD[MLB League/Season Record ICE]

    RECORD -->|is about| PLAN
    RECORD -->|is about| SEASON
    PLAN -->|prescribes| SEASON
    PLAN -->|prescribes| PHASE
    PLAN -->|has continuant part| START
    PLAN -->|has continuant part| END
    PHASE -->|occurrent part of| SEASON
    PHASE -->|has occurrent part| GAME[Baseball Game]
    PHASE -->|occupies temporal region| INTERVAL
    START -->|designates| STARTDAY
    END -->|designates| ENDDAY
    STARTDAY -.->|exact boundary relation unresolved| INTERVAL
    ENDDAY -.->|exact boundary relation unresolved| INTERVAL
```

The source-specific implementation must distinguish planned boundaries from
observed first/last games and must not create a phase from a null date.
Prescription by the Season Plan does not classify the Season or Phase as a
Planned Act; intentional Acts occur as parts of the Season's Games.
Date Identifiers designate Days. The dashed boundary links are unresolved and
must not be replaced by an invented `designates boundary of` property.

## Source separation

```mermaid
flowchart LR
    ORG[Future MLB organization source lane]
    GAME[Existing MLB game source lane]
    ORGGRAPH[Promoted organization graph]
    GAMEGRAPH[Promoted game graph]
    STORE[Authoritative triple store]
    CROSS[Explicit multi-source SPARQL]

    ORG --> ORGGRAPH --> STORE
    GAME --> GAMEGRAPH --> STORE
    STORE --> CROSS
```

There is no RML or SHACL edge between the two lanes.
