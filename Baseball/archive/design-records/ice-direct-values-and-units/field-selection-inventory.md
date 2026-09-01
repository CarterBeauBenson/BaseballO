# Relation selection inventory

This is an ontology-relation inventory rather than a provider-field inventory.
Every row has exactly one disposition.

| Existing relation | Disposition | Proposed treatment |
| --- | --- | --- |
| `cco:ont00001765` has text value | revise existing | Change domain from IBE to ICE; retain the existing property IRI. |
| `cco:ont00001767` has datetime value | revise existing | Change domain from IBE to ICE. |
| `cco:ont00001768` has URI value | revise existing | Change domain from IBE to ICE. |
| `cco:ont00001769` has decimal value | revise existing | Change domain from IBE to ICE. |
| `cco:ont00001770` has double value | revise existing | Change domain from IBE to ICE. |
| `cco:ont00001771` has date value | revise existing | Change domain from IBE to ICE. |
| `cco:ont00001772` has boolean value | revise existing | Change domain from IBE to ICE. |
| `cco:ont00001773` has integer value | revise existing | Change domain from IBE to ICE. |
| `cco:ont00001763` has altitude value | revise existing annotation | State that the coordinate literal belongs to an ICE; do not introduce an IBE. |
| `cco:ont00001764` has longitude value | revise existing | Give the property an ICE domain and update its definition. |
| `cco:ont00001766` has latitude value | revise existing | Give the property an ICE domain and update its definition. |
| `cco:ont00001863` uses measurement unit | revise existing | ICE domain; remove the BFO carrier subproperty; retain Measurement Unit range and inverse. |
| `cco:ont00001961` is measurement unit of | revise existing | ICE range; remove the BFO concretization subproperty; retain Measurement Unit domain and inverse. |
| `cco:ont00001912` uses reference system | revise existing | ICE domain; remove the BFO carrier subproperty; retain Reference System range and inverse. |
| `cco:ont00001997` is reference system of | revise existing | ICE range; remove the BFO concretization subproperty; retain Reference System domain and inverse. |
| `cco:ont00001913` uses geospatial coordinate reference system | revise existing | ICE domain; remain a subproperty of `uses reference system`. |
| `cco:ont00001900` is geospatial coordinate reference system of | revise existing | ICE range; remain a subproperty of `is reference system of`. |
| A new `uses reference unit` object property | rejected | The authoritative property is `uses reference system`; do not create a synonym with different identity. |
| A BaseballO value datatype property family | rejected | Reuse the existing CCO properties after repair. |
| An IBE created solely to hold a literal | rejected | It adds a material bearer unsupported by the source and obscures the ICE/world distinction. |
| BFO carrier relations between a real material bearer and an ICE | unchanged | Continue to use carrier/concretization relations for actual IBEs; they are not value or unit relations. |
| `uses language` | unresolved, out of scope | Its content-versus-encoding semantics need a separate decision. |
| `uses time zone identifier` | unresolved, out of scope | Its content-versus-bearer semantics need a separate decision. |

No new object property is required. This supports the working hypothesis that
the needed relation vocabulary already exists and that an absent relation
would require a principled reason rather than convenience.
