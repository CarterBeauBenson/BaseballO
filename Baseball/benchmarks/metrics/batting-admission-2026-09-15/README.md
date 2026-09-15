# B1 source, graph and SQL proof

The [capture](result.json) records the implementation of the separately
[accepted B1 decision](../../../archive/design-records/batting-leaderboard-admission/README.md).
No ontology, RML, object property or semantic-freeze pin changed.

Game 824315's immutable source and previously validated 38,419-triple RDF
passed the new parameterized source-owned SHACL profile in Jena. The canonical
RDF query supplies 77 recognized completed PA memberships and 52 rostered
players, including 32 with zero PA. Every player's RDF-derived count matches
the independent source total, and every normalized binding survives SQL
storage exactly. Existing three affirmed review results are unchanged.

The source counterexample in game 822693 reconciles Harry Ford's five broad
batting observations to four official PAs; the inning-ending caught-stealing
interruption is excluded from statistical credit. A separate graph fixture
proves that preserving an interrupted turn does not add an official PA.
Negative checks cover changed player counts with unchanged team totals,
unknown results, mid-turn substitutions, missing unfiltered plays, extra
graph PAs/batters/result types, missing decisions and missing nonbatting roster
members. Schedule checks retain nonfinal games and refuse missing dates/games.

Focused checks: 10 source-admission, 4 schedule, 12 batting aggregation,
11 serving, 4 dashboard and 37 Node tests (78 total), plus PowerShell parsing
of the changed NiFi stage and the real-game Jena/SQL proof.

This is isolated developer evidence, not a live corpus promotion or a complete
selected-period score population. B1 verification now runs in NiFi's existing
source SHACL stage before promotion; proof artifacts survive raw cleanup.
Materialization imports only hash-bound proof provenance, while counts and
exposure come from RDF. Missing or stale proofs withhold qualification.

The separate [B2 proposal](../../../proposals/contact-play-continuation-membership/README.md)
documents a concrete contact-continuation mapping gap that prevents the first
complete Offensive Reach player population. It is not implemented here.

Reproduce this component proof with `sources/mlb-game/pipeline/batting-admission.py`
against the retained source/RDF pair, then
`tests/prove_pitch_review_serving.py --batting-admission <proof.json>` with
the same RDF and Jena arguments. Recurring production execution belongs to
NiFi, not this developer proof helper.
