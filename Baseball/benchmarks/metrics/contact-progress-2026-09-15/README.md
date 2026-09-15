# Accepted contact continuations in the player producer

Game 824315, PA 6 now passes through the same contribution adapter used for
Offensive Reach, Hidden Help Rate, Empty Games and Contribution Mix. The
accepted B2 example's six resolutions form three existing C1 personal paths:

- Angel Martinez: batter origin to first, then out. No positive contribution.
- Travis Bazzana: first to second to third. One positive runner trajectory.
- Nathaniel Lowe: second to third to counted score. One positive runner trajectory.

Offensive Reach is **2**. The batter-other channel occurs once for the contact,
not once per beneficiary. No intermediate batter-self channel survives the out.

The immutable source hash and previously validated 38,422-triple RDF hash are
bound in `result.json`. Fresh B2 source-owned SHACL conforms; Jena evaluates
the canonical query; SQL retains the complete bindings and reproduces the
same contribution results. No ontology, RML, source bytes or source SHACL changed.

Thirteen focused player-producer tests cover all four outputs, exact SQL
equivalence, binding-order independence, missing/ambiguous whole membership,
missing resolutions, independent-channel mixing, branching, reverse and
disconnected paths. Existing single-resolution and qualification tests pass.
`regression.json` also retains the complete 73-PA, 90-resolution reference-game
proof for all four player producers, including fresh source conformance and
exact SQL agreement. Its public range still requires independent schedules.

This proves the accepted continuation in an older complete game graph, not a
new complete live player population. Its two unresolved PAs remain explicit:
PA 13 lacks the queried C1 support needed for its multisegment path, and PA 63
has a strikeout/wild-pitch reach without an admitted positive channel. These
are coverage limitations of this graph and adapter, not claims of absent
provider records. Selected-schedule and all applicable admission gates remain.

The proof is reproducible with `tests/prove_contact_progress.py` using the
source, validated RML manifest, Jena runtime and explicit PA/reach arguments.
It reads the isolated graph and never promotes or rebuilds the live corpus.
