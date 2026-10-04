# Implicit state — values a function reads without being given them

Audit business logic that reaches outside its parameters for the values it decides on. Same inputs, different answers, and no way to test or replay it.

## What to look for

- **Ambient time:** A business rule reading the current clock, a timestamp, a calendar date, or "today" from inside the logic, so the same inputs produce a different result tomorrow and a replay of a past event cannot reproduce what happened.
- **Ambient randomness:** A decision, identifier, jitter, or sampling path reading a global random source, so the function cannot be run twice and get the same answer.
- **Ambient identity:** A handler obtaining the acting user, tenant, locale, or permissions from a request-scoped global rather than receiving them as a parameter, so the function's behaviour is invisible from its signature.
- **Ambient configuration:** Business logic reading an environment variable, a config file, or a remote flag mid-decision, so the same code path can be enabled and disabled with no version boundary and no review point.
- **Ambient locale or environment:** Formatting, collation, number parsing, or timezone resolution taken from the machine rather than passed in, so a run on one host produces output another host cannot reproduce.
- **Ordering dependence on the caller:** A function that is correct only because some caller initialised module state first, so a second caller gets a different result.
