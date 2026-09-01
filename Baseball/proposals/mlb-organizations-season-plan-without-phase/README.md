# MLB organization Season/Plan evidence threshold

Status: **under review — design only**

This package asks one source-contract question: when an MLB league response
contains a season code but contains no complete accepted regular-season or
postseason date pair, does that response support emitting the Baseball Season
and Baseball Season Plan subgraph?

The current accepted implementation exposes a real tension. Its context
builder emits a Season and Plan whenever it has a league ID and season code,
but emits a Baseball Season Phase only for a complete reviewed date pair. Its
source SHACL profile requires every emitted Baseball Season Plan to prescribe
at least one Baseball Season Phase. A response can therefore pass the source
input gate and deterministically fail after RML without containing a malformed
value.

This package offers two choices and proposes no new ontology term:

- **Option A — complete-pair gate:** emit no Season, Plan, season identifier,
  or Plan-part date evidence until at least one reviewed phase pair is
  complete. Keep the current SHACL minimum of one Phase.
- **Option B — season-code evidence:** a league ID and season code are enough
  to emit the Season and Plan even when this response does not evidence a
  Phase. Relax the source-graph SHACL Phase minimum while preserving the
  ontology's open-world claim that a Baseball Season Plan prescribes some
  Baseball Season Phase.

Option B distinguishes an incomplete source graph from a claim that the Plan
has no Phase. Option A instead requires this source response to carry enough
local evidence before typing the Plan at all. Neither choice authorizes an
ontology, RML, SHACL, NiFi, graph, or query change while this package remains
under review.

Review the alternatives in
[`competency-questions.md`](competency-questions.md) and
[`source-independent-mermaid.md`](source-independent-mermaid.md).
