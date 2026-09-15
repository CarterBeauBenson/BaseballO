# Both run metrics from a complete scoring population

Game 824087 now passes a fresh whole-game RML and Jena SHACL check with 29,276
triples, 21 personal histories and 37 episode memberships. All seven counted
runs have complete histories. The independent source-owned run/roster census
also conforms. The immutable source hash is retained in `result.json`.

The canonical Jena query yields all seven depth and breadth results with no
unresolved run. Both results survive SQL storage exactly. Breadth traces the
accepted contact-play, normative-award and independent-steal channels and
retains contributor identities and supporting graph evidence. The resolved
reviewed walk contributes through its final operative award; no original call
was inferred. Exact scorer means are tested in an explicitly isolated one-game
scope. They are not substituted for the full day's MLB schedule.

The public SQL request correctly withholds the player population when the
independent complete selected-schedule proof is absent. NiFi must refresh and
promote current source evidence, materialize it and reconcile the selected
schedule before the live dashboard can show those player averages. This proof
does not assert a deployed complete range or completion of the other metrics.

Focused checks passed: 26 source-history/award tests, 32 graph/query/SQL run
tests, 30 proof-freshness/recovery tests, and 43 dashboard/API tests. The HTTP
tests cover both dashboard and expanded rankings receiving graph-scoped player
names without changing scores. Detail views use contributors for breadth and
episodes for depth. Source counterexamples continue to reject unresolved
reviews, inconsistent counts, pinch-runner replacements and missing true
lifetime anchors.

Proof freshness now also verifies the owning context builder's path and hash.
An older completed context proof cannot release the current corpus merely
because the RML template stayed unchanged. NiFi's existing asynchronous
recovery handles a completed obsolete proof; this change does not poll or
resubmit healthy source work.
