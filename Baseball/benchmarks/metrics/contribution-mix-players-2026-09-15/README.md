# Contribution Mix player proof

The unchanged source game 824087 was checked against its existing validated
29,276-triple RDF fixture. Fresh Jena source conformance verifies all 73
official PAs, all 90 runner resolutions, and the existing Steal Attempt
typing. The canonical Jena SELECT and retained SQL bindings produce identical
Contribution Mix player results, including exact channel counts and
separately counted independent running participation.

The isolated game has 17 defined player entropy scores; 15 meet the accepted
one-game qualification. Players with no positive contribution have an empty
entropy denominator. The source, RDF, implementation and conformance evidence
hashes, player counts, channel occurrences and existing batting-progress
regressions are retained in [result.json](result.json).

This is an explicit one-game developer proof. No schedule record or complete
date population was fabricated. The public SQL request correctly withholds
the date range when its independent schedule proof is absent. These results
do not claim a populated live dashboard or full operation of the remaining
thirteen player metrics.

Focused checks cover shared graph/player progress, exact channel counting,
multiple beneficiaries on one play, zero-PA running eligibility, nonpositive
attempts, uncertain strikeout/caught-stealing strategy, missing/spurious
Steal Attempt typing, and corrupt proof data. The existing nine Node tests
also pass for both qualification routes, logarithmic display, canonical
Python/SPARQL agreement, ranking and dashboard HTTP delivery.
