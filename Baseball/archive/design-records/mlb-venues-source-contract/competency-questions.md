# Competency questions and proposed answers

The answers below are the source-specific decisions submitted for ontologist
review. They do not become executable until this named package is explicitly
accepted and archived.

1. **What persistent entity does the MLB venue `id` identify?**  A Baseball
   Venue, using the same canonical venue IRI already referenced by game-event
   data.
2. **Are the Baseball Venue and Baseball Field Site identical?**  No. The
   Venue is a Facility; the Field is a Site. The response record may be about
   both, but this source emits no direct Venue-to-Field relation.
3. **What realizable entity is borne by the mapped Baseball Venue?**  A named
   Baseball Game Hosting Function grounded in the facility's design for
   hosting Baseball Games. The source does not assert that any particular game
   realizes it.
4. **What is the origin of each admitted field dimension?**  A Fiat Point at
   the intersection of the first-base and third-base lines at home base, under
   the reviewed MLB field-dimension convention.
5. **What does a selector such as `leftCenter` identify?**  A
   response-snapshot-specific Non-Name Identifier uses the MLB venue-dimension
   selector Reference System and designates the provider-selected Fiat Point
   on the Baseball Field Site's boundary.
6. **Does `leftCenter` or `rightCenter` entail a fence, wall, power alley, or a
   universally fixed geometric bearing?**  No. Official sources do not define
   the API keys at that precision. The contract claims only a
   provider-selected field-boundary Fiat Point.
7. **What world-side entity bears the distance semantics?**  A Distance
   Quality that inheres in two nonidentical Fiat Points: the origin and the
   selected boundary point.
8. **What bears the numeric source value?**  A generic CCO Measurement
   Information Content Entity that is a measurement of the Distance Quality.
9. **What unit applies?**  Feet, by the ontologist's accepted domain decision.
   The Measurement ICE directly uses CCO `cco:ont00001714` and carries the
   source number as `xsd:decimal`.
10. **Does the venue response establish a Measurement Process, method, agent,
    estimate procedure, or uncertainty?**  No. None is minted or inferred.
11. **Does a requested `season` establish that a dimension was true throughout
    that Baseball Season?**  No. It scopes the request and response snapshot
    only. No Season relation, temporal interval, or validity claim is emitted.
12. **How are persistent and response-dependent identities separated?**  The
    Venue, Field Site, hosting Function, and venue-ID identifier are stable by
    MLB venue ID. A Proper Name ICE is stable by canonical Venue IRI, reviewed
    MLB official-name kind, and SHA-256 of the exact decoded lexical name, so
    identical nightly names reuse one ICE. The response record, selector
    identifier, selected Fiat Points, Distance Quality, and Measurement ICE
    include the requested season and canonical response SHA-256 where their
    evidence or fiat selection is response-dependent. Each response may still
    have the reused Proper Name ICE as a continuant part.
13. **Can two response snapshots be asserted to select the same Fiat Point or
    Distance Quality?**  Not from this endpoint alone. They remain distinct
    unless a later reviewed reconciliation supplies identity evidence.
14. **What happens when one of the five dimension members is absent or null?**
    Nothing selector-specific is emitted. A present value must normalize to a
    positive `xsd:decimal`; otherwise pre-mapping input validation fails and
    NiFi quarantines the input evidence before RML. Source SHACL separately
    enforces the positive decimal and cardinality contract on emitted RDF.
15. **Can coordinates, azimuth, elevation, capacity, turf, roof, time-zone,
    address, phone, or `active` be mapped in this release?**  No. Their
    referents, units, frames, classifications, temporal scope, or identity
    requirements remain unresolved.
16. **Can the standalone venue lane silently replace or delete existing
    MLB-game assertions?**  No. It first promotes independently. A later
    coordinated cutover must demonstrate identity and query equivalence, while
    already promoted authoritative RDF remains persistent.
17. **How is the source operated?**  As an independent NiFi lane with transient
    API payloads, persistent hashes/manifests and promoted RDF, pre-mapping
    input validation, source-local SHACL, retry/quarantine, and asynchronous
    submission without continuous monitoring.
