# Source evidence

## Governing evidence

The 2022-2026 MLB-MLBPA Basic Agreement, Article XX, states that a Player with
the required Major League service becomes a free agent after the term of the
Uniform Player's Contract at a specified time. It also recognizes other routes,
including contract termination, failure to tender or renew, and a confirmed
election following qualifying outright assignment. The consequence is
eligibility to negotiate and contract with any Club.

- MLB-MLBPA Basic Agreement:
  <https://www.mlbplayers.com/_files/ugd/4d23dc_d6dfc2344d2042de973e37de62484da5.pdf>
- MLB Free Agency glossary:
  <https://www.mlb.com/glossary/transactions/free-agency>

This supports a positive, institutionally grounded Role. It does not support
defining the Role as the mere absence of a contract, roster membership, or
team-context Player Role. It also shows that no single declaration act is
necessary for every free-agency route.

## Accepted vocabulary available to the shape

- Role (`obo:BFO_0000023`);
- Person (`cco:ont00001262`);
- Baseball Team (`base:BaseballTeam`);
- Baseball Rule (`base:BaseballRule`);
- Action Permission (`cco:ont00000751`);
- Act of Contract Formation (`cco:ont00000684`);
- Gain of Role (`cco:ont00001194`);
- Stasis of Role (`cco:ont00000824`);
- Loss of Role (`cco:ont00000613`);
- `inheres in` (`obo:BFO_0000197`);
- `has realization` (`obo:BFO_0000054`);
- `has participant` (`obo:BFO_0000057`);
- `participates in` (`obo:BFO_0000056`);
- `permits` (`cco:ont00001910`);
- `affects` (`cco:ont00001834`);
- `occupies temporal region` (`obo:BFO_0000199`); and
- `precedes` (`obo:BFO_0000063`).

No new object property is required. The exact institutional Action Permission
individual and the evidence for each Gain/Loss boundary are data and source
contract questions, not new relation vocabulary.

## Source limitation

The MLB transaction feed can report labels such as `Declared Free Agency`,
`Released`, `Retired`, and `Signed as Free Agent`. Those labels are evidence
ICEs. Until a code-specific rule demonstrates the underlying route, agent,
participants, and temporal boundary, the row remains information-only.

