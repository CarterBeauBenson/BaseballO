# Acceptance boundary

```mermaid
flowchart LR
  Accepted[Accepted current MLB-game contract] --> Pinned[Pinned RML and SHACL]
  Pinned --> Pipeline[NiFi validation and promotion]
  Future[Future fields or models] -.-> Review[Proposal-first review gate]
  Review -.-> Pinned
```
