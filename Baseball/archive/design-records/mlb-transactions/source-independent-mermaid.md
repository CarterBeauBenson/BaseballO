# Source-independent Mermaid

## Record grain versus world processes

```mermaid
flowchart LR
    PERSON[Person]
    RECORD[Descriptive Information Content Entity]
    TYPE[Generic Nominal Measurement ICE]
    REF[Provider Reference System instance]
    PROCESS[Precise supported process\nTrade, Contract Formation, Employment,\nGain/Loss of Role, Number Assignment, or Death]

    RECORD -->|is about| PERSON
    RECORD -.->|is about only when supported| PROCESS
    TYPE -->|is a nominal measurement of| RECORD
    TYPE -->|uses reference system| REF
```

An unresolved type may stop at the record/classification layer. It does not
license an anonymous or generic transaction act. The reference-system edge
depends on prior acceptance of the shared ICE-direct-value foundation.

## Multi-person trade

```mermaid
flowchart LR
    TRADE[Baseball Personnel Trade Act]
    TEAM1[Baseball Team A]
    TEAM2[Baseball Team B]
    PERSON1[Person 1]
    PERSON2[Person 2]
    RECORD1[Person-specific Descriptive ICE 1]
    RECORD2[Person-specific Descriptive ICE 2]
    LOST[Loss of Role]
    GAINED[Gain of Role]
    OLDROLE[Prior team-scoped Occupation Role]
    NEWROLE[Resulting team-scoped Occupation Role]

    TRADE -->|has agent| TEAM1
    TRADE -->|has agent| TEAM2
    TRADE -->|affects| PERSON1
    TRADE -->|affects| PERSON2
    TRADE -->|has occurrent part| LOST
    TRADE -->|has occurrent part| GAINED
    LOST -->|has participant| PERSON1
    GAINED -->|has participant| PERSON1
    OLDROLE -->|inheres in| PERSON1
    OLDROLE -->|has organizational context| TEAM1
    NEWROLE -->|inheres in| PERSON1
    NEWROLE -->|has organizational context| TEAM2
    RECORD1 -->|is about| TRADE
    RECORD1 -->|is about| PERSON1
    RECORD2 -->|is about| TRADE
    RECORD2 -->|is about| PERSON2
```

The proposed Trade class is instantiated only when the grouped evidence
supports those precise role changes. A later source-specific model must prove
the same Person and team-scoped Occupation Role identities across the existing
Gain/Loss of Role axioms and temporal boundaries.

## Team membership through occupation role and stasis

```mermaid
flowchart LR
    PERSON[Person]
    PLAYER[Team-scoped Occupation Role\nfor example Player Role]
    TEAM[Baseball Team]
    STASIS[Stasis of Role]
    INTERVAL[Temporal Interval]

    PLAYER -->|inheres in| PERSON
    PLAYER -->|has organizational context| TEAM
    STASIS -->|has participant| PERSON
    STASIS -->|has participant| PLAYER
    STASIS -->|occupies temporal region| INTERVAL
```

The role's organizational context expresses the team-membership fact. The
Stasis of Role supplies temporal persistence; neither structure warrants a
second membership-role class.

## Uniform-number assignment

```mermaid
flowchart LR
    ACT[Uniform Number Assignment Act]
    TEAM[Baseball Team]
    CODE[Code Identifier]
    ROLE[Player Role]
    PERSON[Person]

    ACT -->|has agent| TEAM
    ACT -->|has output| CODE
    CODE -->|designates| ROLE
    ROLE -->|has organizational context| TEAM
    ROLE -->|inheres in| PERSON
```

The Code Identifier designates a team-scoped Player Role, not the Person as an
intrinsic or permanent number bearer.

## Death is not an act of transaction

```mermaid
flowchart LR
    PERSON[Person]
    DEATH[Death\nNatural Process]
    RECORD[Descriptive Information Content Entity]

    DEATH -->|has participant| PERSON
    RECORD -->|is about| PERSON
    RECORD -->|is about| DEATH
```
