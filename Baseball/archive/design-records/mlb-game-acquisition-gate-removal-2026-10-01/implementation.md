# Acquisition gate removal outcome

Implemented in `fe45c4d` after the instruction record `9ad6007` was published.

NiFi's MLB Game group now connects `Prepare Schedule Batch` directly to
`Acquire MLB Schedule`. All four obsolete proof-release processors were removed.
The waiting request was preserved in its original NiFi queue and redirected;
no FlowFiles were dropped. Per-game RML, source SHACL, promotion, HTTP retries
and the 05:00 Eastern daily trigger remain active.

On October 1, 2026, the recovered September 30 request produced batch
`5e40d2bcf6ca42a2a16601338a46b9e4` at 17:31:57 UTC with four completed games.
The missed September 29 daily request was resubmitted through the existing
NiFi request processor, producing batch `859c595579184efe8494645ebd0465df`
at 17:33:13 UTC with four completed games. The request processor's original
configuration was restored after its one-shot execution.

Live NiFi counters confirmed two schedule responses, eight game acquisitions
and eight games passing the final-game filter. Both batches were still pending
downstream processing when checked; these are acquisition results, not claims
of completed RDF promotion, SQL publication or dashboard coverage.

Focused checks passed for queued-request preservation, idempotent migration,
unchanged per-game validation routes, separation from other source gates, and
PowerShell syntax. No RML, ontology or semantic-freeze files changed.
