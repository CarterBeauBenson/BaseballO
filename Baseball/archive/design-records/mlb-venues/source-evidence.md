# Source and de-duplication evidence

## Official endpoint inspected

The proposal inspected this official MLB Stats API request transiently on
2026-08-28:

`GET https://statsapi.mlb.com/api/v1/venues/3313?hydrate=location,timezone,fieldInfo&season=2019`

A second shape check used:

`GET https://statsapi.mlb.com/api/v1/venues/2680?hydrate=location,timezone,fieldInfo&season=2019`

The responses contained identity/name/status, address strings, default
coordinates, azimuth, elevation, time-zone data, capacity, turf and roof types,
and five field-dimension values. No response JSON was written to the
repository.

## Complete overlap with the authoritative game payload

`Baseball/sources/mlb-game/schema/mlb-feed-path-inventory.csv:247-278`
contains the same venue surface under the authoritative game source, including
all location, time-zone, and field-info members. The active mapping already
owns venue identity, name, and field-site creation in
`Baseball/sources/mlb-game/mapping/mlb-game.rml.ttl:580-619`.

Accordingly, none of the standalone venue fields is genuinely additional.
An endpoint may widen which venue records can be discovered, but population
coverage is not a new semantic predicate. A future reference lane requires an
explicit assertion-ownership decision; it cannot silently shadow the MLB-game
lane.

## Semantic evidence limits

The endpoint supplies values but does not define:

- which physical point the default coordinates locate or their CRS;
- field-dimension endpoints, path, unit, or measurement method;
- azimuth directions, shared point, frame, unit, or method;
- elevation unit, vertical datum, or exact bearer;
- capacity's counted entity, configuration, or effective time;
- the world-side target of turf and roof classifications; or
- the time at which each offset is valid.

Those are not property shortages. Existing BFO/CCO relations can connect the
needed entities once their classes, identity, and evidence are established.

## Existing vocabulary coverage

BaseballO already supplies Baseball Venue and Baseball Field Site. CCO/BFO
already supply Descriptive Information Content Entity, Nominal Measurement
Information Content Entity, Reference System, Time Zone Identifier,
Geospatial Position, Coordinate Reference System, Altitude, Measurement
Information Content Entity, Measurement Unit, Site, Fiat Point, Fiat Line, and
the needed accepted relations. The generic Angle Quality and Distance Quality
patterns remain separately proposed in `realist-geometry-foundations`.
