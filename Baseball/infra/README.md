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
    `-- pipeline\
        |-- inbox\
        |-- staging\
        |-- raw\
        |-- manifests\
        |-- work\
        |-- rdf\
        `-- quarantine\
```

Set `BASEBALLO_LOCAL_ROOT` before invoking a script to use a different local disk.

## Commands

Run these commands from the repository root:

```powershell
.\scripts\infra\bootstrap.ps1
.\scripts\infra\start-stack.ps1
.\scripts\infra\status-stack.ps1
.\scripts\infra\test-stack.ps1 -WriteProbe
.\scripts\infra\backup-fuseki.ps1
```

Open:

- NiFi: <https://127.0.0.1:8443/nifi/>
- Fuseki UI: <http://127.0.0.1:3030/>
- Fuseki query endpoint: <http://127.0.0.1:3030/baseball-dev/query>
- Fuseki read/write Graph Store endpoint: <http://127.0.0.1:3030/baseball-dev/data>

NiFi uses a self-signed local certificate. On the first start, NiFi generates a local username and password and records them in its application log. Display them with:

```powershell
.\scripts\infra\show-nifi-credentials.ps1
```

Stop the services cleanly before restarting Windows:

```powershell
.\scripts\infra\stop-stack.ps1
```

## Security boundary

Both services bind to loopback for development. The Fuseki update and Graph Store write endpoints must never be exposed directly to the public UI. A future query API will expose only allowlisted, parameterized reads. Production secrets, TLS, operating-system services, backups, and firewall policy will be configured separately before deployment.

The local Fuseki process exposes `/$/ping`, `/$/stats`, and `/$/metrics` only on loopback for health and operations. Stop the stack before Windows shutdown when practical; TDB2 remains the transactional persistence layer.

The ontology is not copied, loaded, or modified by these bootstrap scripts.

The manual-import and graph-loading boundaries are documented in [`pipeline/README.md`](pipeline/README.md).
