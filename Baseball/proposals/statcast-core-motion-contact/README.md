# Statcast core motion and contact review

Status: **under review — design only**

This package consolidates the first Statcast review slice around the physical
processes that already exist in BaseballO: the pitch, pitch-ball motion,
swing, bat-ball contact, and batted-ball motion. It then asks what additional
world-side geometry and process-profile structure is required for the small
set of nonduplicative Statcast motion fields.

The package proposes no ontology term and authorizes no RML, SHACL, source
module, acquisition, graph promotion, serving materialization, or UI change.
It uses only accepted BaseballO, BFO, and CCO vocabulary in solid Mermaid
edges. Dotted edges terminate in explicit modeling questions.

The accepted 113-field inventory remains the complete de-duplication ledger.
This package selects only its core motion/contact subset. Analytical model
outputs, defensive alignment, and other later concerns remain separate review
questions.

If accepted as the consolidated foundation, a separate disposition decision
will be needed for the overlapping active pitch-speed, arm-angle, and
bat-tracking drafts. They are not silently superseded by this review draft.

