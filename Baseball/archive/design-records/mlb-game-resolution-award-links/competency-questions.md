# Accepted bounded graph contract

The user answered "Okay, lets keep it going" directly to the question asking
approval of `hasResolvedRunner`, `hasAdjudicatedBase`, and `settlesAwardFrom`.
This accepts the three named relations and the proposed conformance obligations
in [the reviewed specification](resolution-links-review.md). It does not accept
A3 immediate-before state, persistent entitlement, A5/A6 completeness or metric policy.

1. Which runner does this resolution concern? Exactly one `hasResolvedRunner`
   Person for a resolution using these links, also an explicit participant.
2. At which base was the runner adjudicated safe? `hasAdjudicatedBase` links
   the admitted Safe Process to its particular first, second or third Base,
   with the existing game/field context; unknown remains unasserted.
3. Which walk/HBP award does a completed arrival settle? `settlesAwardFrom`
   links a supported Safe or Run Process to the particular Walk/HBP Process
   in the same Game and PA. Require direct-award or corroborated forced-chain
   evidence; an independent balk in the PA does not settle a later walk.
4. Does a destination establish persistent entitlement? No. Its temporal
   scope is the particular adjudication, with no new stasis or exact timestamp.
5. Does safe at home substitute for a counted run? No. Preserve Run Process.

SHACL implements this bounded contract for newly linked resolutions. The
source record remains evidence about its particular resolution and decision.
