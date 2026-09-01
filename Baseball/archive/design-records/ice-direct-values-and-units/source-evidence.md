# Source and ontology evidence

## Authoritative local dependencies

The repository pins the authoritative dependency copies used by BaseballO:

- `CommonCoreOntologiesMerged.ttl`, CCO version 2.1 with version IRI dated
  2026-04-04;
- `ModalRelationOntology.ttl`, MRO version 2.0 with version IRI dated
  2024-11-06.

In both files:

- `cco:ont00000958` is Information Content Entity;
- `cco:ont00000253` is Information Bearing Entity;
- `cco:ont00001163` is Measurement Information Content Entity;
- `cco:ont00000120` is Measurement Unit;
- `cco:ont00000398` is Reference System; and
- `cco:ont00000469` is Geospatial Coordinate Reference System.

The two continuant categories play different roles. An ICE is the content that
is about or designates something. An IBE is a material object on which an ICE
generically depends. A numeric or textual literal in BaseballO describes the
content, not a separate material bearer introduced only for serialization.

## Conflict in the pinned relation axioms

The following generic datatype properties explicitly have IBE as their domain:

| IRI | Label | Current domain |
| --- | --- | --- |
| `cco:ont00001765` | has text value | Information Bearing Entity |
| `cco:ont00001767` | has datetime value | Information Bearing Entity |
| `cco:ont00001768` | has URI value | Information Bearing Entity |
| `cco:ont00001769` | has decimal value | Information Bearing Entity |
| `cco:ont00001770` | has double value | Information Bearing Entity |
| `cco:ont00001771` | has date value | Information Bearing Entity |
| `cco:ont00001772` | has boolean value | Information Bearing Entity |
| `cco:ont00001773` | has integer value | Information Bearing Entity |

The geographic value properties `cco:ont00001763` (altitude),
`cco:ont00001764` (longitude), and `cco:ont00001766` (latitude) do not all
declare an IBE domain, but their scope and definitions still describe placing
coordinate literals on an IBE. They need the same ICE-facing clarification.

The following object properties also use the material-carrier pattern:

| IRI | Label | Current issue |
| --- | --- | --- |
| `cco:ont00001863` | uses measurement unit | IBE domain and subproperty of BFO `is carrier of` |
| `cco:ont00001961` | is measurement unit of | IBE range and subproperty of BFO `is concretized by` |
| `cco:ont00001912` | uses reference system | IBE domain and subproperty of BFO `is carrier of` |
| `cco:ont00001997` | is reference system of | IBE range and subproperty of BFO `is concretized by` |
| `cco:ont00001913` | uses geospatial coordinate reference system | IBE domain inherited within the reference-system family |
| `cco:ont00001900` | is geospatial coordinate reference system of | IBE range inherited within the inverse family |

Those subproperty axioms are not merely overly restrictive domains. They say
that the Measurement Unit or Reference System ICE is carried by a material
IBE. That is a different relation from one ICE using another ICE to make a
literal interpretable.

## BaseballO usage evidence

BaseballO's content rules already specify the intended direct pattern:

```text
world-side measured entity <- is measurement of - Measurement ICE
Measurement ICE -> value literal
Measurement ICE -> Measurement Unit
Measurement ICE -> Reference System when required
```

The 31-class debt includes `BaseballTimestampICE`,
`BaseballFieldCoordinateICE`, and
`BaseballFieldCoordinateReferenceSystemICE`. Their repair would remain
internally contradictory if BaseballO asserted values directly on those ICEs
while the pinned domains continued to infer IBE membership.

## Nearby relations intentionally not changed

`uses language` and `uses time zone identifier` also currently use IBE-facing
definitions. A consistent future CCO cleanup may need to distinguish content
language/time-zone information from the encoding of a particular material
bearer. This package does not decide that adjacent question because the user
specifically authorized direct ICE values, Measurement Units, and Reference
Systems. No inference should be made from their omission.
