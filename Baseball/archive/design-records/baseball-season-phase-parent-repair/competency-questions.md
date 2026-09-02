# Competency questions

1. Is every Baseball Season Phase still inferable as a BFO Process when its
   direct parent is only Baseball Season Segment?
2. Does removing the redundant direct Process assertion preserve the accepted
   distinction between a game-containing Baseball Season Phase and the broader
   Baseball Season Segment?
3. Can the ontology retain one direct named parent for Baseball Season Phase
   without changing its restrictions, definition, examples, or descendants?

## Accepted answers recorded in conversation

- Yes. Baseball Season Segment remains a subclass of BFO Process, so the
  Process ancestry is preserved by subclass transitivity.
- Baseball Season Phase remains a Baseball Season Segment that has the accepted
  game-containing restrictions in the axioms overlay.
- Only the redundant direct `rdfs:subClassOf obo:BFO_0000015` assertion is
  removed.
