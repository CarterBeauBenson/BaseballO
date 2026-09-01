# Competency questions

## Decision requested

1. May a source-owned authority graph for persistent entities also contain the
   accepted one-time Processes that the same source evidences?

   - **Option A — source-owned authority record:** yes. `authority` names the
     source's authoritative reference record, not an exclusive BFO category.
   - **Option B — category-sensitive graph products:** no. The module produces
     an authority graph for persistent continuants and an event/evidence graph
     for one-time occurrents.

2. Under either option, is one-time Process RDF disposable?

   **Candidate answer:** no. It remains persistent authoritative evidence.
   Only indexed RDF and SQL products remain rebuildable/disposable.

3. Under Option B, does splitting graph products create a second source module
   or cross-source RML?

   **Candidate answer:** no. One detachable module owns acquisition, mapping,
   product-specific source SHACL, atomic promotion, retry, quarantine, and
   provenance for both graph products.

4. Under Option B, where does a response Descriptive ICE that is about both a
   persistent continuant and a one-time Process belong?

   **Decision needed:** choose one evidence graph as its home and reference
   across named graphs, or define an explicitly reviewed non-duplicating graph
   partition. Do not copy the same authoritative assertion into both graphs
   merely for convenience.

5. Under Option B, where does a Baseball Season Plan belong?

   **Decision needed:** it is a continuant Plan but prescribes the Season and
   Phase Processes. Its graph placement must follow an explicit evidence and
   query policy rather than treating every object about an occurrent as an
   occurrent.

6. Are response-versioned Measurement ICEs, Date Identifiers, qualities, and
   Fiat Points automatically event facts?

   **Candidate answer:** no. Each retains its ontology category. Graph
   placement follows the accepted product policy and evidence ownership; the
   type of a related Process does not determine the type of these continuants.

7. What is the promotion unit under Option B?

   **Candidate answer:** the module's authority and event/evidence products
   validate separately and promote as one atomic source-run outcome so a
   partial graph pair never represents success.

8. Does either option alter source-independent canonical IRIs?

   **Candidate answer:** no. Named-graph placement does not change entity
   identity.
