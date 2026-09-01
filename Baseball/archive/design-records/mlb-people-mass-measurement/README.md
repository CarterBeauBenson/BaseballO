# MLB people mass measurement

Status: **accepted 2026-08-30 — source-independent design**

This package asks whether MLB's person-level 'weight' value may be mapped as a
measurement of the Person's Mass in pounds. It does not model CCO Weight, invent
a measuring process, or treat the integer as an intrinsic identifier.

The accepted people contract withheld the field only because its unit was not
then established. For this review, the source fact is now explicit: the MLB
value is expressed in pounds. CCO Mass, generic Measurement Information Content
Entity, and Pound Measurement Unit already supply the world and information
structure. No class or object property gap remains.

The field is already present in the authoritative MLB game payload. Approval
would resolve its semantics for the accepted people-source ownership lane; it
would not authorize duplicate emission, an ownership cutover, RML, SHACL,
NiFi, promotion, or removal of existing game RDF.

Successful future API payloads remain transient. The people module must remain
detachable and retain only hashes, validation evidence, provenance, and
promoted RDF after successful promotion.
