# Full metric operation: source-admission decision

Status: **draft; not accepted**. Prepared 2026-09-14 after the user clarified
that the deliverable is full operation of all metrics. Examples, formula
tests, unavailable HTTP responses, and bounded award results do not meet that
deliverable.

## Required deliverable

All 20 metrics must have real admitted inputs, the applicable complete
population, exact calculations (except logarithmic entropy), NiFi-owned
refresh and correction handling, validated RDF-to-SQL equivalence, and usable
player/play/game/season presentations at their defined grains. A selected
display range must not replace the accepted PAQ season reference population.
Independent runner advancement, damage and net must also be available.

Known inapplicability, missing evidence, empty denominators and genuine zero
scores remain distinct. Full operation does not mean inventing a score for
an inapplicable or evidentially unresolved case.

The accepted metric meanings and C1/C2 representation are not reopened here.
No object property, class, axiom or alternative runner identity is proposed.

## E1 — What establishes exhaustive source history?

**Decision requested:** may a final MLB game-feed revision serve as the
exhaustive official scorekeeping history for runner transitions and operative
outcomes, provided the reconciliation conditions below all pass? Or must
completeness be corroborated event by event against independent evidence?

This is a source-authority assumption, not a request to approve Python files
or SQL plumbing. Agreement would not establish that any existing game passes.
Reconciliation within one provider cannot establish that the provider omitted
no event; accepting its exhaustive scope is the proposition requiring review.

Proposed reconciliation conditions:

1. Bind the input hash, game identity, provider revision and final game status.
   Retain that identity with all conformance, graph and calculation products.
2. Independently enumerate the unfiltered source before mapping. Reconcile PA
   membership against `playsByInning`; reconcile scoring membership against
   `scoringPlays` and inning/team run totals. Neither final status nor matching
   totals alone establishes complete history.
3. Account for every event and runner movement in each proposed lifetime.
   Resolve each movement's `playIndex` to exactly one event. Preserve explicit
   unknown or unsupported effects instead of dropping those records.
4. Reconcile substitution, automatic-runner, out, score, review/correction,
   half-inning and game-ending effects. Unsupported effects block the affected
   lifetime and its dependent population; they do not disappear from scope.
5. Require positive entry and termination anchors for each C1 lifetime and
   supported time extents. Source array order does not become strict BFO
   precedence. Simultaneous or ambiguous boundaries remain unresolved.
6. Reconcile occupied-base observations, distinct outs and scoring outcomes.
   Pitch-level count fields keep their own scope; a terminal pitch's out count
   is not automatically the post-consequence count. Missing post-base fields
   alone never establish that the bases are empty.
7. Under the accepted C2 rule, carry a positive safe observation only across
   the accounted-for intervening history and a supported evaluation boundary.
   Preserve stranded participants before the inning reset. Do not manufacture
   a new safe adjudication, location assertion or stasis.
8. Separately reconcile source-to-graph coverage against that input inventory
   after RML and source SHACL. Keep acquisition completeness, mapping coverage
   and analytical eligibility as separate products.
9. For population metrics, reconcile eligible games to the owning schedule
   evidence through the cutoff and every applicable PA/consequence to its
   admitted graph inputs. A withheld eligible member withholds its reference
   population; a convenient scored subset is not a replacement population.

The existing source lane owns this work. The lifecycle stays
`API -> RML -> SHACL -> Fuseki -> queries -> SQL -> UI`. NiFi runs the repeatable
checks, retains manifests and handles retries. Corrections invalidate affected
derived products without rewriting raw checked-in evidence. Engineering
details after a source-authority decision do not require further file-by-file
approval. Any separately needed ontology or field-meaning decision still does.

## Concrete evidence inspected

Source: `data/raw/samples/2026-08-23/824315.json`, unchanged SHA-256
`5fcc75d37a20a516d312b3bfb3d5cefb4371ebafa639851ff16173d9b1a6607c`.
The revision reports `20260823_222717` and final status.

