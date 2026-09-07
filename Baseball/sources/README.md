# Source modules

Every external or derived source owns a detachable module. A module contains
its source contract, source-specific RML, source-specific SHACL, and NiFi lane.
Modules may reuse the shared ontology and mapping policies, but they must not
import another source's files or emit claims from another source.

The triple store is the integration boundary. Cross-source meaning is expressed
by explicitly dependency-scoped SPARQL after each source graph has passed its
own validation and promotion gates. Removing or stopping one module must not
prevent unrelated modules from ingesting, validating, or promoting.

[`source-modules.json`](source-modules.json) is the machine-readable registry.
The registered source modules are:

- [`mlb-game/`](mlb-game/) for game-event evidence and the existing daily feed;
- [`mlb-teams/`](mlb-teams/) for the MLB Teams endpoint and Team authority;
- [`mlb-leagues/`](mlb-leagues/) for the MLB Leagues endpoint and League/Season authority;
- [`mlb-divisions/`](mlb-divisions/) for the MLB Divisions endpoint and Division authority;
- [`mlb-people/`](mlb-people/) for persistent Person authority records;
- [`mlb-venues/`](mlb-venues/) for persistent Venue and Baseball Field
  authority records; and
- [`mlb-transactions/`](mlb-transactions/) for event-scoped transaction
  evidence.

Their operational state remains explicit in the registry. Statcast, weather,
and travel/rest sources receive new sibling modules after their own semantic
review; they never extend an existing MLB module merely because MLB is the
provider.

All seven registered modules are active. Each passed its current bounded proof,
owns an independent 05:00 Eastern trigger, and can be stopped without stopping
the other six. Submission and completion of a particular corpus run are
runtime facts, not source-contract facts. Use source-local terminal evidence to
establish promotion, quarantine, and cleanup without continuously polling the
processors.

Persistent, re-identifiable entities use module-owned authority products.
One-time Processes and Acts require event-scoped evidence rather than reuse as
identity authorities. Both remain persistent RDF after promotion. When a
reference-source response contains supporting occurrent evidence as well as a
persistent entity, its placement in the same authority graph or a separate
source-owned event/evidence graph is an explicit review decision; it is not
inferred from provider nesting or RDF type alone.

Operational and semantic state are deliberately separate. An operationally
active module may continue to run its pinned artifacts while its semantic
surface is frozen. That does not license mapping changes or represent
ontologist acceptance. Each module's machine-readable semantic-status record
names its open blockers and whether extension is allowed.

## Module contract

Each module must declare:

- its source owner and graph namespace;
- its schema, mapping, and SHACL artifacts;
- every source-specific NiFi process group in its acquisition-through-promotion lane;
- the authoritative source it may map;
- its disconnect and retention behavior; and
- its separate operational status, semantic status, extension policy, and
  machine-readable blocker record; and
- any derived outputs it triggers after authoritative promotion.

Shared files are limited to source-neutral ontology, IRI/modeling policies,
reasoning profiles, query-index contracts, and integration queries that declare
their source dependencies.

Future modules are not represented by empty directories, reserved graph names,
or placeholder NiFi groups. Their operational names enter the registry only
when the module exists and can own the entire boundary.

## Ordered source roadmap

- [x] Resolve the frozen MLB game semantic blockers and admit the corrected
  pinned executable contract.
- [ ] Finish useful, non-duplicative `feed/live` coverage using proposal
  Mermaid and one-game proof before extending RML.
- [x] Implement the accepted teams/leagues/divisions, people, transactions,
  and venues semantic contracts as separate MLB API modules. Shared provider
  and identifiers do not merge their RML or SHACL.
- [x] Operationally admit each reviewed MLB lane only after its bounded proof
  passed. A later corpus request remains asynchronous and does not alter the
  proof decision.
- [ ] Restart Statcast as a new module from a fresh field inventory and
  ontologist-approved world-side Mermaid. Do not reuse rejected Statcast RML,
  SHACL, graph, or source-schema classes.
- [ ] Add weather and travel/rest/circadian sources as independent modules only
  after their own evidence and semantic review.
- [ ] Add multi-source SPARQL only after its required source graphs can be
  validated, promoted, disconnected, and rebuilt independently.
