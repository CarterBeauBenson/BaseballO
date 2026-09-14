# C1 runner histories and real Run Construction Depth

The explicitly accepted [E1/C1 decision](../../../archive/design-records/metric-source-c1-operation-2026-09-14/review.json)
was published in commit `3226ec5` before this implementation. No ontology class
or object property was added. The existing MLB mapping emits the accepted
personal process, its runner, half-inning, own interval and episode membership.

## Verified result

The unchanged real game 566279 (April 1, 2019) produced 18 reconciled personal
histories and exactly 34 episode memberships. The full authoritative SHACL
profile conformed with zero violations over 31,717 triples. Serialization
matched the independently selected source membership exactly.

Run Construction Depth is available for **nine complete individual scoring
histories out of 13 observed runs**. Wilmer Flores (527038) has depth **3/1**:
the three distinct state-changing episodes in his admitted scoring history.
The canonical evidence query ran against the real RML graph using Jena; SQL
materialization and selection returned the exact same serialized metric.

- [RML manifest](rml-manifest.json): source/revision hashes, history anchors,
  event bounds, complete nested episode inventory, withheld-half reasons,
  mapping fingerprint and validated SHACL status.
- [Exact query/SQL result](run-depth-sql-proof.json): all nine individual results,
  their graph evidence, fractions and coverage; `sqlExactMatch: true`.
- [Mobile presentation](run-depth-mobile.png): real proof response supplied as
  an HTTP fixture to check rendering. This is not evidence of live promotion.

Focused checks passed: 21 source/C1 tests, 21 serving/source-scope tests,
19 Node tests, and headless browser checks for run cards, mobile overflow,
stale requests/downloads, all 20 explanations and the existing live TFS case.
The mapping proof was repeated after fixing nested manifest serialization;
its saved history and episode arrays were checked as structured objects.

## Remaining limits

Only fully reconciled three-out half-innings are selected in this release.
The proof withholds top 2 and top 3 for missing stable movement anchors,
and bottom 5 and top 7 for unsupported offensive-substitution effects.
Games with unresolved reviews, ambiguous event times, unsupported entry or
game-ending boundaries, incompatible movement chains or source inconsistencies
withhold the affected histories. A direct batter out does not fabricate a
personal baserunning process. A stranded runner receives no invented out.

The selected population result remains unavailable: nine supported runs are
not a replacement population for all 13. C2 boundary queries, complete PA
attribution and independent running, complete game/season eligibility, pitch
count-state evidence and defensive/review populations still require work.
Full operation of all 20 metrics is not complete.

NiFi owns promotion, materialization, retry and subsequent refresh. Local
proof artifacts are isolated from NiFi's active manifests. A submission receipt,
when present here, establishes submission only; it does not establish success.

## Focused reproduction

Run `scripts/pipeline/run-rml.ps1` with `-InputJson data/raw/game-566279.json`,
an isolated `-DeveloperEvidenceRoot`, and `-ShaclEngine jena`. Then run
`tests/prove_run_construction.py --rdf <proof-rdf> --java <java.exe>
--jena-classpath <fuseki-server.jar> --output <result.json>`.
The browser check accepts `-RunDepthProof <result.json>` for this separately
identified real-data presentation fixture. Routine runs belong in NiFi.
