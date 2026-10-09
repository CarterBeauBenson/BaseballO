# Independent offense and defense publication

Accepted October 9, 2026. In response to the explicit recommendation to build
and publish offense and defense independently over the same existing RDF, the
user instructed: "Good. Do it".

Offensive products (batting, baserunning, run construction and Empty Games)
must be able to reach the dashboard when defensive calculation or preparation
fails. Defensive products have separate progress, retries and freshness.
Metrics that actually combine both, including PAQ-2.1, retain both dependencies.
Review and participation metrics retain their own applicable dependencies.
The dashboard combines prepared products and exposes their freshness and
coverage without representing stale or incomplete results as current.

The existing authoritative RDF, accepted metric meanings, source conformance,
SQL serving architecture and NiFi resource budget remain in place. NiFi owns
execution and retry; the UI performs no graph queries or expensive calculation.
The change does not authorize source reacquisition, RML reruns, a database
rebuild, ontology terms, object properties, or pending EG2–EG5 semantic decisions.

A verified out, safe advance or run needed by offense remains an offensive
dependency. A missing field/catch/throw/tag sequence does not by itself invalidate
that verified outcome. Isolation does not resolve genuine offensive attribution,
official PA eligibility or runner-outcome gaps.

Implementation plan:

1. Partition derived calculation and player preparation by dependency family,
   retaining shared RDF extraction and bounded resource use.
2. Give each family resumable progress and an independent publication boundary;
   retain prior valid products when another family fails.
3. Carry family freshness and failure information through prepared SQL to the UI.
4. Exercise defensive-failure isolation and unchanged offensive values with
   focused component regressions, publish to dev, and let NiFi execute the build.
