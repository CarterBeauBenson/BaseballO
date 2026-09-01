# MLB venues source semantic audit

Status: **approved surface; audited 2026-08-30**

The executable module implements only the solid graph contract accepted in
[`mlb-venues-source-contract`](../../archive/design-records/mlb-venues-source-contract/review.json).
It declares no new ontology term and imports no mapping or SHACL artifact from
another source.

## Admitted graph surface

- canonical Baseball Venue, stable MLB venue identifier, exact Proper Name,
  Baseball Game Hosting Function, and Baseball Field Site;
- response DICE about the Venue and Field and containing its admitted ICE
  parts;
- one provider-selector identifier and selected boundary Fiat Point for each
  non-null positive field dimension;
- one Distance Quality inhering in the response origin and selected boundary
  Fiat Points; and
- one generic Measurement ICE with a positive decimal value and CCO Foot
  (`cco:ont00001714`);
- a stable Venue Reference Point designated by response-versioned WGS84
  coordinate information;
- a stable Spectator Accommodation Amount with response-versioned positive
  integer capacity measurement;
- response-supported material Playing Surface and support Function with a
  nominal type classification; and
- a response-supported Roof and covering Function for `Dome`/`Retractable`, or
  an information-only Venue classification for `Open`.

There is no direct Venue-to-Field edge and no Measurement Process. Requested
season identifies the response snapshot; it is not mapped as season-long
temporal validity.

## Validation split

`mapping/prepare-context.py` validates source mechanics before RML. A missing
or JSON-null selector is permitted and emits nothing. A present nonnumeric,
nonfinite, or nonpositive value fails before mapping so RML cannot silently
drop the bad field. The same gate requires complete coordinate pairs, valid
ranges, positive integer capacity, and exact pinned surface/roof codes.

`shacl/authoritative.ttl` validates the emitted graph before promotion. It
checks stable identities, response aboutness and parts, Venue/Field separation,
selector designations, exact two-point Distance Quality structure, Foot unit,
positive decimal values, coordinates, capacity, material-part/Function
structure, classification evidence, and response-local cardinality.

## Explicitly excluded surface

The RML contains no references to `active`, azimuth, elevation, address, phone,
or time-zone fields. Capacity never enumerates Seat or Standing-Room
particulars. Surface and Roof classifications never assert Function
realization; `Open` never creates a Roof; a retractable type never creates an
open/closed state.

## Operational boundary

The source response and derived RML context are transient. NiFi preserves
request metadata, exact-byte response hash, mapping hash, validation evidence,
and promoted graph-pair provenance. Failed inputs remain source-local in
quarantine. Successful raw inputs are removed only after promotion. The lane
is detachable and meets other sources only in the authoritative triple store.
