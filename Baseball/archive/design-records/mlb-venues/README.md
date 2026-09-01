# MLB venue API coverage and ontology-gap review

Status: **accepted gap and de-duplication record on 2026-08-29; no mapping authorized**

This package evaluates the standalone MLB venue endpoint against the
authoritative MLB game payload. The checked game contract already contains the
entire observed venue surface: identity, name, address strings, geographic
coordinates, time-zone fields, turf and roof classifications, capacity, field
dimensions, azimuth, and elevation. A missing RML binding is MLB-game mapping
coverage debt; it does not make the same field semantically new in a second
lane.

The current conclusion is therefore that a standalone venue lane has no
demonstrated nonduplicative field surface. It may later provide population
coverage or refresh behavior, but that requires an explicit ownership
migration or coverage partition before acquisition, RML, SHACL, or NiFi work.

No class or property is proposed. Existing `BaseballVenue` and
`BaseballFieldSite` preserve the physical venue/site distinction. Existing CCO
terms cover descriptive information, nominal classifications, coordinates,
reference systems, measurements, time-zone identifiers, Altitude, Fiat Points,
and Fiat Lines. The useful result of this review is the list of bindings that
must remain blocked in the owning MLB-game lane:

- the physical point and coordinate reference system for
  `defaultCoordinates`;
- the endpoints, path, unit, and method for each field dimension;
- the two directions, shared point, frame, unit, and method for azimuth;
- the unit, datum, and exact bearer of elevation;
- the counted entity, configuration, and time for capacity;
- the classified referent of `turfType` and `roofType`; and
- the temporal interpretation of time-zone offsets.

This package does not authorize ontology implementation, a venue source
module, RML, SHACL, NiFi changes, RDF promotion, SQL materialization, or UI
exposure.
