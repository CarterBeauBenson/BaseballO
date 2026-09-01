# Source-specific Mermaid

Status: **under review — design only**

Solid edges are accepted vocabulary in a candidate source shape, not approved
RDF. Dotted branches are unresolved modeling questions, not properties.

## Versioned model execution and state evidence

```mermaid
flowchart LR
    GAME[Baseball Game]
    EVENT[Pitch Act or Plate Appearance]
    RECORD[Statcast row\nDescriptive ICE]
    STATE[Game-state input ICEs]
    ALGORITHM[Versioned Algorithm]
    TRANSFORM[Generic model-computation Process\nAct and Agent status unresolved]
    HOMEWIN[Probability Measurement ICE\nhome_win_exp]
    RUNDELTA[Point Estimate ICE\ndelta_run_exp]
    AGENTQ[QUESTION\nWhat causally active Agent would justify\nan Act of Data Transformation type?]

    RECORD -->|is about| GAME
    RECORD -->|is about| EVENT
    TRANSFORM -->|has input| STATE
    TRANSFORM -->|prescribed by| ALGORITHM
    TRANSFORM -->|has output| HOMEWIN
    TRANSFORM -->|has output| RUNDELTA
    HOMEWIN -->|is about| GAME
    RUNDELTA -->|is about| EVENT
    TRANSFORM -.-> AGENTQ
```

The state inputs are not permission to duplicate MLB-game state in Statcast
RML. Their exact before/after scope and model identity remain required evidence.

## Home-win probability target blocker

```mermaid
flowchart LR
    HOMEWIN[Probability Measurement ICE]
    VALUE[xsd:decimal]
    GAME[Actual Baseball Game]
    POSSIBLE[Possible home-team win outcome\nQUESTION - target identity unresolved]
    TARGETQ[QUESTION\nWhich Process or Process Aggregate's\nlikelihood is measured at this state?]

    HOMEWIN -->|has decimal value| VALUE
    HOMEWIN -->|is about| GAME
    HOMEWIN -.-> TARGETQ
    POSSIBLE -.-> TARGETQ
```

No `is a measurement of` edge is proposed until the possible target is
accepted.

## Run-expectancy delta blocker

```mermaid
flowchart LR
    BEFORE[Before-state run Estimate ICE\nQUESTION - not exposed directly]
    AFTER[After-state run Estimate ICE\nQUESTION - not exposed directly]
    ACTUALRUN[Actual Run Process or count]
    DELTA[Point Estimate ICE\ndelta_run_exp]
    VALUE[xsd:decimal]
    FUTURE[Remaining Run Process aggregate\nQUESTION - target identity unresolved]
    FORMULAQ[QUESTION\nDoes delta include actual runs scored, and\nwhich event boundary separates states?]

    DELTA -->|has decimal value| VALUE
    BEFORE -.-> FORMULAQ
    AFTER -.-> FORMULAQ
    ACTUALRUN -.-> FORMULAQ
    DELTA -.-> FORMULAQ
    FUTURE -.-> FORMULAQ
```

The scalar does not by itself supply two state estimates, a formula, or a
future Process target.
