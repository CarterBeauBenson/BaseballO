# Competency questions

1. Which Person is the subject of the generic Descriptive Information Content
   Entity corresponding to one MLB personnel row?
2. Which precise process or processes does that record describe?
3. Which Baseball Teams are agents in a Baseball Personnel Trade Act?
4. Which Persons participate in one multi-person trade?
5. Which team-scoped Occupation Roles begin or end through a Gain of Role or
   Loss of Role, and what Stasis of Role supplies each effective interval?
6. Which Act of Contract Formation or Act of Employment supports a signing?
7. Which Uniform Number Assignment Act assigned a Code Identifier to a
   team-scoped Player Role?
8. Which dates designate the record date, effective date, and resolution date,
   and which process boundary does each date identify?
9. Which generic Nominal Measurement ICE and provider Reference System instance
   classify a record when its world-side semantics remain unresolved?
10. Can one provider transaction ID denote an overall trade while several row
    records describe different participating Persons?

Negative tests:

- a Death is not a Planned Act or transaction act;
- `fromTeam` and `toTeam` are optional and their absence does not create an
  unknown Team individual;
- `Status Change` does not license an unspecified world-side process;
- a release does not entail death or retirement;
- a number change is not a change to the Person's identity;
- an organizational context or roster label does not by itself license a new
  membership-role universal;
- a repeated trade ID does not collapse multiple Persons into one row or mint
  multiple overall trade acts.
