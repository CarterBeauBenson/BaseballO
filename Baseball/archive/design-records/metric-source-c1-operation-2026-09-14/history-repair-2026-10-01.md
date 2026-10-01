# H2: targeted runner-history selection repair

**Superseded for activation by the [combined H3 repair](../../../sources/mlb-game/review/rml-selection-repair-2026-10-01.md).**
The three H2 patches below remain historical preparation records; do not apply
them separately or treat them as active changes. H3 includes their five games.

Prepared under the [accepted narrow repair scope](../metric-repair-scope-2026-09-30/README.md)
and [overlapping temporal-region decision](../metric-repair-scope-2026-09-30/answers.md).
The user requested this repair after the October 1 RML audit. This document
does not record approval of a semantic-freeze update. Runtime publication of
the context pin remains pending that explicit acceptance.

The [exact context patch](../../../sources/mlb-game/review/history-selection-repair-2026-10-01.patch)
repairs existing E1/C1 source selection without adding ontology terms,
properties, identity policies, review assertions or metric meanings:

- Account for pickoff/caught-stealing events through the existing independent
  movement and out reconciliation.
- Account for completed, consistent final home-run, hit-by-pitch and shift
  reviews. Keep pitch reviews and original-call reconstruction separate.
- Recognize the existing null strikeout bookkeeping record beside a supported
  safe wild-pitch movement after a completed first-base review. Do not invent
  a second running episode.
- Account for a completed pickoff review only when the participant, pickoff
  association, final narrative, movement and counters agree.
- Permit the diagnosed passed-ball/wild-pitch interval to overlap a subsequent
  pitch when its pitch association and the next ball/strike counter reconcile.
  All runner/out/base reconciliation still applies. No clock value is changed,
  and an arbitrary overlap or array position does not establish order.

The five diagnostic responses exactly match their originally promoted source
hashes. Their raw bytes are held outside Git; the fixture is a labeled derived
test projection, not an ingest source. NiFi will reacquire only these named
responses if necessary and require the same hashes before mapping a delta.

| Game | Histories before | Histories after | Remaining withheld half |
| --- | ---: | ---: | --- |
| 849842 | 18 | 19 | None |
| 849848 | 17 | 25 | None |
| 849843 | 16 | 23 | None |
| 849845 | 19 | 22 | None |
| 849849 | 28 | 29 | Ninth top: pinch-runner with no movement episode |

The prepared context recovers 20 histories while preserving every prior
lifetime identity and episode allocation. The ninth-inning zero-episode case
continues to use accepted Q7 isolation; its complete neighboring histories
remain selected. There is no fabricated movement or whole-half admission.

Validation: 28 focused tests passed, including missing/contradictory review,
participant, count, movement, association and temporal evidence. The original
five inputs also reconcile with the previous selected histories supplied as
the identity-preservation baseline. These are developer results, not claims
of RDF promotion or dashboard completion.

Runtime scope is the three existing personal-history maps for the 20 missing
histories. The worker preserves existing RDF, checks the addition through
source SHACL, refreshes affected evidence and the game query index, and emits
the ordinary promotion event for SQL. No whole-game replacement or rebuild.
Unrelated previously withheld products remain withheld.

The [execution patch](../../../sources/mlb-game/review/history-selection-execution-2026-10-01.patch)
contains the bounded five-game inventory, existing-worker changes, regression
fixture/tests and exact proof compatibility. It rejects all 15 tested changes
to source hashes, selected history keys and half-inning scope. The existing
compatibility regression passes: unrelated context definitions stay identical,
all six exact producer transitions resolve, and unknown fingerprints fail.
Neither this patch nor the context patch is active code while approval is pending.

The required publication update is limited to the context-builder hashes in
`governance/semantic-freeze.json` and exact retained-proof compatibility
records. The global freeze remains unratified. Previously checked outcomes
keep their provenance and are not relabeled as newly validated results.
The [prepared pin patch](../../../sources/mlb-game/review/history-selection-pin-2026-10-01.patch)
changes the context from
`48f1f0daa2cfde9b899a5dad6bcf68f9eb7bcb9a1189715f2e3a2c7e9e432d5d` to
`148afacfc4b5667c044b1e109d0c1386c358f0965421fa2e690fe462cb49b0c4`,
updates its containing set digest, and cites the existing accepted E1/C1 decision.
All three patches pass `git apply --check` together against `86a4711`.

## Independently completed queue repair

Commit `156cadb` preserves D1's independently recorded source identity through
later additive repairs. The formerly failed game 822789 was retried by NiFi
and completed on October 1 at 18:45 UTC: two histories and 13 triples added,
with its 36,977 existing triples preserved. This is a completed graph repair;
it does not assert that H2's five games have been repaired or SQL republished.
