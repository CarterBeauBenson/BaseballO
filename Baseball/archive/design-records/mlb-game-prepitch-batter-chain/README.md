# F7: counted foul after a pre-pitch batter replacement chain

**Accepted by Carter Beau Benson on October 3, 2026. Acceptance is recorded before activation.**

Game **823312**, PA **73**, names Gavin Sheets replacing Miguel Andujar, a
mound visit and pitching change, then Ramon Laureano replacing Sheets. Every
substitution precedes the first pitch at 0-0 with two outs. All three pitches
belong to Laureano. The second pitch is the missing counted foul
`b42bce27-908d-3f43-9387-3eb07f1ef7f3`.

The [exact patch](selection.patch) extends the existing pre-pitch PH selection
to an explicitly linked chain. It requires rostered distinct participants,
matching incoming/outgoing identities, unchanged 0-0 count and outs, no pitch,
runner movement, scoring, out or review within the prefix, and final-batter
identity on every actual pitch. Only mound visits and pitching changes may
intervene. A later PH, broken chain, participant mismatch, count change or
runner movement remains excluded. Intermediate substitutes receive no pitch
or batting contribution merely from being named in the chain.

## Competency question and field selection

Can an explicitly reconciled PH chain completed before the first pitch leave
a later ordinary foul eligible for the existing second-strike pattern?
Proposed answer: **yes**, under the conditions above.

| Existing MLB field | Use |
| --- | --- |
| Replacement identities, roster and final matchup | Existing identity/join evidence |
| Pitch flag, count, outs and event flags | Existing prefix reconciliation |
| Runner rows and review details | Existing contradictory-evidence exclusions |
| Actual pitch participants, play ID, clocks and foul call | Existing counted-foul requirements |
| New sources, fields or ontology vocabulary | None |

The [diagram](source-independent-mermaid.md) is the accepted world-side strike
pattern. This adds no ontology classes, object properties or new mapping
pattern. The same five foul maps and source SHACL remain in use. The
[check](check.py) tests the exact named strike and contradictory variants in a
disposable candidate module, without running RML or modifying live RDF.

## Activation scope

The user approved **F7 and its scoped context-pin update** by replying
"approve and fix the next problems" to the explicit pending F7 request. Publish
this acceptance before activation. Apply only the prepared selector patch and its
corresponding freeze, inventory and exact proof-compatibility references.
Preserve original proof hashes and statuses; no stale rejection becomes an
admission. NiFi may add only the selected missing foul and its accepted
dependencies. No whole-game replacement or corpus rebuild is included.

Previous context SHA-256: `0b6b0fdf7eb4cfef8760ac68e5d556b3214ac6bb6ae15fd0ad38041a0368d9a8`.

Candidate context SHA-256: `6c4829ed57028bc635e71487c7489f5c3473e427bbcc1d7ddafb0c2ab3be3e96`.
