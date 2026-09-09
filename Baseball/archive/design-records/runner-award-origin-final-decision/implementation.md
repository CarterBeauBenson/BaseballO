# Final award and origin implementation

Decision commit `7faed3e` was pushed to `origin/dev` before protected changes.
This implementation follows the user's A-F final decision, superseding the
interim directive and shared stasis-boundary requirements.

## Implemented

- Removed BaseAwardDirectiveICE from the ontology and overlay. Source SHACL
  rejects event-specific instances of that withdrawn class.
- Supported Walk/HBP results cause particular Baserunning Acts. Applicable
  Baseball Rule individuals require those same acts, with distinct batter-walk,
  batter-HBP and existing-runner force provisions and edition/code identifiers.
- Existing forced runners require positive r_adv_force evidence, exact next-base
  completion and matching event/runner/destination evidence. Mixed same-runner
  segments, overshoots, unrelated moves and reviewed/ambiguous awards are withheld.
- Added BaserunningSegmentOriginDesignation: about the act, designates the Base,
  and part of the source row record. movement.start supplies the segment origin;
  originBase does not override it, including when the two fields differ.
- Removed all stasis-ending/act-start equality requirements from origin queries.
  No stasis, physical location or continuity is inferred from a movement start.
- Batter metric HOME=0 is derived from PA batter identity. The TFS calculation
  accepts this initial state when runner start is null. Existing-runner origin
  resolution prefers the designation, then a positively supported PA-start
  fallback, and otherwise reports unavailable. Conflicts never become zero.
- Updated source RML/SHACL, evidence queries, origin policy, gap register,
  source documentation and generated Mermaid inventory. No new object or data
  properties and no RDF index predicates were introduced.

## Focused evidence

67 tests passed: 11 structural/source SHACL, 9 final-decision source tests,
9 movement-query tests, 3 attribution-audit tests, 4 metric-origin tests,
23 existing metric calculations and 8 serving integration tests.

The bases-loaded walk fixture (game 823016 PA40) passed the actual RMLMapper
8.1.0 transformation and Jena 6.1.0 full source SHACL profile: 1,930 triples,
zero violations. It has four causal/required advances and three segment origin
designations. The batter acquires metric HOME=0 without an RDF origin Base.

Full game 823016 also passed: 33,648 triples, 118 episodes, 38 segment origin
designations, 10 award causal links and 10 normative requirements. It has zero
BaseAwardDirectiveICE instances. All 59 stases retain the PA-start subclass;
no additional stasis is fabricated by origin mapping. The actual evidence query
returns the loaded walk's four metric origins 0, 1, 2 and 3, all with the same
award source. Raw source bytes are unchanged.

Static mapping checks passed (361 maps, 103 logical sources, zero undeclared
classes). Ontology curation passed with 275 classes, zero local properties and
the same three unrelated frozen findings. The definition was expanded to the
repository's required Aristotelian sentence form without changing its meaning.
Generated inventory: 62 patterns, 127 Markdown files.

See implementation-evidence.json for exact graph bindings, hashes and SHACL
results. No repository-wide aggregate gate was manually run.

## Remaining coverage, distinct from the resolved modeling decisions

The two named modeling gaps are resolved. The initial source subset admits
unreviewed operative awards and the verified 2019/2026 rule editions. Other
editions and reviewed PAs need source coverage; source rows do not manufacture
positive no-intervening-movement evidence for the conditional PA-start fallback.
Complete attributed trajectories, unchanged-runner state and remaining suite
eligibility gates are independent prerequisites, retained in the gap register.

This is a local developer proof. No existing promoted graphs were rewritten,
no raw source was edited, and no NiFi schedule or topology changed. Normal
NiFi mapping/validation/promotion supplies corrected graphs and serving products;
repository-wide validation remains its asynchronous observer gate.

## Subsequent NiFi proof submission

On 2026-09-09 at 13:45:53 UTC, NiFi accepted one `RUN_ONCE` request for game
566279 using implementation commit `603730ce27b72b0380c483496d7206ade63ca382`.
The existing MLB Game Proof Request processor returned revision 2. The request
selects immediate serving materialization and no schedule evidence file.
This MLB game exercises the verified 2019 rule edition and forced walk advances.
The [submission receipt](nifi-proof-submission.json) records the exact request,
processor identity, mapping hash and source SHACL hash.

Fuseki and NiFi were initially stopped and were started with the repository's
existing startup scripts and configured storage. NiFi took about 100 seconds
to become ready, exceeding the initial 45-second readiness check. The required
source processors were valid and running before submission; daily acquisition
was also running. No flow reprovisioning or schedule change was needed.

This is a submission receipt, not a successful graph-pair or serving-promotion
report. NiFi owns those gates and their evidence, retries and quarantine. No
healthy-run polling, historical corpus request, or manual transformation was
performed. Complete trajectory scoring and percentile release remain gated by
the unresolved prerequisites in the metric gap register.

## Promoted graph and metric evidence integration

The user's subsequent request to continue prompted a result inspection. NiFi
run `3e3447623d554c428eaba68dd94b0f87` passed source SHACL with zero violations
and promoted game 566279 at 13:46:40 UTC on 2026-09-09: 31,593 authoritative
triples and 8,254 query-index triples. The promoted-graph event was emitted.
The [stage observation](nifi-proof-observation.json) retains the completed
stage results and their hashes. At inspection, SQL materialization was running
with a request queued; serving completion is not claimed.

Suite 2.0.2 now carries the accepted movement-query bindings through its
existing SQL evidence table and live API reducer. It exposes observed movement
coverage in metric results and the metrics page. This is an engineering
projection over accepted graph paths; ontology, identity, RML, SHACL, scoring
meaning and semantic admissions are unchanged. Unknown and conflicting values
remain distinct, and observations do not certify whole-trajectory completeness.

Eleven focused serving tests passed, covering RDF-to-SQL preservation,
idempotence, graph isolation, conflicting and missing origins, batter HOME=0,
exact result equality, and unchanged unavailable-score behavior. The browser
script passed Node's syntax check.

The [live query evidence](metric-serving-evidence.json) records 925 suite rows,
including 113 movement pairs. All 113 have one bound metric-origin value;
34 have segment-origin designations, 46 have safe-destination bindings, 89
have contact-play links and 8 have causal award plus rule-requirement links.
The composed query's movement rows exactly equal the canonical movement query
over this graph. Restricting the composed dataset with `FROM NAMED` avoids
unrelated-graph scanning: the final scoped query completed in 0.304 seconds.
The initial VALUES-only live check failed to return complete JSON; that
failure is not counted as a passed check.

TFS remains unavailable for attribution, boundary state, completeness,
operative outs and path identity. An origin value on every observed movement
does not account for unchanged runners or prove every relevant consequence.
NiFi's existing materialization stage will consume the new version; no manual
corpus build or additional proof request was made for this serving update.
