# Complete Recovery inputs from existing RDF

The unchanged reference game 566279 passes current RML and authoritative source
SHACL, followed by the new pitch-count admission and independent B1 admission.
No ontology, RML, source byte or protected semantic pin changed.

- 79 official PAs; 282 pitches.
- 40 two-strike eligible PAs; 39 known ineligible PAs.
- Eligible raw extension steps: 19 at zero, 9 at one, 6 at two, 1 at three,
  and 5 at four.
- Canonical Jena extraction and exact SQL-retained inputs agree.
- Per-game input completeness is true; season and live population completeness
  are false. These are not season percentiles or populated leaderboards.

`result.json` retains the exact identities, ordered count traces, fractions,
input/RDF/implementation hashes and admission/report hashes. The proof is
reproducible with `tests/prove_recovery_inputs.py` using the immutable source,
an isolated validated RML manifest, the Jena runtime and an output directory.
It performs no corpus promotion or live materialization.

Focused tests cover automatic second strikes contributing zero pitches,
foul-tip subtype reuse, equivalent typed timestamps, unknown/overlapping order,
missing/extra graph members, proof tampering, season coverage before the display
start date, exact selected-date means, complete B1 membership and known versus
unknown eligibility. All four percentile implementations are compared against
the retained canonical SPARQL kernels, including exact large fractions, ties,
separate cohorts and a 20,200-observation nonquadratic path.

The source-module ownership check has a separate known failure: five metric
profiles are absent from the pinned catalog. The
[proposed registration](../../../proposals/mlb-game-metric-profile-registration/README.md)
passes the unchanged catalog and source-scope validators in isolation. The
actual protected catalog and pin remain unchanged pending named approval.
That release gate is not made to pass by this developer proof.
