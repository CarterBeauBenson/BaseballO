# H2: targeted runner-history selection repair

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

The required publication update is limited to the context-builder hashes in
`governance/semantic-freeze.json` and exact retained-proof compatibility
records. The global freeze remains unratified. Previously checked outcomes
keep their provenance and are not relabeled as newly validated results.
