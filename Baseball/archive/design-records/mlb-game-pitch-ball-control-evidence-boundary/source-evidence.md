# Source and repository evidence

The accepted MLB-game RML review manifest states that passed-ball and wild-pitch classifications do not independently establish a physical pitch-ball control failure. Its uncaught-third-strike pattern likewise forbids fabrication of a physical failure from the unresolved runner placeholder.

The executable RML follows that boundary: it creates the scorer-classified institutional processes, judgments, decisions, rules, and records, but no `PitchBallControlFailureProcess`.

Game `823539` exposed drift in the generated-RDF validator. The source contained three passed-ball/wild-pitch classifications; RML generated the approved institutional graph, while the validator incorrectly expected three physical failures and predecessor links. This decision restores the validator and SHACL gate to the accepted mapping contract.
