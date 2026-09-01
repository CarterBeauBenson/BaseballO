# MLB people throwing-side disposition

Status: **accepted 2026-08-30 — source-independent design**

Although the provider field is named `pitchHand`, the accepted realist target
is not pitcher-specific. Every evidenced baseball player bears a Throwing Side
Disposition, and a corresponding Throw Act or Pitch Act may realize it. Those
accepted event grains remain distinct and neither supplies the identity of the
disposition.

The provider code is a Nominal Measurement ICE about the real disposition. It
does not turn the Person into a left/right kind, identify a Hand individual, or
assert that every Throw Act uses the reported side. An ambidextrous player may
bear both left- and right-side particular dispositions.

This accepted package admits `ThrowingSideDisposition` and no object property.
It authorizes the named ontology class but no executable source change.
