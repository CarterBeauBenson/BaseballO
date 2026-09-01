# Field inventory and identity policy

| Evidence or entity | Disposition | Modeling consequence |
| --- | --- | --- |
| `MajorLeagueFreeAgentRole` | proposed world-side class | One particular Role per uninterrupted free-agency interval. A later return to free agency creates a new Role individual. |
| Person | accepted identity | The Role inheres in the canonical Person. |
| applicable Baseball Rule / Action Permission | required institutional grounding | The rule permits the relevant Act of Contract Formation; it is not replaced by a provider status literal. |
| Act of Contract Formation | accepted realization Process | May realize the Role when the Person and Baseball Team participate and the applicable rule permits the Act. |
| Gain of Role | required only when beginning evidence exists | The Person participates; the Gain affects the exact Role and occupies its own Temporal Region. |
| Stasis of Role | persistence structure | The Person and exact Role participate; it occupies the continuous interval. It does not realize the Role. |
| Loss of Role | required only when ending evidence exists | The Person participates; the Loss affects the exact Role and occupies its own Temporal Region. |
| team-context Player Role | accepted distinct Role | Its absence does not entail free agency. Signing may precede Gain of a new Player Role. |
| transaction code and description | source evidence ICE | Code-specific structured rules may license world mapping; free text is never parsed to invent a boundary. |
| transaction date | Day-level evidence | Localizes a supported Process no more precisely than the source warrants. |

## Proposed class account

- **Named parent:** Role (`obo:BFO_0000023`).
- **Proposed label:** Major League Free Agent Role.
- **Aristotelian definition:** A Role that inheres in a Person and is realized
  in an Act of Contract Formation with a Baseball Team that is permitted by a
  Baseball Rule governing Major League free agency.
- **Necessary axioms proposed for the later overlay:** inheres in some Person;
  participates in some Stasis of Role; has realization some Act of Contract
  Formation that has participant some Baseball Team and is permitted by some
  Baseball Rule.
- **Identity:** Person plus the evidenced Gain boundary of one uninterrupted
  free-agency interval. For left-censored evidence, use the earliest supported
  Stasis boundary without inventing a Gain.
- **Example:** The particular Role borne by a released Major League player
  during the interval in which MLB rules permit that player to contract with
  an eligible Club.
- **Scope note:** The class does not cover every Person who is willing to play
  baseball, and it does not silently include amateur, Minor League,
  international, or posting-system statuses.

