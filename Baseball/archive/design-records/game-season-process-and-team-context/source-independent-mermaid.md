# Accepted source-independent shapes

## Game and season processes

```mermaid
flowchart LR
    RULE[Baseball Rule]
    GAME[Baseball Game\nProcess]
    ACT[Baseball Act\nPlanned Act]
    PHYSICAL[Baseball Physical Process\nProcess]
    INSTITUTIONAL[Baseball Institutional Process\nProcess]
    SEASONPLAN[Baseball Season Plan\nPlan]
    SEASON[Baseball Season\nProcess]
    PHASE[Baseball Season Phase\nProcess]

    RULE -->|prescribes| GAME
    GAME -->|has occurrent part| ACT
    GAME -->|has occurrent part| PHYSICAL
    GAME -->|has occurrent part| INSTITUTIONAL
    SEASONPLAN -->|prescribes| SEASON
    SEASONPLAN -->|prescribes| PHASE
    SEASON -->|has occurrent part| GAME
    SEASON -->|has occurrent part| PHASE
```

The Game and Season are Processes even when a Rule or Plan prescribes them.
Their intentional Acts remain proper processual parts.

## Team context through an occupation role

```mermaid
flowchart LR
    PERSON[Person]
    ROLE[Player Role\nOccupation Role]
    TEAM[Baseball Team\nOrganization]
    STASIS[Stasis of Role]
    INTERVAL[Temporal Interval]

    PERSON -->|bearer of| ROLE
    ROLE -->|has organizational context| TEAM
    STASIS -->|has participant| PERSON
    STASIS -->|has participant| ROLE
    STASIS -->|occupies temporal region| INTERVAL
```

This shape expresses the intended claim that a Person is a member of a Team in
virtue of a team-scoped Occupation Role. It does not introduce a second roster
membership role.
