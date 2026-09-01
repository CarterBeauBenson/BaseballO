# ICE direct values, units, and reference systems

Status: **accepted by the ontologist on 2026-08-29; implementation pending**

This package proposes the prerequisite foundation repair for BaseballO's
intended measurement pattern: an Information Content Entity (ICE) directly
carries its literal value and directly uses the Measurement Unit or Reference
System needed to interpret that value. It does not introduce an intermediate
Information Bearing Entity (IBE).

The pinned CCO 2.1 snapshots currently give the generic value properties and
the `uses measurement unit` / `uses reference system` relation families IBE
domains. Because CCO also separates ICEs from material IBEs, using those
relations directly on a Measurement ICE currently produces an unintended IBE
inference. The current `uses` relations are also subproperties of the BFO
carrier relation, which cannot be retained when their subjects are ICEs.

This proposal therefore changes the domains and definitions of existing CCO
relations. It creates no BaseballO class and no object property. The user's
phrase "uses reference unit" is implemented through the authoritative CCO
property named `uses reference system`; no similarly named property is
invented.

No active ontology or dependency snapshot is changed by this package. If the
ontologist accepts it, implementation must happen in a later commit and update
both pinned copies consistently:

- `Baseball/ontology/CommonCoreOntologiesMerged.ttl`
- `Baseball/ontology/ModalRelationOntology.ttl`

The 31-class curation repair depends on this decision for timestamp and field
coordinate ICEs. MLB and Statcast proposals may cite the intended pattern, but
no executable mapping may use a newly proposed term or assumption before the
decision is accepted and implemented.

## Review boundary

The exact changes are in [proposed-changes.md](proposed-changes.md). Adjacent
IBE relations such as `uses language` and `uses time zone identifier` are
deliberately outside this decision. They are listed as follow-up consistency
questions rather than silently broadened.
