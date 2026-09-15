# M1/M2 mapping proof

Scope: the accepted counted-foul and affirmed-pitch-review extension, using
unchanged MLB game 824315 from August 23, 2026. This is isolated developer
evidence; it does not record live promotion or completed player metrics.

The [result](result.json) binds source, context-builder, mapping, SHACL and RDF
hashes. The [source evidence and decision](../../../archive/design-records/mlb-game-metric-mapping-completion/README.md)
were published before implementation.

Verification proceeds from one PA through the full game:

- Production RMLMapper executes the one-PA source fixture containing a counted
  foul and a nonterminal affirmed review. Focused source SHACL passes.
- A separate synthetic duplicate PA/pitch narrative exercises canonical review
  identity in the actual RML engine and produces one review.
- Full-game RML, generated-RDF checks, Jena source SHACL and exact C1/M1/M2
  source-to-RDF reconciliation pass.
- Thirteen source/conformance tests include invalid counters, unsupported
  resets/times, substitutions, held-count fouls, two reviews in one PA,
  conflicting narratives, missing officials, mismatched decisions, extra
  outputs and incorrectly inherited umpire attribution. Six existing review
  context regressions also pass.

The game adds **21 counted second-strike fouls** to the existing 20 first-strike
fouls. The 27 source candidates do not all pass the admitted prefix gates;
the retained manifest identifies withheld rows and reasons. Two additional
pitch-level reviews coexist with the existing play-level review: three
distinct reviews, without duplicate counted pitch outcomes.

NiFi owns repeatable execution and the existing queued proof/refresh. Its
source SHACL gate remains before promotion. A healthy asynchronous run is not
polled as part of this developer proof, and a pending corpus refresh is not
reported as already reflected in the dashboard.
