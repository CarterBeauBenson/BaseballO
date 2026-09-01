# Field-level selection inventory

Every field below is compared with the authoritative MLB game payload, not
only with the current RML output. Each row uses one gate disposition.

| Source field or family | Disposition | Consequence |
| --- | --- | --- |
| `id` | identity or join only | Reuse canonical MLB venue identity; do not create a second venue. |
| `link` | deterministically derivable | Navigation metadata only. |
| `name` | authoritative duplicate | Already present and mapped by the MLB-game lane. |
| `active` | authoritative duplicate | Present in the game contract; provider-status meaning remains insufficient for a world-state assertion. |
| `season` | identity or join only | Request/snapshot context, not physical venue identity or a validity interval. |
| `location.address1`, `city`, `state`, `stateAbbrev`, `postalCode`, `country`, `phone` | authoritative duplicate | All occur in the observed game contract; strings do not establish geographic entity or organizational identity. |
| `location.address2` | unresolved | Not observed in the checked MLB-game path inventory; establish source presence and ownership before treating it as a venue-lane addition. |
| `location.defaultCoordinates.latitude`, `longitude` | authoritative duplicate | Present in the game contract; mapping remains blocked on target-point and CRS semantics. |
| `location.azimuthAngle` | authoritative duplicate | Present in the game contract; mapping remains blocked on Fiat Lines, shared Fiat Point, frame, unit, and method. |
| `location.elevation` | authoritative duplicate | Present in the game contract; mapping remains blocked on bearer, unit, and vertical datum. |
| `timeZone.id`, `tz`, `offset`, `offsetAtGameTime` | authoritative duplicate | Present in the game contract; identifier and offset temporal semantics still require review. |
| `fieldInfo.turfType` | authoritative duplicate | Present in the game contract; classified world-side referent remains unresolved. |
| `fieldInfo.roofType` | authoritative duplicate | Present in the game contract; do not infer a roof artifact or state. |
| `fieldInfo.capacity` | authoritative duplicate | Present in the game contract; counted entity, configuration, and time remain unresolved. |
| `fieldInfo.leftLine`, `leftCenter`, `center`, `rightCenter`, `rightLine` | authoritative duplicate | Present in the game contract; endpoints, path, unit, and method remain unresolved. |

## Source-ownership result

There is no admitted standalone venue field. The owning MLB-game lane may be
extended only after the relevant world-side shape is approved. A later venue
reference lane must prove a nonoverlapping population/ownership contract in a
new review package.

No new class or property IRI is proposed.
