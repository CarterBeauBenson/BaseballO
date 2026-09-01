# Accepted competency-question answers

1. Every genuine pitch type in the reviewed MLB pitch-type catalog is
   represented by reusable Nominal Measurement ICE content under the MLB
   pitch-type Reference System. Each such ICE is a nominal measurement of a
   particular Pitch Act and may provide mapping evidence for a corresponding
   source-independent Pitch Act subtype. `Slider` was only an example.
2. The provider `playId` is represented by an Identifier ICE that designates
   the source event-record ICE. That identifier content may safely contribute
   to the event-record IRI because its purpose is to distinguish that record.
   The source event record is about the particular Pitch Act.
3. A generated plate-appearance-start out count is not free-floating. Its
   integer is derived from the preceding institutionally counted Out Processes
   recorded as occurrent parts of the same Half Inning. The count ICE is about
   that Half Inning at the Plate Appearance's start boundary and remains linked
   to the Plate Appearance whose start state it describes.
4. Provider routing tokens such as event type, pitch call, and replay status do
   not serve as record identifiers or RDF types. They may trigger accepted
   world-side, decision, or record structures. Reusable provider-code ICEs are
   retained only where the classification has independent provenance or query
   value.
5. A replay-review Act may output new Decision and review-result ICEs. The
   earlier Decision and its source evidence remain in the historical graph;
   the later Decision overrides its institutional effect rather than erasing
   the earlier state.
6. The rulebook strike zone is a three-dimensional Site. The 2026 ABS
   evaluation plane is a two-dimensional Fiat Surface that is a continuant part
   of that Site. The applicable rule and evaluation method determine which
   structure governs a particular adjudication.
7. Preseason, regular season, postseason, All-Star Game phase, offseason, and
   transaction-relevant offseason segments are Processes that are occurrent
   parts of a Baseball Season. Game-containing phases have Baseball Games as
   occurrent parts. Offseason segments need not contain a Game. Their Temporal
   Regions are temporal parts of the Season's Temporal Region.

Exact pitch-type class definitions, replay override relation selection,
strike-zone class definitions, and the inventory of transaction-relevant
offseason subsegments remain implementation proposals rather than facts added
by this decision record.
