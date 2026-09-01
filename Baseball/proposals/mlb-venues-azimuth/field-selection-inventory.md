# Field inventory and de-duplication

| Field/evidence | Disposition | Consequence |
| --- | --- | --- |
| 'location.azimuthAngle' | authoritative duplicate; blocked | Admit only after two lines, shared point, frame, convention, unit, and scope are accepted. |
| venue/field identity | identity/join-only | Reuse canonical Venue and Field Site. |
| field dimension origin/boundary points | nearby accepted evidence | Do not assume they identify the azimuth origin or line. |
| request season/response hash | provenance | Snapshot evidence, not automatic season validity. |
| null/absent value | resolved absence | Emit no angle subgraph. |
| malformed/out-of-range present value | invalid if admitted | Quarantine before RML under the accepted numeric range. |

Angle Quality already exists. Potential class/identity gaps concern the
source-independent field reference line, north reference line, and shared
reference point. No object property is proposed.

