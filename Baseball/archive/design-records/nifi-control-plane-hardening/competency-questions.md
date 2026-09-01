# Accepted control-plane decisions

1. May a NiFi configurator stop or update a processor whose desired definition
   already equals its live definition?
   **No.** Exact no-op reconciliation must leave the processor and its running
   state untouched.
2. May separately authored configurators implement their own processor
   stop/update race handling?
   **No.** They must use one shared, bounded reconciliation primitive.
3. May an explicit module or stage selection reconfigure unselected work?
   **No.** Selection is both the enablement scope and the mutation scope.
4. Is an exact-build fingerprint the same thing as a semantic query-index
   contract?
   **No.** Implementation/provenance identity and semantic compatibility are
   distinct evidence.
5. May a source-ingestion seed depend on Explorer benchmark-routing approval?
   **No.** It must use neutral promotion evidence plus its own declared grain
   requirements.
6. May a source run reference be accepted before the exact prerequisite gate
   used by its first NiFi stage succeeds?
   **No.** Submission and event dispatch must call the same pure preflight used
   by the corpus-seed stage.
7. May a downstream lane start before the upstream completion record is
   durable?
   **No.** Upstream completion is committed first. A separate idempotent
   dispatcher processes a durable outbox event afterward.
8. May failure to configure or queue a downstream source invalidate an already
   completed upstream source run?
   **No.** It creates downstream dispatch failure evidence while preserving the
   upstream completion.
9. Should successful daily game promotion trigger authority refreshes without
   Codex coordinating the handoff?
   **Yes.** NiFi owns the event-driven MLB-game to Teams handoff; successful
   Teams completion drives Leagues and Divisions through the same dispatcher.
10. What proves readiness?
    **A bounded lifecycle test** covering game promotion evidence, exact Teams
    preflight, Teams completion, and downstream outbox dispatch. Component-only
    checks are insufficient.
11. What scopes an automated source refresh?
    **A typed trigger pointer and checksum.** Automated Teams runs use the exact
    completed game batch; automated League and Division runs use the exact
    Teams completion. An explicitly requested global backfill remains a
    separate mode and may not be inferred from an unscoped event.
12. Is a transient wake-up FlowFile the dependency truth?
    **No.** Persisted batch and source completion evidence is the durable
    outbox truth. Wake-ups only prompt an idempotent rescan, so a crash between
    completion and dispatch is recoverable.
13. May Explorer routing metadata contribute to a neutral promotion-inventory
    fingerprint?
    **No.** The neutral fingerprint covers only promotion, manifest, graph-pair,
    and neutral contract evidence. Serving adds routing policy to its own
    separate snapshot fingerprint.
14. May semantic change control freeze NiFi control-plane code merely because
    its filename contains terms such as `rdf` or `context`?
    **No.** Guard ontology, RML, SHACL, SPARQL, semantic query definitions, and
    declared semantic-output contracts. NiFi scheduling, reconciliation,
    locking, transport, retries, and stage mechanics are implementation code,
    not semantic artifacts.
