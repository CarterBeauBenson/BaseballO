# Source evidence and rules

Unchanged source: `data/raw/samples/2026-07-20/824087.json`, SHA-256
`249a1df5bb53bc0e5fac2ba16f2204029e7d6325229824523e7fccc85779f237`.
Its existing 29,276-triple fixture has SHA-256
`ded9c6b83739d9da9c913d0715a60b0596e4b8a9047ef2238a689654440b4e16`.
A focused audit inspected all 267 pitch records and their existing RDF
Ball/Strike/Foul Process links. The selected source excerpts and identities
are retained in [source-capture.json](source-capture.json).

| PA / event | Source observation | Current missing coverage |
| --- | --- | --- |
| 37 / 3 | Foul: 1-1 to 1-2, after event 2 reports Daniel Susac stealing second with count unchanged at 1-1. | Existing prefix selector does not account for this non-pitch steal report. |
| 64 / 2 | Foul: 0-1 to 0-2, after event 0 is a pitching change at 0-0 before the first pitch. | Existing prefix selector rejects every substitution. |
| 65 / 2 | Foul: 1-1 to 1-2, after event 1 is a completed overturned MJ call whose final value is Ball and count is 1-1. | Existing prefix selector rejects reviewed prefixes, although the operative count is explicit. |
| 72 / 0 | L / Foul Bunt, first pitch: strikes 0 to 1. | Foul bunt is outside the accepted M1 extension. |

The diagnostic also observed two hit-by-pitch records whose provider ball
counter increments. That counter change alone is **not** evidence for an
additional ordinary Ball Process and is not included as a proposed mapping.
Counter fields, institutional outcomes and measurement/quality instances must
retain their own meanings.

The 2026 official STRIKE definition distinguishes ordinary fouls with fewer
than two strikes from foul bunts, which are strikes without that restriction.
This supports the baseball rule used by M3/M4; it does not by itself admit the
source or authorize a new mapping.
[MLB 2026 Official Baseball Rules, Definitions of Terms, printed p. 158](https://mktg.mlbstatic.com/mlb/official-information/2026-official-baseball-rules.pdf#page=170).

No counter literal becomes a new ontology class or direct SQL score. No
original review decision is reconstructed by negating the final call.
