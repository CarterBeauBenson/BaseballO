# Baserunning-origin implementation evidence

Implemented 2026-09-08 after the named acceptance in [review.json](review.json).

The existing MLB-game context builder selects unambiguous supported origins.
Five small additions to the existing RML reuse act, resolution, Base and record
identities and supply explicit Base Code Identifiers. Source SHACL constrains
the linked act, runner, PA, field, source record and Base code. No separate
mapping or dataset reset was introduced.

## Focused developer evidence

- Six baserunning-origin context/SHACL tests passed, including PA 12 and PA 64
  of game 824315, missing and conflicting evidence, and malformed graph links.
- Eight resolution/award tests passed with the Base Code Identifier contract.
- Three attribution-evidence SPARQL regressions passed, including origin counts.
- The static mapping check passed for game 824315: 354 TriplesMaps, 103 logical
  sources, 77 plate appearances, 360 pitches and 114 runner rows. Existing
  structural identities handle the two reported legacy composite collisions.
- An isolated execution of seven actual RML fragments with RMLMapper 8.1.0
  emitted the expected 21 triples for PA 12. Explicit code joins identify the
  steal's 1B origin and 2B destination, and the later single's 2B origin and 3B
  destination. The batter's null origin produces no origin assertion. RDF 1.1
  string values were checked independently of serialization abbreviation.
- Ontology curation passed with 272 classes, four approved object properties
  and the same three frozen findings. Accepted/active review records and the
  scoped MLB-game runtime admission passed their focused checks.
- Generated Mermaid inventory: 62 patterns, 354 TriplesMaps, 127 Markdown files.

Mapping SHA-256:
`76b433db32acb7e8d69d7aeaabd0b6faa4e1973919c14b99d49047880065e471`.
The checked-in source fixture retains SHA-256
`5fcc75d37a20a516d312b3bfb3d5cefb4371ebafa639851ff16173d9b1a6607c`.

## Asynchronous one-game proof

NiFi accepted a `RUN_ONCE` submission for game **824315** at
`2026-09-08T19:48:06.0432969Z` through the existing MLB-game Proof Request
processor `5e89e2f4-01a0-1000-4b06-fcf9b197942f`, response revision **5**.
Request: `gamePk=824315`, `materializeMode=immediate`,
`scheduleEvidencePath=none`.

This records submission only. Whole-game RML, source SHACL, promotion and
downstream proof results remain pending NiFi evidence; no healthy-run polling
was performed. The acquisition schedule and unrelated source lanes are unchanged.

## Remaining metric boundary

This proves an origin for a particular supported act. It does not establish
unchanged runners, continuity across multiple acts, operative replay/out
identity, or complete batter attribution. TFS and PAQ-2 scoring and serving
remain gated by those decisions and the required graph proofs.
