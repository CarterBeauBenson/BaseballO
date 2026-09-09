# C1/C2 implementation

Acceptance was recorded and pushed in `39bae57` before these changes. No new
object property, ontology class or RDF Person-to-Base shortcut was introduced.
The accepted slice is archived; the larger metric review remains active only
for its other unresolved requirements.

Implemented:

- C1 source-owned SHACL for the personal BFO Process, its Half Inning and
  Temporal Interval, same-runner episode membership, and compatible terminal
  structure. The whole is distinct from its single act/resolution episodes
  and does not inherit their agency or Role realization.
- The source IRI policy documents the accepted lifetime grain without minting
  personal wholes from source row adjacency. The existing RML is unchanged.
- Whole/episode/interval evidence extraction, IRI validation and SQL retention.
  Observed whole membership does not certify complete history.
- C2's canonical SPARQL component and serving helper for an already admitted
  ordered history. Unknown coverage/boundaries, unresolved state changes,
  concurrent ambiguity and terminal changes withhold stale safe-base results.
  New supported safe outcomes supply updated state. Stranding is evaluated
  before the independently supported inning reset. Projection assigns no
  contribution credit and asserts no RDF relation.
- Current policy and gap records distinguish accepted C1/C2 from the remaining
  source evidence. Only the approved IRI-policy and source-SHACL pins changed;
  unrelated semantic pins and the unratified baseline status are preserved.

Focused verification passed 31 Python tests and eight browser/API/compiler
tests, plus the generator drift check. The new C1 one-game graph fixture also
passed Apache Jena SHACL; a mixed-runner mutation correctly failed. These
synthetic admitted-evidence checks establish component behavior, not the
completeness of any real game's history.

The first unpassed source gate is documented in the
[source contract](../../../sources/mlb-game/review/runner-continuity-source-contract.md).
No existing adapter supplies independently verified complete real histories
with supported lifetime and evaluation boundaries. No personal-whole RML
source or complete-history flag is fabricated to bypass that gate. Live
dependent metrics remain unavailable until those inputs are evidenced.
