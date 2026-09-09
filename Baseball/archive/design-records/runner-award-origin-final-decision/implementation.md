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
