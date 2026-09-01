# Authority-graph placement of one-time occurrent evidence

Status: **under review — design only**

This package asks what the word *authority* means at the named-graph boundary
when a detachable reference-source module maps both persistent continuants and
one-time occurrents. MLB people owns persistent Person reference facts but also
maps Birth Processes. MLB organizations owns persistent Organization reference
facts but also maps Baseball Season and Baseball Season Phase Processes.

The decision is between:

- **Option A — source-owned authority record:** an authority graph is the
  authoritative record produced by that reference source and may contain its
  accepted one-time Process evidence alongside persistent continuants; or
- **Option B — category-sensitive graph products:** the same detachable source
  module promotes persistent continuant facts to its authority graph and
  promotes one-time Process evidence to a separate event/evidence graph.

Both options keep RDF persistent and authoritative. Neither makes event RDF
transient, moves integration out of the triple store, creates another source
module, or permits RML/SHACL to cross source boundaries. The question is graph
placement and lifecycle, not whether Birth, Season, or Season Phase is a
Process.

No ontology term is proposed. No executable graph split is authorized until
the ontologist selects an option and answers where shared response and Plan
ICEs belong.
