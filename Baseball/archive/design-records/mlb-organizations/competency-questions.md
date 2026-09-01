# Competency questions

1. Which Baseball League is a Baseball Team affiliated with during a stated
   season?
2. Which Baseball Division is a Baseball Team affiliated with during that
   season?
3. What accepted relations and independently grounded differentiae distinguish
   Baseball League and Baseball Division Organizations without treating a Rule
   ICE as an Organization's continuant part or projecting a temporary team
   affiliation into their identities?
4. Which Baseball Games are occurrent parts of a Baseball Season?
5. What evidence would justify asserting that an Organization participates in
   a Baseball Season, or that an Agent performs an Act of Planning, rather
   than inferring either claim from a nested season record or existing Plan?
6. Which Baseball Season Plan prescribes a Baseball Season and its phases?
7. Which Days are designated by the Plan's Date Identifiers, and what accepted
   relation would connect those Days to the planned boundary of the Temporal
   Interval occupied by a Baseball Season Phase?
8. Can an All-Star, postseason, spring, or exhibition game be distinguished
   from a regular-season game without inferring its kind from team, date, or
   absence of a code?
9. Can team/league/division identities survive name or abbreviation changes?
10. Can the organization source lane be removed without invalidating game RDF
    already promoted from the MLB game lane?
11. Can a Baseball Season remain correctly classified as a Process while its
    Baseball Games contain intentional Baseball Acts and its Season Plan
    prescribes it?

Negative tests:

- `active: false` does not entail that an Organization ceased to exist;
- `firstYearOfPlay` does not entail an Organization's founding year;
- a source `link` is not a baseball-world relation;
- a Baseball Rule ICE is not a continuant part of an Organization merely
  because the Rule governs its competition;
- a current league/division link is not projected backward across every
  historical season;
- the words "during season" in a Mermaid edge do not temporalize an
  unqualified affiliation assertion;
- prescription by a Baseball Season Plan does not entail that a Baseball
  Season or Baseball Season Phase is a Planned Act;
- nesting a season under a league record does not entail that the League
  participates in or is an agent in the Baseball Season;
- existence of a Baseball Season Plan does not by itself establish a
  particular Act of Planning or its agent;
- `numTeams` is not asserted as a timeless property of a League.
