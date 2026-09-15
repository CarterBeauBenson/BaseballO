# Implementation status after the first accepted completion pass

The [user's decisions](user-decision.md) were published in `b4d4f88` before
implementation. B2's exact engineering paths were subsequently published in
`d95d537`. This status is engineering evidence, not additional user approval.

| Question | Current implementation |
| --- | --- |
| 1 — B2 | Implemented through existing RML context and source-owned SHACL. Real one-record and whole-game proofs pass; six resolutions, three personal histories, bounded Offensive Reach 2. NiFi owns the validation before promotion. |
| 2 — Shared outs | Not accepted. The hit-and-run counterexample remains open; no equal split was installed. A confirmed hit-and-run's runner-out damage needs the user's allocation decision. |
| 3 — Catcher interference | Exclusion policy is executable in the trajectory calculator and exposed by the canonical single-source evidence query. A recognized official PA remains eligible; awarded progress is zero. The complete live PA/Empty Game adapter is still unfinished. |
| 4 — Substituted Batter Acts | Identity decision accepted and recorded. Source-specific segmentation, RML links, SHACL and full official-PA reconciliation beyond B1 remain unfinished. |
| 5 — Non-pitch awards | Meaning and zero-pitch treatment accepted and recorded. Real source fixtures are identified below. Automatic-award RML, conformance and complete ordered count extraction remain unfinished. |
| 6 — Defensive acts | Evidence/identity criterion accepted and recorded. Full particular-act extraction and source/RDF conformance remain unfinished; credits are not a complete act census. |
| 7 — Review eligibility | Decision-time eligibility policy recorded. UI qualifies and ranks mechanisms separately. Complete historical challenge-availability reconstruction and eligible-decision production remain unfinished. |
| 8 — Walk-off | Evaluation policy recorded. C1 source admission still needs the supported final-game boundary extension; no new fictitious outs or erosion were added. |
| 9 — Minimums | Exact table implemented and tested, including zero-PA nonbatting participants, rare-event floors, upward rounding and separate review mechanisms. Contribution Path Diversity was omitted from the table; the follow-up asks whether either batting or independent-running qualification suffices. |

The dashboard is not fully populated. Numerical examples and bounded proofs
do not constitute complete player or season-reference populations. No new
runtime corpus-refresh request or monitoring loop was started in this pass;
the existing NiFi lane and asynchronous work remain enabled.

## Non-pitch source fixtures for the accepted next mapping

These are existing checked-in source fields, not a missing external source or
authorization for a duplicate acquisition lane:

| Immutable source | Particular record | Evidence |
| --- | --- | --- |
| `data/raw/samples/2026-07-18/823116.json` | PA 76, event 3, `c5576ea2-9665-4006-8875-3cba5fab0284` | `isPitch=false`, `type=no_pitch`, code `VP`, explicit `pitcher_pitch_timer` violation, post-count one ball and zero strikes. |
| `data/raw/samples/2026-07-18/824088.json` | PA 33, event 0, `f213963d-0938-4a7c-84f1-df71eaaa1b6b` | `isPitch=false`, `type=no_pitch`, code `AC`, explicit `batter_pitch_timer` violation, post-count zero balls and one strike. |
| `data/raw/samples/2026-07-16/823440.json` | PA 33, events 0–3 | Four `VB` no-pitch intentional-walk counter records. Do not silently equate provider counter rows with four separately evidenced umpire performances. |

Clock violations can yield automatic balls or strikes without a pitch.
[MLB's pitch-timer explanation](https://www.mlb.com/glossary/rules/pitch-timer).
Field identity, operative count increments, corrections and temporal scope
must be reconciled before these fixtures release a complete count history.
