# Field-selection inventory

The active RML references none of these fields. Classification here controls
review; it does not authorize mapping.

| Family | Fields | Draft disposition |
| --- | --- | --- |
| Scalar pitch speed | `startSpeed`, `endSpeed` | Retain; Speed Process Profiles at separately reviewed evaluations. |
| Pitch duration | `plateTime` | Retain if confirmed as elapsed pitch-flight duration; otherwise unresolved. |
| Release extension | `extension` | Retain after release point, mound/plate reference point, direction, and unit are confirmed. |
| Initial location | `x0`, `y0`, `z0` | Retain only as an ordered coordinate designation under a documented frame; never three intrinsic qualities. |
| Initial velocity components | `vX0`, `vY0`, `vZ0` | Retain only after axes, signs, origin, units, and evaluation scope establish a Velocity Process Profile. |
| Acceleration components | `aX`, `aY`, `aZ` | Retain only after the same frame review establishes an Acceleration Process Profile. |
| Plate location | `pX`, `pZ` | Retain only after MLB Games evidence establishes this feed's own evaluation plane, axes, signs, origin, units, and method eras. Do not import the similarly named Savant `plate_x`/`plate_z` definitions. |
| Pitch movement | `pfxX`, `pfxZ` | Unresolved until baseline trajectory, gravity treatment, axes, signs, and units are documented. |
| Display coordinates | `pitchData.coordinates.x`, `.y` | Exclude from physical mapping unless the provider documents their display coordinate system. |
| Strike-zone boundaries | `strikeZoneTop`, `strikeZoneBottom` | Retain only after MLB Games evidence establishes this feed's own batter-relative geometry, method, and version history. Do not import Savant `sz_top`/`sz_bot` era semantics by name similarity. |
| Provider zone | `zone` | Nominal classification, not a physical measurement; separate classification pattern. |
| Pitch type | `details.type.code`, `details.type.description` | Accepted: retain every genuine pitch type as a reusable Nominal Measurement ICE under the MLB pitch-type Reference System. It nominally measures the particular Pitch Act and may trigger a separately reviewed Pitch Act subtype. It is not an individual-pitch identifier and does not type the Pitch Ball Motion Process. |
| Pitch-type confidence | `typeConfidence` | Provider score with undocumented scale in current evidence; unresolved, never physical confidence quality. |
| Break geometry | `breakAngle`, `breakHorizontal`, `breakLength`, `breakVertical`, `breakVerticalInduced`, `breakY` | Unresolved until each baseline, direction, unit, and computation convention is documented. |
| Spin | `spinRate`, `spinDirection` | Retain only with rotational Process Profile, axis/direction geometry, unit, frame, and method semantics. |
| Exit speed | `launchSpeed` | Retain as a provider-reported value about a Speed Process Profile; assert direct measurement versus estimate only when row-level evidence distinguishes them. |
| Launch angle | `launchAngle` | Retain as a provider-reported value about reviewed initial-motion Angle Quality; assert direct measurement versus estimate only when evidenced. |
| Projected distance | `totalDistance` | Treat source-specifically as a Projection/Estimate ICE about the batted-ball trajectory; do not invent an actual or merely possible Distance Quality as its target. |
| Hit coordinates | `coordX`, `coordY` | Retain only as an ordered tuple under an explicit provider convention. Do not use Spatial Region or Coordinate System Axis classes. MLB's public documentation still does not define origin, orientation, sign, scale, projection, or unit. Jena polygon containment is allowed only against a polygon expressed under the same provider convention. Until provider-frame-to-field grounding is established, mint no Batted-Ball Location Site and assert no world-side designation, feet, latitude/longitude, or physical distance. |
| Contact hardness | `hardness` | Nominal provider classification, not a measurement magnitude; separate classification pattern. |
| Batted-ball trajectory | `trajectory` | Nominal provider classification; do not replace Batted-Ball Motion Process. |
| Fielding location | `location` | Provider position/location code; information classification, not evidence of a physical fielding act. |

Null values emit no measurement, profile, quality, point, or placeholder. Every
Measurement ICE identity must include the measured entity, evaluation scope,
method/version, source response, and payload hash.
