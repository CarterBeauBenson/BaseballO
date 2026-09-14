# Contribution dashboard: live evidence capture

The dashboard uses one game/date selection for all 20 existing metrics.
It separates scoped results, individual play/run results and unavailable
scores. Selecting a card opens the exact result from that same response.
Definitions, examples, evidence traces, coverage and gaps remain accessible.

## Actual selection

The [HTTP response](dashboard-response.json) covers the 15 loaded regular-season
games on **August 25, 2026** and used **authoritative RDF fallback**.
It reports 1,164 observed PAs, 126 observed runs and 1,567 movement pairs.
No movement in this selection was linked to a C1 personal history.
These evidence counts do not certify completeness of a metric population.

- TFS: one supported award play, exact **25/12**, displayed **2.08**.
- Offensive Reach: that same play, exact **4/1**, displayed **4**.
- Adjudication Volatility: **13/23**, displayed **56.5%**, over explicitly
  resolved mapped reviews.
- The other 17 metrics have no score for this selection. Missing scores
  are shown as unavailable; no fabricated zero or player ranking is supplied.

See the [desktop dashboard](desktop.png) and [mobile view](mobile.png).
The live browser test verified one dashboard request, all 20 cards, filtering,
matching exact details without another request, and disabled stale downloads.
Late single-metric and dashboard responses cannot restore an old selection.

## Validation and limits

Python regression checks show the shared response equals all 20 individual
calculations over the same bindings, and SQL returns those exact results.
Removing one selected metric's stored result rejects the SQL dashboard.
The existing route's schema, implementation and evidence-admission contract
checks remain enforced. Public requests cannot inject graph facts or
completeness flags. Node and browser checks cover endpoint routing, fallback,
SQL-required behavior, scoped zero versus missing scores, and mobile layout.

The nine complete Run Construction Depth results from the separate
[C1 real-game proof](../c1-run-depth-2026-09-14/README.md) are still a separate
capture. This dashboard proof does not claim that game was promoted or that
those histories exist in the August 25 selection. Full operation of all 20
metrics remains incomplete; no ontology, RML or source SHACL changed here.

NiFi retains ownership of serving refresh and the asynchronous repository
gate. This capture proves a working live RDF route and separately tested SQL
equivalence, not completion of a new production SQL build.
