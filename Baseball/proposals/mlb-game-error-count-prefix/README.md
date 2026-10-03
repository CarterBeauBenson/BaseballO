# F6: counted foul after an independent error advance

**Draft; the active context and its protected pin remain unchanged.**

Game **823172**, plate appearance 20, records a no-pitch event followed by an
interference error. Ivan Herrera advances from first to second. The batter's
count remains one ball and no strikes; later pitches reach three balls and one
strike before the selected foul adds the second strike. The missing strike is
`67aeb1a0-e793-3313-b02d-4132d7a338a5`.

The proposed [patch](selection.patch) extends the existing reconciled-running
prefix selector to this error case. It requires one identified runner with a
matching error movement and forward, safe base advance; unchanged balls and
strikes; reconciled outs; an exact preceding action link; no pitch/substitution
or unresolved review. Existing pitch identity, participants, final call, count
increment and timestamp checks remain in force.

This selects the existing foul-strike pattern. It gives the hitter no credit
for the runner's error advance, adds no new error adjudication, creates no
ontology terms or object properties, and changes no history identity. The
existing five foul maps and source SHACL remain unchanged. NiFi may add only
the selected missing facts and their existing dependencies.

## Competency question and field selection

Should an independently reconciled runner error with an unchanged batting
count prevent a later ordinary foul from becoming the second strike? Proposed
answer: **no**, when the requirements above all hold.

| Existing MLB field | Use |
| --- | --- |
| Event type, pitch flag, action link and runner identity | Existing selection/join evidence |
| Runner movement, out number and scoring flag | Existing runner-pattern evidence; no new running assertion |
| Ball, strike and out counters | Deterministically reconciled selection evidence |
| Foul call, play ID, participants and clocks | Existing counted-foul mapping requirements |
| New endpoints, fields or ontology vocabulary | None |

The [existing world-side diagram](source-independent-mermaid.md) shows the
accepted strike pattern. [Evidence](evidence.json) binds the exact retained
response and missing-class repair request. The [focused check](check.py) runs
the candidate only in a disposable module, including rejection of contradictory
counts, runners, movement, outs, review, action links and event kinds.

## Activation scope

Approval must name **F6 and its scoped context-pin update**. Record and publish
that decision before activation. Change only the prepared context patch and
its corresponding freeze, runtime/inventory references and exact proof
compatibility. Preserve original proof hashes and outcomes; no stale or
withheld proof becomes an admission merely because a fingerprint changed.

Previous context SHA-256:
`73bd4ef20e96c8b369e7334572d36240e0f73db912f67bd7cf39c22dc202c5ec`.

Candidate context SHA-256:
`0b6b0fdf7eb4cfef8760ac68e5d556b3214ac6bb6ae15fd0ad38041a0368d9a8`.

No whole-game replacement or corpus rebuild is authorized by this package.
