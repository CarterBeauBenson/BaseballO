# MLB venues source module

This is the detachable authoritative-reference lane for the official MLB Stats
API venues endpoint. It implements the accepted source-specific contract and
maps venue identity/name, the venue's hosting Function, the Baseball Field
Site, the five reviewed stadium-distance fields, coordinates, capacity,
playing-surface evidence, and roof/configuration evidence.

- [`mapping/mlb-venues.rml.ttl`](mapping/mlb-venues.rml.ttl) owns all source RDF
  semantics.
- [`mapping/iri-policy.yaml`](mapping/iri-policy.yaml) pins identity, unit,
  missing-value, and source-lifecycle rules.
- [`mapping/prepare-context.py`](mapping/prepare-context.py) performs
  pre-mapping validation and creates a transient RMLMapper context without
  rewriting source bytes.
- [`shacl/authoritative.ttl`](shacl/authoritative.ttl) is the source-local
  post-RML/pre-promotion graph gate.
- [`schema/`](schema/) documents the admitted response mechanics and contains a
  synthetic one-record fixture.
- [`review/semantic-status.json`](review/semantic-status.json) records the
  approved semantic state; [`SEMANTIC-AUDIT.md`](SEMANTIC-AUDIT.md) records the
  implemented boundary.

The module has its own MLB Venues API connector. It does not consume a Games
payload or depend on the Games lane to discover venues.

## Execution contract

NiFi stages an exact API response as `venue.json`, records its SHA-256 and
requested season, and runs:

```powershell
python mapping/prepare-context.py venue.json venue-context.json `
  --requested-season 2025 `
  --expected-sha256 <exact-response-sha256>
```

RMLMapper runs `mapping/mlb-venues.rml.ttl` with `venue-context.json` beside
the staged mapping. The candidate RDF must conform to
`shacl/authoritative.ttl` before source-owned authority-graph promotion. The execution context is
derived and disposable; the promoted RDF and provenance/evidence manifest are
persistent.

Missing or null selected fields emit nothing. Present invalid dimensions,
coordinate pairs, capacity values, or pinned surface/roof codes fail before
RML and are quarantined. SHACL validates the emitted realist structures and
their response-versioned measurement or classification evidence.

The `MLB Venues` NiFi group passed its bounded proof. Its enabled 05:00 Eastern
trigger discovers the season's venue population before sending independent
detail requests. A healthy run is asynchronous and is not polled continuously;
current status belongs to source-local terminal NiFi evidence. Source-catalog
registration and the process-group contract are active and version controlled.

## Deliberate exclusions

Azimuth, elevation, addresses, phone data, time zones, and provider `active`
status remain unmapped. Capacity does not enumerate Seats or Standing-Room
Sites. `Open` roof information creates no fictional roof artifact, and a
retractable type creates no open/closed state. The module emits no direct
Venue-to-Field relation, no Measurement Process, no Function realization, and
no claim that a response-held condition persisted for the requested season.
