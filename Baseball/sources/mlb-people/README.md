# MLB people source module

This detachable module owns accepted reference facts from the MLB Stats API
people endpoint. Its own connector discovers the season's MLB player
population and acquires the corresponding person records. Corpus identifiers
may supplement later backfills, but the lane does not depend on Games to run.

- Successful API bytes are transient. NiFi retains request and response hashes,
  validation evidence, graph hashes, and promotion provenance.
- `mapping/prepare-context.py` validates the selected source fields before RML
  and creates an execution-only context document.
- `mapping/mlb-people.rml.ttl` emits the accepted realist graph shape.
- `shacl/authoritative.ttl` validates only RDF emitted by this module.
- Promoted graphs use the immutable authority prefix
  `https://w3id.org/baseball/graph/authority/mlb-people/`.

The executable surface includes Person identity, names, Height and Mass
measurements, Birth/date evidence, batting- and throwing-side Dispositions,
and reviewed primary-position descriptions of real Role/Disposition clusters.
`currentTeam.id` remains response aboutness only: this reference endpoint does
not create a Player Role, Stasis, Gain, or Loss. Uniform-number assignment also
remains outside the mapping.

The `MLB People` NiFi group passed its bounded proof. Its enabled 05:00 Eastern
trigger discovers the current season's player population before sending
independent detail requests. Successful records promote to source-owned Person
authority graphs; one failed Person request does not stop another source
module. Current run status belongs to source-local terminal NiFi evidence, not
this module contract.
