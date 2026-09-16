# Complete pitch histories and Two-Strike Extension Rank

`pitch-count-admission.py` implements an E1/Q5 completeness proof over the
existing MLB game graph. Source counters constrain a source-owned SHACL
profile; they never become metric values or new authoritative assertions.

The source census enumerates official PAs and count events in the final feed,
checks count changes, pitch identities and times, accounts for already
accepted automatic awards, and checks supported PA termination. Unresolved
corrections, non-pitch awards, call kinds, event ordering or termination
withhold the entire game. The retained census includes the existing Q5
selector's exact reasons for withholding automatic awards.

Parameterized SHACL then checks exact pitch membership, interval and timestamp
paths, counted Strike Processes and their judgments/decisions, and automatic
awards and neighboring-pitch precedence. A foul tip reuses its existing
Strike Process individual and accepted judgment/decision subclasses. It does
not acquire a duplicate strike. Date-time values compare by their typed value,
so equivalent UTC/offset or fractional-second spellings do not fail conformance.

The existing NiFi SHACL stage retains the source/RDF/implementation/shape/report
hashes and passes their manifest through graph promotion. The SQL materializer
rechecks those hashes and provenance. Old, missing or mismatched proofs cannot
admit Recovery. A withheld metric proof does not disable the accepted ingester.

The canonical query obtains pitch chronology from existing typed temporal
paths, and automatic-award placement from existing precedence. The reducer
counts institutional strikes, identifies the first two-strike state, and
counts later nonterminal pitches. Automatic awards add no pitch. A known PA
that never reaches two strikes is ineligible, not a zero or missing result.
Official PA assignment and roster exposure still require independent B1
admission. Every official PA must be accounted for before the per-game inputs
are retained as complete.

The player producer reads those exact inputs from SQL across the regular
season through the reporting cutoff. Every reference calendar day, including
zero-game days, needs independent schedule evidence. It ranks the entire
eligible season population before selecting display dates. Each player's
output is the exact mean of their selected applicable PA percentiles, with
official PA and applicable-PA qualification kept separate. Seasons are ranked
separately when a display spans years. Non-regular-season Recovery remains
unavailable; no out-of-reference extrapolation is inferred.

All four percentile calculators now use exact rational tuple grouping and
cumulative ranks instead of a quadratic pairwise join. Tests compare their
answers with the unchanged canonical SPARQL kernels, including ties, separate
cohorts and very large fractions. The canonical RDFLib verification path uses
sufficient decimal precision for integer cross-products; no score is rounded.

## Evidence and release limits

The [reference-game proof](../../../benchmarks/metrics/recovery-inputs-2026-09-15/README.md)
checks all 79 official PAs and 282 pitches in game 566279, through Jena and SQL.
There are 40 eligible PAs and 39 known ineligible PAs. This is a complete
one-game input proof, not a complete-season leaderboard.

For game 824087, Q5 withholds automatic strike
`6e1edbb8-f263-41d9-9613-56400d396d2f` in PA 32 with
`UNRESOLVED_COUNT_REVIEW`. The existing selector excludes awards in a PA
containing a review. The source award is present; its graph admission is
unfinished. Four additional pitched-strike cases are covered by the separate
draft M3/M4 proposal. No selector, mapping, ontology or freeze pin was changed
by this component.

The new profile and four pre-existing metric profiles are registered in the
source-owned `pipeline/validation-profiles.json`. The ownership validator
retains exact membership and unique ownership across operational profiles and
the pinned source contract. The protected catalog and freeze remain unchanged.
The [unnecessary approval request was withdrawn](../../../archive/design-records/mlb-game-metric-profile-registration/disposition.md).

The [nineteen-metric status](../../../serving/METRIC-READINESS.md) distinguishes
implemented player producers from remaining work and live population admission.
