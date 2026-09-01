# Baseball season segments and transaction periods

Status: **accepted 2026-08-31**

This package proposes the exact taxonomy needed to distinguish game-containing
Season Phase Processes, no-game-required Season Segment Processes, and
institutionally designated transaction-calendar Temporal Intervals. It
corrects one important boundary exposed by the official calendar: an
International Signing Period and parts of open free agency can extend through
the playing season, so they must not be asserted wholesale as intervals within
the Temporal Interval occupied by the Offseason.

No object property or data property is proposed. The package is archived as an
accepted design record; bounded implementation is authorized by the separate
MLB-game classification and geometry implementation record.

The reusable nominal category ICEs are ontology individuals. Annual or
method-era MLB Reference Systems are source evidence and must be minted as
versioned individuals by the owning mapping; this proposal does not install a
timeless MLB calendar reference-system individual.
