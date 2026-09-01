# Competency questions

1. What Process or Process Aggregate is the target whose likelihood xBA
   measures for one batted ball?
2. How can a possible Hit outcome be represented without asserting that an
   actual Hit Process occurred when the batter was out?
3. Is the xBA output a CCO Probability Measurement ICE, an Estimate ICE, or a
   more specific intersection whose axioms can be stated with accepted terms?
4. Which versioned Algorithm and model-computation Process produced the
   output, and what Agent evidence would justify typing that Process as an Act
   of Data Transformation?
5. Which comparable-event population, season, tracking method, and conditioning
   inputs define the model version?
6. How is the documented 2019+ sprint-speed input change represented?
7. What does xwOBA measure: an expected weighted value of a possible outcome
   distribution, a statistic about the actual batted-ball event, or another
   target requiring ontology coverage?
8. Must the single/double/triple/home-run probability distribution be retained
   to justify xwOBA, and does the source expose it?
9. Which season-specific wOBA weights are used, and how are those Algorithm
   inputs versioned?
10. Can the model output link to the canonical Batted-Ball Motion Process using
    identity keys without remapping MLB launch measurements or result facts?
11. Can missing, untracked, estimated, and not-applicable values remain
    distinguishable?
12. Can Good At Bat analytics explain model/version provenance without
    treating xBA or xwOBA as the truth of the Plate Appearance?

## Negative tests

- The actual Batted-Ball Motion Process is not a probability or expected value.
- An out does not instantiate an actual Hit Process merely to serve as xBA's
  target.
- A Probability Measurement ICE without a reviewed Process target is not
  promoted as semantically complete.
- xwOBA is not reduced to its lexical field name or a generic quality of the
  batter.
- The provider Algorithm is not assumed timeless across method changes.
- A computation is not typed as an Act merely because an output field exists;
  a causally active Agent at that Process grain must be evidenced.
- Duplicate launch-speed, launch-angle, sprint-speed, and actual-result facts
  are not remapped from Statcast for convenience.
- A Statcast mapping does not read MLB-game RDF; integration occurs only after
  independent promotion.
