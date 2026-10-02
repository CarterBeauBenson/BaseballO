# F4 implementation — October 1, 2026

The user's named acceptance was committed and pushed in `96aae72` before
implementation. The exact reviewed patch is now applied: the context SHA-256 is
`86f6f6ad62eec5795b6bc464a0040c210e8be4bb83e94e65b765b943eb3cc00e`.

Only the context pin changes within the 55 protected artifacts. Its containing
digest, runtime reference and history-inventory reference follow that pin. The
global freeze remains unratified. The five RML maps, ontology and SHACL are
unchanged.

The existing evidence owner has an exact F4 compatibility entry. The changed
selector does not change admission censuses: the only admission path that uses
it is W1's intentional-walk selection, which already separately accepts the
same zero-episode witness and excludes a DH prefix. Unrelated context
definitions are unchanged. Old validation outcomes, producer hashes, source
hashes and graph identities remain intact; unknown fingerprints are rejected.
Older, stricter compatibility decisions retain their original restrictions.

Ten focused checks passed over the active implementation: the existing exact
compatibility chain, C3 prefix/replacement behavior, DH selection, zero-episode
isolation, accepted overlap handling and W1 intentional-walk behavior. The
prior candidate check separately verified the three actual missing strikes,
39 invalid-prefix mutations and 42 generated triples.

NiFi's existing counted-foul worker and two-minute timer are running and valid.
Its own bounded retry for game 822682, recorded with a `checkedAtUtc` of
00:48:36 UTC October 2 (October 1 Eastern), is complete: it added 28 triples
for the two selected strikes and the pitch-count admission is now admitted. Game
822688's last inspected record still belongs to the old failed implementation;
the new fingerprint permits its bounded retry. No manual graph write or
database rebuild was performed. SQL refresh remains owned by NiFi after
promotion; these results do not establish full dashboard population.
