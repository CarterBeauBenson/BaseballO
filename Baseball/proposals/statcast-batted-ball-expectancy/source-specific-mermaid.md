# Source-specific Mermaid

Status: **under review — design only**

Solid edges use accepted vocabulary but remain unapproved. Dotted lines point
to unresolved target/model questions and are not object-property proposals.

## Shared provider model execution

```mermaid
flowchart LR
    MOTION[Batted-Ball Motion Process]
    RECORD[Statcast row\nDescriptive ICE]
    INPUTS[Reviewed input Measurement ICEs]
    ALGORITHM[Versioned Algorithm]
    TRANSFORM[Generic model-computation Process\nAct and Agent status unresolved]
    XBA[Probability Measurement ICE\nxBA output]
    XWOBA[Point Estimate ICE\nxwOBA output]
    AGENTQ[QUESTION\nWhat causally active Agent would justify\nan Act of Data Transformation type?]

    RECORD -->|is about| MOTION
    TRANSFORM -->|has input| INPUTS
    TRANSFORM -->|prescribed by| ALGORITHM
    TRANSFORM -->|has output| XBA
    TRANSFORM -->|has output| XWOBA
    XBA -->|is about| MOTION
    XWOBA -->|is about| MOTION
    TRANSFORM -.-> AGENTQ
```

The input edges require versioned evidence; they do not authorize Statcast to
duplicate MLB-owned launch measurements. If input ICEs live in another
promoted graph, the source-local mapping cannot require them.

## xBA target blocker

```mermaid
flowchart LR
    XBA[Probability Measurement ICE]
    VALUE[xsd:decimal]
    ACTUAL[Actual Batted-Ball Motion Process]
    POSSIBLE[Possible Hit outcome Process\nQUESTION - no accepted target identity]
    TARGETQ[QUESTION\nHow is likelihood measured without\nasserting that a hit actually occurred?]

    XBA -->|has decimal value| VALUE
    XBA -->|is about| ACTUAL
    XBA -.-> TARGETQ
    POSSIBLE -.-> TARGETQ
```

The required `is a measurement of` edge is intentionally absent until the
possible Process target is accepted.

## xwOBA target and weighting blocker

```mermaid
flowchart LR
    XWOBA[Point Estimate ICE]
    VALUE[xsd:decimal]
    ACTUAL[Actual Batted-Ball Motion Process]
    DISTRIBUTION[Possible outcome distribution\nQUESTION - source does not expose all values]
    WEIGHTS[Season-specific wOBA weights\nQUESTION - versioned inputs required]
    TARGET[Expected weighted outcome target\nQUESTION - ontology anchor unresolved]

    XWOBA -->|has decimal value| VALUE
    XWOBA -->|is about| ACTUAL
    DISTRIBUTION -.-> TARGET
    WEIGHTS -.-> TARGET
    XWOBA -.-> TARGET
```

Neither the lexical field name nor the scalar alone supplies the missing
distribution, weights, or measured entity.
