# Mappings

- [`direct/`](direct/) is the active RML implementation. It reads untouched MLB `feed/live` JSON.
- [`policies/`](policies/) contains the approved modeling and IRI rules that govern the mapping.

The former enriched Stage 1 prototype is retained under [`../archive/stage1-preprocessing-prototype/`](../archive/stage1-preprocessing-prototype/) for history only. It is not part of the active pipeline.

The current direct mapping contains 249 triples maps across 58 logical sources
and uses no referencing-object-map joins. It produces 28,701 authoritative
triples for the original fixture and 231,018 across the checked-in eight-game
2026-08-03 corpus. Pitch records retain MLB's final call code, and replay event
records retain review type, disposition, narrative, and final-result links
without changing the untouched raw JSON. Intentional walks use the full walk-process pattern;
source-limited terminal pickoff and caught-stealing outcomes remain explicit
generic terminal results instead of unsupported performer-specific acts.
