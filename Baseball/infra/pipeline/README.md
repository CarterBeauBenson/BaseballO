# Pipeline storage and graph contract

NiFi owns movement through the local pipeline area; it does not alter supplied response bodies or make ontology decisions.

## Local stages

| Path under `%LOCALAPPDATA%\BaseballO\state\pipeline` | Contract |
| --- | --- |
| `inbox/games/` | User-controlled drop location for locally supplied completed-game JSON |
| `staging/manual-inbox/` | Short-lived byte-identical handoff between NiFi and the immutable archiver |
| `inbox/rdf/` | Compact per-game semantic work requests; never raw source bodies |
| `staging/rdf-requests/` | Active request state passed through the shared NiFi semantic stages |
| `raw/games/` | Immutable MLB `feed/live` responses, partitioned by season and game identifier |
| `raw/schedules/` | Immutable MLB schedule responses, partitioned by requested date |
| `raw/transactions/` | Immutable daily transaction API responses |
| `raw/reference/` | Immutable player and other slow-changing reference snapshots |
| `manifests/` | Acquisition metadata kept separately from response content |
| `evidence/nifi/game-processing/` | Compact per-stage results and log fingerprints |
| `evidence/nifi/game-promotion/` | Final proof that authoritative and index graphs are current together |
| `work/` | Retry-safe temporary processor inputs |
| `rdf/` | RML output awaiting or completing validation |
| `quarantine/` | Failed acquisition, mapping, validation, or load artifacts with error metadata |

The active job processes only files deliberately placed in the local inbox. A
valid game document is archived first; only a document whose own state is
`Final` creates an RDF work request. NiFi assesses dependency freshness and
promotes only a fully validated authoritative/index pair. Every submitted file
receives a separate import manifest or structured quarantine record.

Raw response bodies are stored by SHA-256, so repeating an import reuses identical content without overwriting it while changed responses receive a new immutable path. The import manifest records the safe staging filename, import time, content SHA-256, byte count, pipeline run identifier, local raw path, and whether that content was newly archived. NiFi provenance retains the submitted filename. Neither mechanism replaces or wraps the original JSON.

## Fuseki graph names

Graph IRIs are operational containers, not new ontology terms:

| Source | Named graph pattern |
| --- | --- |
| Completed game | `https://w3id.org/baseball/graph/game/{gamePk}` |
| Disposable query index | `https://w3id.org/baseball/graph/query-index/game/{gamePk}` |
| Daily transactions | `https://w3id.org/baseball/graph/transactions/{yyyy-mm-dd}` |
| Reference snapshot | `https://w3id.org/baseball/graph/reference/{snapshot-date}` |
| Acquisition provenance | `https://w3id.org/baseball/graph/acquisition/{run-id}` |

NiFi loads a complete authoritative graph with Graph Store Protocol `PUT`.
Reprocessing the same source therefore replaces that graph atomically instead
of appending duplicate statements. A successful authoritative load triggers a
guarded, independently replaceable query-index build. The index is disposable;
the full graph and immutable raw bytes remain authoritative. The public query
layer will use only the query endpoint; the write endpoint remains private.
