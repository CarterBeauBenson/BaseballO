# Source-independent Plate Appearance and Batter Role shape

```mermaid
flowchart LR
    PERSON[Person]
    ROLE[Batter Role]
    PA[Plate Appearance<br/>Process]
    HALF[Half Inning<br/>Process]
    ACT[Batter Act<br/>one per Plate Appearance]
    SPECIFIC[Supported Swing Act or Bunt Act]
    STASIS[Stasis of Batter Role]

    ROLE -->|inheres in| PERSON
    PA -->|has participant| PERSON
    PA -->|occurrent part of| HALF
    ACT -->|has participant| PERSON
    ACT -->|realizes| ROLE
    ACT -->|occurrent part of| PA
    SPECIFIC -->|has participant| PERSON
    SPECIFIC -->|realizes| ROLE
    SPECIFIC -->|occurrent part of| ACT
    SPECIFIC -->|occurrent part of| PA
    ROLE -->|participates in| STASIS
    PERSON -->|participates in| STASIS
```

Identity and cardinality decisions:

- `BatterRole`: one role IRI per Person across that Person's career;
- `PlateAppearance`: one Process IRI per game and source `atBatIndex`;
- each Plate Appearance has exactly one generic Batter Act whose participant is
  the batter Person and which realizes the Batter Role inhering in that Person;
- the Plate Appearance does not itself need a duplicate realization edge;
- supported Swing and Bunt Acts may additionally realize the same Role; and
- a Stasis of Batter Role expresses persistence only.

Forbidden substitute:

```mermaid
flowchart LR
    STASIS[Stasis]
    ROLE[Batter Role or Disposition]
    STASIS -.->|must not realize| ROLE
```

A reviewed Stasis may represent persistence without relevant change during an
evidenced interval. It is never used as the realization Process. The generic
Batter Act is that Process in the common Plate Appearance pattern.
