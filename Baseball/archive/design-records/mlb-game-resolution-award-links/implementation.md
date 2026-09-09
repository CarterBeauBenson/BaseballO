# Implementation evidence ? 2026-09-08

The accepted decision was recorded before ontology, context, RML and SHACL
implementation. Git remains disabled.

Implemented the exact three accepted property declarations in BaseballO.ttl.
Added only those three IRIs to the explicit approved-local-property list;
the three frozen curation findings were preserved. Existing resolution,
runner, Base, award and game identities remain unchanged.

Three RML maps over three execution-context lists implement the links.
Source SHACL checks resolved-runner participation and provenance, safe
Base type and field context, and award type, PA/game context and destination.
The existing source lane owns all subsequent mapping, validation and promotion.

Focused checks passed:

- 8 resolution/award tests, including positive walk/HBP examples and negative
  unknown, duplicate, mixed-reason, overshoot, missing-chain and SHACL cases.
- 6 existing contact-play containment regression tests.
- Ontology curation: 272 classes, exactly 3 admitted object properties and
  the unchanged 3 frozen unresolved findings.
- Static RML: 349 triples maps, 102 logical sources, no referencing-object
  joins or undeclared classes; original fixture structural identities pass.
- Actual RMLMapper fixture: game 822693 PA 6 produces exactly 6 expected
  relation triples across the existing 2 runner resolutions. The isolated
  fixture writes no production graph or manifest.
- Generated Mermaid: 61 patterns, 125 Markdown artifacts.
- MLB-game runtime admission and accepted review artifact pins verified.

NiFi proof submitted asynchronously:

- Game: 566279.
- UTC submission: 2026-09-08T19:15:41.6743534Z.
- Proof Request processor: 5e89e2f4-01a0-1000-4b06-fcf9b197942f.
- Acknowledgement: RUN_ONCE, revision 3.
- Mapping SHA-256: f46ba5b939206833aa64bf2b03b0e42f287ae60a74b127a0fc2d443c4251f1cc.

Submission is not terminal proof or promotion evidence. The healthy run was
not polled. No historical corpus batch was released; that requires completed
current-hash proof evidence. Immediate-before state, continuity, operative
review identity and metric completeness remain unresolved.
