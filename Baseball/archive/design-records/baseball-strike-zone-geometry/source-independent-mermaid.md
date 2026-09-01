# Source-independent Mermaid

```mermaid
flowchart TB
    FIELD[Baseball Field Site]
    PLATE[Home Plate]
    ZONE[Baseball Strike Zone Site]
    UPPER[Upper Fiat Surface]
    LOWER[Lower Fiat Surface]
    FIRST[First-base-side Fiat Surface]
    THIRD[Third-base-side Fiat Surface]
    FRONT[Front Fiat Surface]
    BACK[Back Fiat Surface]
    ABS[ABS Evaluation Fiat Surface\nmidpoint of Home Plate]
    RULE[Strike Rule]
    ABSRULE[ABS Evaluation Rule]
    BATTER[Batter]
    ANATOMY[Selected anatomical Fiat Points]
    PLATELINES[Selected Home Plate boundary Fiat Lines]

    ZONE -->|continuant part of| FIELD
    ZONE -->|has continuant part| UPPER
    ZONE -->|has continuant part| LOWER
    ZONE -->|has continuant part| FIRST
    ZONE -->|has continuant part| THIRD
    ZONE -->|has continuant part| FRONT
    ZONE -->|has continuant part| BACK
    ZONE -->|has continuant part| ABS
    RULE -->|is about| ZONE
    ABSRULE -->|subclass of| RULE
    ABSRULE -->|is about| ABS
    UPPER -.->|position determined from| ANATOMY
    LOWER -.->|position determined from| ANATOMY
    FIRST -.->|extends from| PLATELINES
    THIRD -.->|extends from| PLATELINES
    FRONT -.->|extends from| PLATELINES
    BACK -.->|extends from| PLATELINES
    ANATOMY -->|continuant part of| BATTER
    PLATELINES -->|continuant part of| PLATE
```

The dotted geometry edges expose the instance construction that measurements
must substantiate; they are not proposed object properties. The proposed OWL
axioms assert only necessary Site/Fiat-Surface/rule restrictions and leave
provider-specific anatomical and plate-line selection to reviewed RDF. No
Strike Zone Site equivalence axiom is proposed until those identity-bearing
anchors are modeled.
