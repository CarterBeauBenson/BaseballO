# Failure and repository evidence

The quarantined Teams run `c9dcfa4afcdb443aa878920c559e636b` failed three
times at `corpus-seed` before any MLB Teams request. All five promoted game
indexes carried exact-build fingerprint
`70457857e549b78c5dfb8fb92ceb7b2670fd6fa635bc1da5db4111fbd423fcc5`.
The PowerShell helper admitted the dynamically calculated current fingerprint,
while `materialize-serving-layer.py` admitted only the fixed Explorer-routing
fingerprints, whose current routing value was
`8498a513f7468faa65b3f9c68bf196ca8fd1ecf62785b90d7e05decaf7ee497c`.

`process-source-lane-stage.py` imported `materialize-serving-layer.py` solely to
reuse its promotion inventory. That made the Teams acquisition prerequisite
depend on an Explorer serving decision. The exact-build fingerprint also
included orchestration scripts, so adding process-wide Fuseki write locking
changed it without changing the indexed RDF grain.

The NiFi configurators independently duplicate processor state, wait, update,
and connection code. Their stop guarantees and selection scopes differ. The
same edit-while-running race appeared first in source-lane configuration and
then in corpus-audit configuration.

Teams cleanup also constructed League and Division run references before
writing Teams `completion.json`. A downstream reader could therefore begin
before the evidence it requires existed, and a missing downstream configuration
could prevent Teams from recording its own successful completion.

These are control-plane and contract-boundary defects. The five authoritative
game graphs remain valid persistent evidence; the five query-index graphs
remain valid derived, rebuildable products.

The semantic-freeze path classifier also used filename substrings such as
`rdf` and `context` for scripts. That caused NiFi configurators and stage
wrappers to inherit ontology-style approval requirements despite not declaring
semantics. The accepted boundary is artifact responsibility, not vocabulary in
a filename.
