# A1 accepted source-independent shape

The boxes denote particular instances of the named accepted classes.

```mermaid
flowchart LR
  BP["Batted-Ball Play Process"]
  RR["Runner Resolution Process"]
  PA["Plate Appearance"]
  PERSON["Person: affected runner"]
  BP -->|"obo:BFO_0000117: has occurrent part"| RR
  BP -->|"obo:BFO_0000132: occurrent part of"| PA
  RR -->|"obo:BFO_0000132: occurrent part of"| PA
  RR -->|"obo:BFO_0000057: has participant"| PERSON
```

The contact play and runner resolution already exist under their accepted
identities. Only the first edge is added. The edge expresses parthood and
does not determine attribution, causation, destination or persistence.
No stasis or new ontology term is introduced by this accepted slice.
