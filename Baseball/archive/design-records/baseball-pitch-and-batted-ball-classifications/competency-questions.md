# Competency questions

1. Can a particular Pitch Act be retrieved by MLB pitch-type classification
   without typing its Ball Motion Process as the pitch type? **Proposed: yes.**
2. Can one reusable pitch-type ICE nominally measure many Pitch Acts?
   **Proposed: yes.**
3. Do grip, velocity, break, spin, or shape define these classes?
   **Proposed: no.** They remain separately represented evidence.
4. Which pitch types receive classes? **Proposed:** MLB's fourteen documented
   2025 Statcast categories plus the historically documented Eephus category.
5. Do `Other`, `Unknown`, intentional-ball, or pitchout tokens create pitch-type
   classes? **Proposed: no.** The latter two concern objective or game tactic
   and require their own Act review rather than masquerading as physical pitch
   types.
6. What does `ground_ball`, `line_drive`, `fly_ball`, or `popup` classify?
   **Proposed:** the particular Batted-Ball Motion Process, not the batter's
   Swing or Bunt Act.
7. Can a provider reclassification change the asserted class without erasing
   older evidence? **Proposed: yes.** Preserve versioned nominal-measurement
   evidence in authoritative history, but keep explicit current class typing in
   a rebuildable current-state reasoning graph. Historical classification
   triples never trigger OWL class inference.
