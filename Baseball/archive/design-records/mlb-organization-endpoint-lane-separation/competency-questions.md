# Competency questions

1. Can the MLB teams connector be stopped, retried, quarantined, or rebuilt
   without stopping the MLB leagues or MLB divisions connectors?
   **Accepted:** yes.
2. Can the MLB leagues connector be stopped, retried, quarantined, or rebuilt
   without stopping the MLB teams or MLB divisions connectors?
   **Accepted:** yes.
3. Can the MLB divisions connector be stopped, retried, quarantined, or rebuilt
   without stopping the MLB teams or MLB leagues connectors?
   **Accepted:** yes.
4. Does each endpoint family own its acquisition contract, transient payload
   lifecycle, RML, SHACL, graph namespace, promotion evidence, and NiFi process
   group?
   **Accepted:** yes.
5. May the three lanes reuse source-neutral execution machinery?
   **Accepted:** yes, provided the shared machinery contains no endpoint field
   selection, source-specific semantic assertions, or cross-lane payload state.
6. Does the separation change the approved world-side classes, relations, or
   identity of Teams, Leagues, Divisions, Seasons, Plans, Phases, Days, Names,
   or Identifiers?
   **Accepted:** no. The accepted `mlb-organizations-source-contract` semantics
   remain unchanged and are partitioned by the endpoint that supplied them.
7. Do source Response ICE identity and promoted graph identity become
   connector-specific?
   **Accepted:** yes. The source-module identifier and graph namespace must make
   the independently detachable provenance boundary explicit.
8. Is legacy combined `mlb-organizations` executable material retained as an
   active compatibility lane?
   **Accepted:** no. It is retired so it cannot pull future work back toward a
   combined connector.
