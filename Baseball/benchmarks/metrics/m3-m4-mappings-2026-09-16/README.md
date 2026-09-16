# M3/M4 counted-foul completion proof

The explicit decision was published in `e4166c1` before implementation.
The unchanged MLB game 824087 source now serializes the three previously
missing ordinary second-strike fouls (PAs 37, 64 and 65) and first-strike
foul bunt (PA 72). No new ontology term or object property was introduced.

Nineteen focused source/conformance tests passed, including counter, identity,
review, substitution, runner and order mutations. A separate actual RMLMapper
one-PA foul-bunt proof passed before the whole-game proof. Whole-game RML
produced 29,351 triples; authoritative Jena SHACL passed without violations.
The independent complete count census admitted all 73 PAs and 267 pitches
against RDF, with no remaining count-history issues in this game.

See [result.json](result.json) for retained hashes and admission evidence.
This proof does not claim live promotion, complete C1 runner histories or
complete-season reference populations. NiFi owns the existing asynchronous
refresh, source validation and promotion stages.
