# Mappings

- [`direct/`](direct/) is the active RML implementation. It reads untouched MLB `feed/live` JSON.
- [`policies/`](policies/) contains the approved modeling and IRI rules that govern the mapping.

The former enriched Stage 1 prototype is retained under [`../archive/stage1-preprocessing-prototype/`](../archive/stage1-preprocessing-prototype/) for history only. It is not part of the active pipeline.

The current direct mapping contains 277 triples maps across 77 logical sources
and uses no referencing-object-map joins. It produces 28,701 authoritative
triples for the original fixture and 231,670 across the checked-in eight-game
2026-08-03 corpus. Pitch records retain MLB's final call code. Replay mapping
now creates distinct on-field judgments, challenges, replay-review acts,
reviewed and replay decision ICEs, review-result ICEs, and source records. It
classifies the eight accepted ball/strike and out/safe transitions and links a
player challenger only when the narrative name resolves uniquely to a rostered
player, all without changing the untouched raw JSON. Intentional walks use the full walk-process pattern;
source-limited terminal pickoff and caught-stealing outcomes remain explicit
generic terminal results instead of unsupported performer-specific acts.
