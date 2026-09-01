# Source evidence

The accepted reviews at
'Baseball/archive/design-records/mlb-people/' and
'Baseball/archive/design-records/mlb-people-source-contract/' establish that:

- MLB person records expose a bare integer 'weight';
- the same field already occurs in 'gameData.players.*', so it is an
  authoritative duplicate rather than a new assertion kind;
- CCO supplies Mass and Pound Measurement Unit; and
- the endpoint does not identify a measuring act, method, instrument, agent, or
  measurement time.

The source fact supplied for this review is that MLB reports this value in
pounds. That resolves the prior unit blocker. It does not establish when or how
the Person's mass was measured.

No API response was downloaded or retained for this package. Future source
bytes remain transient, and the accepted once-decoded Unicode policy for Person
names is unchanged.

