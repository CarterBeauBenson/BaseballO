# Operational improvements authorized September 23, 2026

The user requested implementation ("Do it up") of the ten recommendations
from the live NiFi/serving diagnosis. This records engineering scope, not an
ontology approval or permission to replace authoritative RDF.

The accepted API -> RML -> SHACL -> Fuseki -> queries -> SQL -> UI lifecycle
continues. Existing source schedules and running builds retain their scope.
Source facts, classes, properties, mapping semantics and SHACL constraints do
not change through this work. Any discovered mapping gap remains separately
identified; stale evidence is not relabeled as current.

| Work | Delivery |
| --- | --- |
| Admission evidence | Distinguish missing, stale and previously withheld proofs; refresh only supported evidence from retained inputs and existing RDF |
| Authority SQL | Recover stale locking and retry congestion without dropping promoted-graph events |
| Waiting and recovery | Queue pending dependencies; reconcile abandoned process status; bounded retries |
| Dashboard reads | Prepared SQL names and reference products; remove graph work from normal requests |
| Derived builds | Independent product ownership, versioned reusable calculations, resumable report partitions |
| Workload lanes | Prioritize current requests and isolate repair/historical requests within their owning source |
| SHACL execution | Reuse one loaded game across existing profiles with distinct reports and outcomes |
| Performance evidence | Retain stage durations and cache statistics; tune within workstation memory limits |
| Recovery | NiFi-owned consistent backup, separate-device export and isolated restore |
| Maintenance | Clear group names, readable canvas, shared small provisioning helpers and accurate operational status |

Live diagnosis: authority SQL has a September 4 orphaned lock and a saturated
retry loop; long-lived replay commands sleep while waiting on SQL; old process
records remain "running"; dashboard proof version mismatches mask earlier
admission outcomes. Historical percentile computation and optional player-name
SPARQL remain on the HTTP path. The workstation has approximately 11.3 GiB
usable RAM and had about 1 GiB available during the review.

Changes are deployed incrementally through their NiFi owners. Successful
component checks are not repeated as a manual aggregate release gate.
