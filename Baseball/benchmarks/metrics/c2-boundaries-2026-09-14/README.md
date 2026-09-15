# Bounded C2 runner-state adapter

Metric suite 2.0.12 implements the already accepted C2 analytical projection
over promoted C1 personal histories. It changes analytical SPARQL, the reducer,
SQL evidence consumption, and display plumbing. It introduces no RDF statement,
object property, ontology term, RML change, or semantic approval.

The existing graph supplies the PA's half-inning, Temporal Interval, first and
last instants, and timestamps explicitly designating those instants. These are
conservative bounds for contained runner episodes. A prior Safe decision and a
later episode in the same complete history bracket an intervening PA. Only when
that entire PA is strictly between those bounds, and the complete history has
no member in that PA, does the adapter carry the runner's safe base through it.

Source indexes and IRI spelling never establish order. All history members must
have unambiguous movement bindings, consistent state transitions, and supported
nonoverlapping PA bounds. Unordered episodes within one PA, missing members,
ambiguous destinations, conflicting histories, and events after a terminal
outcome withhold projection. No state is extended past the last known episode;
half-inning parthood alone does not establish a stranded runner's termination.

## Real evidence and checks

[result.json](result.json) comes from the existing 31,717-triple, SHACL-validated
proof RDF for game 566279. Jena evaluates the canonical evidence query. The
same bindings then traverse the normal in-memory SQL materialization/query
path, with exact result equality checked for run depth and TFS evidence.

- 18 personal histories inspected; 17 have supported episode order.
- Three unchanged runner/PA states: runner 444482 at second during PA source
  index 4; runner 592518 at first during indexes 53 and 54.
- One history withheld because multiple episodes within a PA lack supported
  internal order. Zero duplicate-history state claims were admitted.
- Nine of thirteen counted runs retain complete run-depth results; Flores's
  value remains exactly 3/1. This change does not close the four missing runs.
- Twelve boundary-adapter tests, twelve run-depth tests, four shared-dashboard
  tests, eight serving tests, and four focused Node tests pass. The browser
  smoke test passes automatic loading, stale-request rejection, the existing
  live August 25 award example, and the real-RDF/SQL proof's mobile display.

The browser's proof response is an explicit HTTP fixture for presentation
testing. Game 566279 remains intentionally classified as the development
fixture and excluded from public regular-season date selection. A public query
for April 1, 2019 returned zero games, as expected for this corpus. The current
2026 corpus receives C1 histories through the already queued NiFi source
recovery; this check neither runs ingestion nor claims that refresh is done.

The UI lists the supported states under coverage details, with optional
graph-scoped player names and downloadable evidence. A base state is not a PA
score or a player leaderboard entry. Both complete-PA and population-complete
flags remain false. The existing metric fingerprint guard rejects obsolete
SQL products until NiFi completes a matching validated build.

## Research consequences

- Interrupted batting turns can earn no PA. Qualification must preserve that
  distinction. [MLB PA definition](https://www.mlb.com/glossary/standard-stats/plate-appearance)
- Timer violations can change the count without a pitch.
  [MLB pitch-timer rule](https://www.mlb.com/glossary/rules/pitch-timer)
- Statcast CSV `balls` and `strikes` describe the pre-pitch count. These cannot
  silently replace the accepted recovery metric's post-pitch sequence.
  [Statcast CSV documentation](https://baseballsavant.mlb.com/csv-docs)

Those factual questions are resolved; the owning MLB lane still needs admitted
graph coverage for official PA attribution, exact pitch/non-pitch state, and
within-PA consequence boundaries. The inspected frozen RML has PA timestamps
but does not supply those complete contracts. The separate
[defensive-source investigation](../../../proposals/graph-native-metric-suite-batch-review/defensive-source-research-2026-09-14.md)
records the available sequence evidence and its coverage/access limits.
Neither external definitions nor another SQL rebuild can substitute for those
missing inputs. Full player rankings remain unfinished.
