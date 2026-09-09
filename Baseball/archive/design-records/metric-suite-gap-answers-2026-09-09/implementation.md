# Implementation of the September 9 answers

The prior decision commit `d12b742` records accepted questions 1–6, 8 and 9.
Question 7 remains an explanation request; no continuity criterion is accepted.

The calculation layer now provides:

- Exact independent advancement with marginal values 1/3, 1/2 and 1, with
  advancement, damage and net reported separately. Its SPARQL component is
  cataloged separately from the existing 20 public metrics.
- PAQ-A cohort construction from admitted immediate pre-consequence base/out
  states, preserving the declared reference population and boundary evidence.
- Review-dependence calculations with separate traditional-replay and
  ball/strike-challenge populations. Known eligible decisions remain in the
  denominator even when never reviewed; unknown eligibility or dependence
  prevents the affected score.

Policy and gap documentation also records that supported safe end states need
not assert physical location or stasis, supported operative outcomes can serve
ordinary scoring without original review calls, and official PA attribution
must remain separate from actual consequence contribution. Their authoritative
graph representation and complete source evidence remain pending. No ontology,
RML, source SHACL, identity rule, semantic pin or live admission changed.

The independent calculation accepts already supported, consolidated participant
paths. Conflicting segments for one runner are rejected rather than joined.
Missing live evidence continues to produce named unavailable results.

Focused validation passed: 38 Python tests covering metric arithmetic, serving,
movement evidence and these decisions; eight browser/compiler parity tests;
and the metric generator drift check. Full repository validation remains the
asynchronous NiFi observer's responsibility.
