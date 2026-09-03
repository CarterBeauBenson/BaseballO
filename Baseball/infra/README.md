# Local NiFi and Fuseki stack

This directory defines BaseballO's no-license-fee local development services:

- Eclipse Temurin OpenJDK 21
- Apache NiFi 2.10.0
- Apache Jena Fuseki 6.1.0 with persistent TDB2 storage
- RMLMapper 8.1.0

Versions and release checksums are pinned in [`versions.psd1`](versions.psd1). The bootstrap script verifies every archive before extraction.

## Storage layout

By default, binaries and mutable state live under `%LOCALAPPDATA%\BaseballO`, outside Git and the OneDrive repository:

```text
%LOCALAPPDATA%\BaseballO\
|-- downloads\
|-- runtimes\
|   |-- jdk-21.0.12+8\
|   |-- nifi-2.10.0\
|   |-- apache-jena-fuseki-6.1.0\
|   `-- rmlmapper-8.1.0\
`-- state\
    |-- fuseki\
    |   |-- databases\baseball-dev\
    |   |-- logs\
    |   `-- fuseki.pid
    |-- nifi\
    |   |-- content_repository\
    |   |-- flowfile_repository\
    |   |-- provenance_repository\
    |   |-- database_repository\
    |   |-- flow\
    |   `-- secrets\
    |-- pipeline\
        |-- inbox\
        |-- staging\
        |-- transient\
        |-- raw\
        |-- manifests\
        |-- evidence\
        |-- events\promoted-graphs\
        |-- work\
        |-- rdf\
        `-- quarantine\
    `-- serving\
        |-- builds\
        |-- authority\
        `-- equivalence\
```

Set `BASEBALLO_LOCAL_ROOT` before invoking a script to use a different local disk.

The high-volume RDF store can be moved independently while runtimes, NiFi,
transient pipeline state, and the analytical SQL serving layer remain local.
Use the guarded one-time migration command with a dedicated directory on the
external volume:

```powershell
.\scripts\infra\migrate-rdf-storage.ps1 `
  -TargetRoot 'D:\BaseballO\RDF' `
  -RemoveLocalAfterVerification
```

The command stops NiFi and Fuseki, copies the stopped Fuseki state, verifies an
exact SHA-256 inventory, writes a machine-local storage contract under
`%LOCALAPPDATA%\BaseballO\state\storage.json`, starts and health-checks Fuseki
from the external store, optionally removes the verified local copy, and then
restarts NiFi. The external root contains a unique marker that prevents a
different volume mounted under the same drive letter from receiving RDF. If
the configured volume or marker is absent, ingestion fails closed instead of
silently creating a new empty local database.

On the current workstation, that guarded contract points the high-volume RDF
state to `D:\BaseballO\RDF`. Runtimes, transient NiFi state, and immutable
SQLite serving builds remain under the local state root. Keep the configured
external volume attached whenever NiFi or Fuseki may read or write the
datastore; the marker check prevents accidental fallback to another volume.

## Commands

Run these commands from the `Baseball/` project directory:

```powershell
.\scripts\infra\bootstrap.ps1
.\scripts\infra\start-stack.ps1
.\scripts\infra\status-stack.ps1
.\scripts\infra\test-stack.ps1 -WriteProbe
.\scripts\infra\backup-fuseki.ps1
```

Open:

- NiFi: <https://127.0.0.1:8443/nifi/>
- Fuseki UI: <http://127.0.0.1:3031/>
- Fuseki query endpoint: <http://127.0.0.1:3031/baseball-dev/query>
- Fuseki read/write Graph Store endpoint: <http://127.0.0.1:3031/baseball-dev/data>

NiFi uses a self-signed local certificate. On the first start, NiFi generates a local username and password and records them in its application log. Display them with:

```powershell
.\scripts\infra\show-nifi-credentials.ps1
```

Stop the services cleanly before restarting Windows:

```powershell
.\scripts\infra\stop-stack.ps1
```

## Security boundary

Both services bind to loopback for development. The Fuseki update and Graph
Store write endpoints must never be exposed directly to a public UI. The
current local Explorer server exposes only allowlisted, parameterized reads;
its browser never submits raw SPARQL. Production secrets, TLS, operating-system
services, backups, and firewall policy will be configured separately before
deployment.

The local Fuseki process exposes `/$/ping`, `/$/stats`, and `/$/metrics` only on loopback for health and operations. Stop the stack before Windows shutdown when practical; TDB2 remains the transactional persistence layer.

The ontology is not copied, loaded, or modified by these bootstrap scripts.

The RML, graph-loading, query-index, and serving components are documented in
the [`scripts/pipeline` runbook](../scripts/pipeline/README.md). The seven
configured source-owned NiFi lanes, their proof and corpus submission commands,
the shared Analytical Serving, DSQ SQL Materialization, Repository Evidence,
and Serving Equivalence groups, and the active 05:00 Eastern schedules are documented in the
[`NiFi runbook`](nifi/README.md).
