# Benchmark and equivalence evidence

This directory preserves measured and semantic evidence. A checked-in capture
is immutable research history: its timestamp, corpus, contract fingerprint,
query hashes, results, and timings must not be relabeled when the live contract
changes. A new run creates a new capture; a separate admission record decides
whether current runtime routing may rely on it.

- [`canned-query-audit/`](canned-query-audit/) records bounded authoritative
  query results and corpus identity.
- [`advanced-query-audit/`](advanced-query-audit/) records the reviewed
  advanced catalog over the same bounded corpus.
- [`query-audit-evidence-register.json`](query-audit-evidence-register.json)
  records the immutable canned and advanced captures and the separately
  reviewed canonical-text compatibility fingerprints used by current checks.
- [`query-index/`](query-index/) contains authoritative/index equivalence,
  timings, algebra, TDB2 traces, and the immutable capture register.
- [`serving-layer/`](serving-layer/) contains a historical compact summary of a
  local SQL serving build. Its local graph scope and implementation boundary
  are stated explicitly; it is neither the checked-in raw-corpus baseline nor
  proof of the current materializer.

Runtime databases, full logs, and disposable generated artifacts stay under
the local state root. Compact evidence may be promoted here only with its exact
scope and provenance.
