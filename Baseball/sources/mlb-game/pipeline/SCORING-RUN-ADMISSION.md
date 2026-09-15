# Counted runs and player means

This implements the already accepted E1/C1 complete-population and
selected-range scoring-runner display contracts. It adds no ontology terms,
RML mapping, identity policy, source lane or global semantic admission.

`scoring-run-admission.py` reconciles the final source's scoring membership,
inning/team run totals and complete game roster. Expected existing Run and
Baserunning Act identities and scorer/roster bindings parameterize the owning
`shacl/scoring-run-admission.ttl` profile. Missing or additional runs, a wrong
scorer, or a missing roster member withhold admission. Zero runs require the
same positive source reconciliation and exact graph census.

NiFi runs this after ordinary authoritative SHACL and before promotion. The
existing promotion marker binds the proof and its retained source, shapes and
report hashes. The SQL materializer verifies source/RDF identity, current
implementation and retained evidence. It imports only proof provenance into
`metric_suite_run_admission`; source-census numbers never supply metric facts.

The canonical RDF query supplies runs, C1 membership and realized game roster
context. The scorer producer requires every counted run to have exactly one
complete scoring history, and every selected schedule date/game to reconcile.
It then pools episode depths by scoring runner and publishes exact sums and
counts for player means. Non-scoring game roster exposures remain in the
qualification denominator. Run qualification uses runs scored, so the producer
does not invent official PA counts for pinch runners or require B1 batting
admission. A player with no scored runs has no run mean.

This is a conditional live producer, not a declaration that a deployed range
is complete. Missing C1 histories still withhold the selected population. The
new proof is required on the next normal source proof/refresh; an old build
cannot acquire admission merely because the serving code changed.
