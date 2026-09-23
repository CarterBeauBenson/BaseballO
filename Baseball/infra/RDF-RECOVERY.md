# RDF backup and isolated restore

The recovery component implements explicit stages invoked by NiFi's `RDF
Recovery` group. Its owner now schedules daily backup/export and weekly isolated
restore, with bounded retries and retention. It never replaces the live TDB2
directory. The configured export is on the workstation's C: drive, separate
from the D: RDF drive; off-machine recovery remains unconfigured. Enabling this
owner does not establish that a full production restore has completed.

The [September 23 operating record](OPERATIONS-IMPROVEMENTS.md#recovery-storage-and-operating-limits)
documents paths, free-space requirements, two-export/two-restore retention and
deferral while SQL builds are active.

`scripts/pipeline/rdf-recovery.py` uses Fuseki's asynchronous backup API and
gzip N-Quads output. See the [Fuseki administration protocol](https://jena.apache.org/documentation/fuseki2/fuseki-server-protocol.html).
It supports the documented task array and the installed Fuseki 6.1 object
response, including its capitalized `Backup` task name.

## Stages

1. `submit` records intent before the HTTP request, the existing backup filenames,
   submission time, dataset and returned task ID. NiFi supplies a stable UUID
   with `--request-id`; retries return the existing submission instead of issuing
   another POST. An uncertain submission or reused identity with different inputs
   fails for review. Do not manufacture a new UUID merely to retry a lost response.
2. `complete` checks that exact task and returns `pending` immediately if it is
   still running. NiFi owns requeue and retry. A successful task must have exactly
   one fresh, completed backup artifact. Old files, ambiguous concurrent artifacts,
   wrong operations and reused task IDs fail closed. Keep only one outstanding
   backup for a given dataset; external concurrent backups require review.
3. `verify` checks the recorded SHA-256, compressed size and decompressed size.
   Full streaming gzip reads detect truncation and CRC failures. This proves
   archive integrity, not semantic conformance or complete workstation recovery.
4. `export` copies into a unique partial directory at an existing destination,
   checks the copied archive, writes its manifest and renames the directory only
   after verification. Failed partial copies remain identifiable. Existing exports
   are reused only when identity, manifest and archive match.
5. `stage-restore` verifies the export and invokes Jena's transactional basic
   loader in a newly allocated `restores/<UUID>/tdb2` directory. It records success
   or failure and never promotes a pointer or writes to a named live store.
   A loaded database still needs application and evidence checks before any
   separately planned cutover. See [Jena's loader documentation](https://jena.apache.org/documentation/tdb2/tdb2_cmds.html).

From `Baseball/`, the local convenience wrapper now submits asynchronously:

```powershell
.\scripts\infra\backup-fuseki.ps1
.\scripts\infra\backup-fuseki.ps1 -Action Complete -Job '<returned job ID>'
.\scripts\infra\backup-fuseki.ps1 -Action Verify -Job '<returned job ID>'
```

This replaces the old blocking helper and its unsafe selection of the newest
file regardless of which task created it. The old `-TimeoutSeconds` argument
has been removed. Routine orchestration must invoke the Python component with
a stable request UUID; the convenience wrapper creates a new request each time.

All Python commands require `--root <local recovery evidence directory>` before
their action. `export --job <ID> --destination <existing directory>` publishes a
verified copy. `stage-restore --export-directory <export> --java <pinned java.exe>
--jena <pinned fuseki-server.jar>` stages a fresh database. Neither command
changes the authoritative storage contract. The exporter does not infer whether
a destination is physically off-machine; that requires the operator's actual
storage choice and a restore test from that location.

## Scope and recovery requirements

The archive contains the RDF dataset, including named and default graphs. It
does not contain NiFi queues, credentials, source/promotion manifests, source
identity evidence, machine storage markers, runtime binaries, or SQL databases.
Authoritative RDF must remain paired with its retained source and promotion
evidence before a replacement installation can safely resume ingestion or
rebuild serving. Git alone does not contain that runtime evidence.

Before declaring full disaster recovery operational, choose an off-machine
destination, RPO/RTO and account access; preserve the required runtime evidence
and protected configuration; then restore the actual corpus
and its evidence on an isolated replacement. Credential protection and actual
off-machine access must be verified there. This component does not silently
copy secrets or claim that RDF alone restores the whole application.

## Focused verification

Fourteen tests cover missing/old/ambiguous artifacts, task identity, pending and
failed tasks, truncated gzip, manifest integrity, idempotent submission/export,
interrupted copies and refusal to launch Java for an invalid export.

`scripts/pipeline/verify-rdf-recovery.py` starts a separate temporary Fuseki,
creates a four-row synthetic dataset, runs an actual backup, exports it,
loads a new TDB2 database and compares query results. The proof preserved the
default graph, two named graphs, Unicode, a blank-node label and an integer
larger than JavaScript's safe integer range. The live dataset was not touched.
This is a component proof, not a full-corpus or off-machine restore.
