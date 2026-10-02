# F5/D2: repair the recorded foul and defensive selection failures

**Prepared for review; the protected context remains unchanged.**

The October 2 failure snapshot contains 15 foul additions and 14 defensive
additions. One defensive failure appeared after the previous 28-failure report.
These are failed repair jobs, not 29 games lacking all RDF.

This [patch](selection.patch) repairs existing source selection. It changes no
ontology term, object property, identity policy, RML triple map or SHACL shape.
It preserves the graph and uses the existing NiFi lanes to add missing facts.
The user has authorized narrow repairs; activation additionally needs acceptance
of the exact protected context pin below.

## Recorded causes and corrections

| Cases | Cause | Correction |
| --- | --- | --- |
| 4 foul games | Extra-inning placement was treated as an unexplained count change | Reuse C1's exact placement adjudication and boundary witness; require unchanged count, second base and zero outs |
| 2 foul games | Mound visits/timeouts overlapping a pitch were not recognized by H3's administrative overlap handling | Use the existing strict no-movement, no-out, no-scoring, unchanged-count check; remove the loose event-label fallback |
| 6 foul games | PR plus PH, a mid-turn PH, batting-order pitcher changes, or a name ending in `Jr.` failed parsing | Reuse the roster and Q4/Q5's actual pitch participants; reconcile each substitution independently and preserve counts |
| 2 foul games | A completed mixed tag/pitch-result review or reviewed foul tip was rejected | Recognize the explicit completed dispositions and final ordinary count; infer no original ruling, review subject or challenge eligibility |
| 1 foul game, 822861 | The retained response changed another pitch's end time | Already fixed in `47c6a48`: retain the promoted census's unrelated clocks while requiring exact identity/time/outcome agreement for every selected foul |
| 14 defensive games | A period inside `A.J. Ewing` or `J.P. Crawford` was read as the end of a sentence | Match the complete, uniquely rostered name and retain the existing putout/assist evidence requirements |

The same punctuation repair covers the named final catcher in the already
accepted compact groundout pattern. It does not infer a catch, throw or tag
from an isolated statistical credit. Catch identity and its Fielding Attempt
supertype remain the same particular. No precedence is added.

## Competency questions and field inventory

1. Should an explicitly reconciled placement or substitution suppress an
   independently recorded second-strike foul? No; the selected pitch still
   needs its actual participants, final call, counter increment and times.
2. Should overlapping administrative intervals imply that actual pitches
   overlap? No; retain H3's distinction and still reject pitch-to-pitch overlap.
3. Does a completed mixed review erase an earlier final foul? No; reconcile
   every review disposition and keep unresolved reviews excluded.
4. Does punctuation in a uniquely rostered name invalidate a named catch with
   matching putout evidence? No; parse the complete name.

All inputs are already owned by the MLB game lane:

| Field family | Selection inventory |
| --- | --- |
| Event kind, call, counters, movement, review flags and clocks | Existing authoritative fields; repair coverage only |
| Roster IDs, pitcher list, replaced player, batting position and names | Existing identity/join evidence; no new identity rule |
| Placement/boundary witnesses and Q4/Q5 pitch participation | Existing deterministically derived context; reuse it |
| Final review descriptions/dispositions and defensive credits | Existing authoritative fields; retain corroboration requirements |
| New endpoint, ontology vocabulary or predicate | None |

The [existing world-side diagrams](source-independent-mermaid.md) are reproduced
for reference. The accepted M3/M4, D1, C1, Q4/Q5 and H3 patterns remain the
authority. The repaired administrative selectors do not map new administrative
acts or assign a Fielder Role to a DH.

## Focused evidence

[Evidence](evidence.json) pins every input, selected foul and retained failed
defensive union. [The check](check.py) exercises the candidate in a disposable
copy and leaves live RDF and the active context untouched.

- All 17 selected strikes in the 15 foul cases pass the existing repair
  worker's exact source-identity, clock and outcome comparison. F5 newly
  selects 14 of them; 822861's three were already selected by the active context.
- The unchanged five foul maps produce precisely 14 triples for the selected
  822794 strike, with no unrelated subject.
- The original closed-census SHACL query returns no unexpected defensive acts
  or contact plays for any of the 14 retained failed unions. Every expected act
  is present. This is a check of the recorded failure, not a claim of complete
  defensive population or a replacement for NiFi's full SHACL execution.
- Contradictory placement witnesses, participants, counters, reviews, movement,
  pitch overlap, names and credits remain excluded.
- Existing focused C3, counted-foul and defensive selector checks pass. One
  stale fixture count was corrected from 59 to 65: both the already active
  context and this candidate select those same 65 acts.

The check requires the exact pre-implementation context and retained evidence.
After NiFi promotes a repair it may retire transient source bytes, so this
pre-implementation check is not a permanent production gate.

```powershell
python -B Baseball/proposals/mlb-game-foul-defense-selection-repair/check.py
```

## Exact activation scope

Accept **F5/D2 and its scoped context-pin update**:

- Previous context SHA-256:
  `86f6f6ad62eec5795b6bc464a0040c210e8be4bb83e94e65b765b943eb3cc00e`.
- Candidate context SHA-256:
  `73bd4ef20e96c8b369e7334572d36240e0f73db912f67bd7cf39c22dc202c5ec`.

Record and push acceptance before applying this patch. Advance only this
context pin, its containing protected-set digest, runtime/inventory references
and the exact retained-proof compatibility needed by these changes. Unrelated
protected artifacts and the global freeze disposition remain unchanged.

Preserve old proof producers and outcomes. Families whose selection expands
may reuse a previously successful, stricter proof only when its dependencies
and source/graph identities match. A withheld or failed proof is not a new
successful proof. Unchanged families retain their existing evidence. A changed
fingerprint is not grounds to regenerate RDF.

Then let the existing foul and defensive NiFi lanes retry their recorded cases,
validate base plus addition with their existing source SHACL, promote additive
triples, refresh affected derived products and retire successful transient
inputs. Other lanes keep their existing work scopes. This authorizes neither
whole-game replacement, a corpus rebuild nor a new source-acquisition project.
Successful promotion and SQL population remain runtime outcomes to report,
separately from these offline checks.
