# Accepted repair inventory

| Existing or candidate content | Accepted disposition |
| --- | --- |
| `base:BaseballFieldCoordinateReferenceSystemICE` parent | Replace CCO Spatial Reference System with generic CCO Reference System. |
| Field frame axes | Fiat Lines, not Spatial Regions or CCO Coordinate System Axis individuals. |
| Frame origin | Shared Fiat Point that is a continuant part of both axis Fiat Lines. |
| Axis perpendicularity | Angle Quality inhering in both axis Fiat Lines. |
| Component magnitudes | Distance Qualities grounded in the origin and selected axis Fiat Points. |
| Coordinate tuple | Designative ICE using the field-coordinate Reference System and designating a field-relative Site. |
| Provider `coordX`, `coordY` | Still deferred from executable RML pending the provider convention and approved literal properties. |
| Polygon containment | Derived Jena query operation only when both geometries use the same reviewed convention. |

No new class or object property IRI is introduced by this repair.
