# Accepted TFS arithmetic examples

`tfs-policy-arithmetic.rq` is a synthetic SPARQL regression component invoked by
`tests/test_tfs_policy_arithmetic.py`. Fifteen complete hypothetical examples
cover the supplied primitives and accepted error/FC, stranded-runner,
continuous-path terminal-out and shared-play erosion policies.

Its VALUES rows are local test inputs, not a new graph, source contract,
ontology vocabulary, serving schema or production metric route. They assert
their admission assumptions explicitly. The test does not derive attribution,
continuity, an unchanged runner, stranding or a common event boundary.

The arithmetic returns exact integer numerators over 36. Every valid primitive
denominator divides 36; there is no display rounding. Expected reduced
fractions are independently recorded from the reviewed examples and compared
component by component. Mean and percentile calculations are not covered by
this fixed denominator representation.

Production scoring remains gated by the reviewed authoritative graph pattern,
source SHACL, proof, completeness and admitted analytical population.
