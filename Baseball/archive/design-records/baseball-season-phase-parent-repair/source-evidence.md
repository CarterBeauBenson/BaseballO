# Source evidence

This is an ontology-curation repair rather than a new external-source mapping.

The accepted ontology currently states:

- `BaseballSeasonSegment rdfs:subClassOf BFO Process`; and
- `BaseballSeasonPhase rdfs:subClassOf BaseballSeasonSegment`.

An earlier declaration also directly states
`BaseballSeasonPhase rdfs:subClassOf BFO Process`. The repository curation gate
therefore reports two direct named parents for `BaseballSeasonPhase`.

Removing the earlier direct assertion leaves the accepted subclass chain and
all overlay restrictions intact.