| Exact source location | Observation | Operational consequence |
| --- | --- | --- |
| `liveData.plays.allPlays[34..35]` | Runner 800050 is positively reported on third after both PAs. PA 35 includes a batter timeout and eight pitches, but only the batter's movement row. | Source membership, non-pitch effects and boundary reconciliation are needed before C2 projection. Matching endpoints alone do not establish continuity. |
| `liveData.plays.allPlays[15..16]` | PA 15 reports two runners on base. PA 16 has a third-out batter movement and no post-base fields. | Preserve the two candidate stranded runners pending complete-history admission; omission alone cannot decide their fate. |
| PA 35 terminal pitch `count.outs` and batter `movement.outNumber` | The values are 1 and 2, respectively. | The pitch count and completed consequence have different scopes. A generic “end outs” read would be wrong. |
| `liveData.plays.allPlays[43]` | Double-play description plus runner assist/putout credits; the event array has two pitches and a pickoff event. | These records do not enumerate the complete defensive field/throw/catch/tag sequence. |

## Field selection inventory

These fields are already in the owning MLB feed; an omitted mapping is coverage
debt, not permission to duplicate the assertion through another provider.

| Field/product | Selection | Scope or unresolved issue |
| --- | --- | --- |
| Game ID, PA index, inning/half, runner IDs, event indexes/play IDs | Identity/join-only | Reuse accepted identities; indexes alone do not prove temporal precedence. |
| Revision, final state, `playsByInning`, `scoringPlays`, linescore totals | Already supplied | Mechanical reconciliation inputs; exhaustive-history authority is E1. |
| Runner movement origins, destinations, out/scoring flags, credits | Already supplied | Reuse admitted meanings; credits do not enumerate all defensive acts. |
| Post-base observations | Already supplied | Positive observations only; C2 needs complete intervening history. |
| Pitch/non-pitch flag, count fields, timestamps | Already supplied | Exact grain, operative corrections and ordering require supported mapping contracts. |
| Substitution and review details | Already supplied where present; unresolved coverage | Every relevant effect must be accounted for; unsupported cases remain blocked. |
| Full runner lifetime and boundary projection | Deterministically derivable only after prerequisites pass | Accepted C1/C2; no new relation or source-record surrogate. |
| Complete intentional defensive sequence | Unresolved | Not supplied by the inspected credit/event arrays. |
| All review-eligible decisions, including never-reviewed decisions | Unresolved | Outcome-category eligibility and complete membership need evidence. |

## E2 — Additional evidence for the full suite

E1 cannot make the defensive sequence or review-eligible decision census appear
in the current feed. Full Defensive Resolution Depth requires the complete
intentional act sequence; Defender Breadth and Role Realization Breadth also
need adequate agent/realization coverage. PAQ-2.1 inherits its defensive inputs.
Review Dependence needs eligible never-reviewed decisions in its denominator,
with traditional replay and ball/strike challenges separated.

The next source investigation must establish whether free accessible structured
evidence supplies those exact inputs. If it does not, a separately reviewed
video-annotation source is a possible fallback; it is **not authorized or
implemented by this document**. Credit lists, a model's guessed actions and
synthetic examples are not substitutes for that evidence. No new source module
or NiFi group is being pre-created.

MLB describes [Statcast](https://www.mlb.com/glossary/statcast) as tracking
technology. That does not establish public access to every defensive act.
Its [replay database](https://baseballsavant.mlb.com/replay) supplies reviewed
plays; it cannot alone enumerate eligible decisions that were never reviewed.
These are investigation leads, not source admission or a promise of coverage.

## Implementation sequence and honest completion

After E1 is resolved, implement and prove its source reconciliation against
the real cases above, followed by the accepted C1/C2 source mapping, source
SHACL and graph-derived contribution/boundary queries. Then implement the
complete TFS and independent-running adapters, game/player aggregates,
run-construction metrics, population reconciliation and PAQ comparisons.
Pitch and defensive/review evidence remain separately gated where their
necessary source contracts are unresolved. E1 does not approve those contracts.

Only real end-to-end results with their applicable complete populations count
as operational completion. Until all required work is done, report the overall
task as incomplete, identify the actual blocked dependency, and keep working
on authorized independent components. Do not substitute more examples or UI
polish for operational implementation.
