# B2 contact continuation admission

Accepted design: [B2](../../../archive/design-records/contact-play-continuation-membership/README.md).
The context builder extends the existing BattedRunnerResolutionSource rows;
the RML templates and all domain identities remain unchanged.

```mermaid
flowchart LR
  source[Final MLB contact play and complete runner rows] --> check[Reconciled C1 personal histories and B2 continuation selection]
  check --> context[battedRunnerResolutions: all supported existing resolutions]
  context --> rml[Existing BattedRunnerResolutionSource RML]
  rml --> graph[Batted Ball Play has occurrent part Runner Resolution]
  check --> shape[Parameterized source-owned contact-continuation SHACL]
  graph --> validation[NiFi source SHACL before promotion]
  shape --> validation
```

The gate requires complete source/C1 histories, a unique terminal contact,
only matching contact-result/other_out movements at that event, no conflicting
review, substitution, independent event or control failure, and one personal
history per runner. An unadmitted mixed continuation produces no partial
contact membership. The parameterized SHACL checks every expected resolution
and episode membership and rejects extra Runner Resolution parts. It adds no
domain RDF or new vocabulary.

NiFi runs `contact-continuation-admission.py` in its existing source-SHACL stage,
after the authoritative profile and before graph-pair promotion. The source
census, exact instantiated shapes and validation report are retained, with
hashes in the proof and its promotion marker. A conformance failure fails the
stage; unsupported source cases remain explicit withheld cases. This proof
does not declare complete PA, game or reference-population metric scores.
