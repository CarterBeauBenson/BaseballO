# Pipeline storage and graph contract

NiFi owns movement through the local pipeline area; it does not alter MLB response bodies or make ontology decisions.

## Local stages

| Path under `%LOCALAPPDATA%\BaseballO\state\pipeline` | Contract |
| --- | --- |
| `raw/games/` | Immutable MLB `feed/live` responses, partitioned by season and game identifier |
| `raw/transactions/` | Immutable daily transaction API responses |
| `raw/reference/` | Immutable player and other slow-changing reference snapshots |
| `manifests/` | Acquisition metadata kept separately from response content |
| `work/` | Retry-safe temporary processor inputs |
| `rdf/` | RML output awaiting or completing validation |
| `quarantine/` | Failed acquisition, mapping, validation, or load artifacts with error metadata |

The acquisition manifest records source URL, HTTP status, retrieval time, content SHA-256, byte count, media type, pipeline run identifier, and local raw path. It never replaces or wraps the original JSON.

## Fuseki graph names

Graph IRIs are operational containers, not new ontology terms:

| Source | Named graph pattern |
| --- | --- |
| Completed game | `https://w3id.org/baseball/graph/game/{gamePk}` |
| Daily transactions | `https://w3id.org/baseball/graph/transactions/{yyyy-mm-dd}` |
| Reference snapshot | `https://w3id.org/baseball/graph/reference/{snapshot-date}` |
| Acquisition provenance | `https://w3id.org/baseball/graph/acquisition/{run-id}` |

NiFi loads a complete graph with Graph Store Protocol `PUT`. Reprocessing the same source therefore replaces that graph atomically instead of appending duplicate statements. The public query layer will use only the query endpoint; the write endpoint remains private.
