# Source-independent Mermaid

Solid edges use accepted vocabulary. The diagram says nothing about a provider
field or source-specific IRI.

```mermaid
flowchart LR
    PERSON[Person]
    MASS[CCO Mass]
    MEASUREMENT[Measurement Information Content Entity]
    VALUE[positive decimal value]
    POUND[Pound Measurement Unit]

    MASS -->|inheres in| PERSON
    MEASUREMENT -->|is a measurement of| MASS
    MEASUREMENT -->|has decimal value| VALUE
    MEASUREMENT -->|uses measurement unit| POUND
```

There is intentionally no Measurement Process. The particular measurement
content may change while the Mass Quality continues to inhere in the Person.
