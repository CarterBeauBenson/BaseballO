# T1 timestamp isolation proof - September 17, 2026

The user explicitly approved T1. Decision commit `bfb874f` was pushed before
implementation. The repair changes selection of existing measurements and
admissions; it adds no ontology terms or object properties.

All five retained problem games passed full RML, generated RDF checks,
authoritative Jena SHACL, and source-bound clock-isolation Jena SHACL. Input
hashes remained identical. The exact record fixtures include an actual pitch,
a PA header, two automatic balls, and an automatic strike.

| Game | PA records | Pitches | RDF triples | Clock handling |
| --- | ---: | ---: | ---: | --- |
| 822753 | 73 | 315 | 33,970 | Both pitch boundary measurements omitted |
| 823302 | 72 | 283 | 30,165 | Automatic ball preserved; unsupported precedence omitted |
| 823532 | 86 | 309 | 34,921 | Automatic ball preserved; unsupported precedence omitted |
| 823631 | 81 | 311 | 34,502 | Both PA boundary measurements omitted |
| 823740 | 84 | 359 | 38,347 | Automatic strike preserved; unsupported precedence omitted |

The affected automatic awards had no timestamp measurement maps before T1;
their inconsistent clocks now withhold order edges without suppressing the
supported award. Clock conflicts are retained separately from structural source
errors. Consistent measurements remain exact. A conflicting terminal PA header
also cannot supply a game-end measurement.

There were 74 passing focused tests across clock isolation, source
reconciliation, automatic awards, batting admission, runner histories, pitch
counts, and quarantine retry. They cover both clocks being omitted, timezone
comparison, preserved structure, independently supported awards, unchanged raw
records, unrelated errors still blocking, scoped history withholding, correction
identity guards, and rejection of original or renamed bad measurements.

For game 822753, batting, runner-resolution and scoring-run admissions passed.
Runner-history and defensive graphs conformed while their population admissions
remained withheld; pitch-count completeness remained withheld. These statuses
are deliberately distinct from successful graph promotion. T1 does not turn an
incomplete population into an admitted leaderboard.

All 13 production Jena query-index components built for that game; the resulting
8,965 triples passed index SHACL. A negative Jena control restored one disputed
timestamp and failed the clock gate. A query regression also confirms that a
missing terminal clock cannot misclassify an earlier pitch as the hit-by-pitch
pitch. Independently evidenced calls remain available.

`proof.json` retains exact input/RDF hashes and admission evidence. Original
full proof artifacts are in `%TEMP%/baseballo-t1-proof-20260917/`. Those are
isolated developer evidence, not production promotion markers. NiFi must run
its normal source validation, graph-pair promotion and batch materialization.
The aggregate repository gate remains NiFi-owned and asynchronous.
