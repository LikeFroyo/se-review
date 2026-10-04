# Trust boundaries — the primitive every other security rule references

Audit where untrusted input enters, what is validated there, and what the code
assumes downstream. This is the first sub-domain because everything else in the
domain is stated in terms of it: an access-control defect is a boundary that
failed to hold, an injection defect is a boundary that was never drawn, and a
crypto defect is usually a boundary between a secret and a log.

**Nothing in this domain can be graded without one.** A rule that says "validate
at the boundary" is unusable unless you can name the boundary. A rule that says
"an unescaped value reaches a query" is a finding; the same sentence without a
named source, boundary, and sink is a suspicion.

## The inventory

- **No boundary inventory exists:** Nothing enumerates where untrusted data
  enters. Every other finding in this domain is then an assertion about a
  crossing nobody has located.
- **An entry point classified by nothing:** A route, message consumer, file
  drop, or scheduled input recorded without saying whether its data is attacker
  controlled, and therefore without saying what must be validated.
- **Trust decided by location:** Data treated as trusted because it arrived over
  a loopback, from an internal network, from a queue, or from another service —
  where any of those may be reachable by a party the system does not control.
- **A boundary that moved without moving its validation:** Validation sits at the
  old crossing after the caller moved, the protocol changed, or the field became
  writable by a new actor.
- **No owner for a boundary:** A crossing exists that no module claims, so no
  test covers it and no change is judged against it.

## Validation at the crossing

- **Validation by type only:** A value is checked for shape or type and then
  treated as safe, so a well-formed dangerous value passes.
- **Validation at the wrong side:** The check lives in the caller, the
  consumer, or the storage layer, so a second caller reaches the sink unchecked.
- **Allow-list after the fact:** Dangerous characters are removed rather than
  permitted ones required, so a representation the filter did not anticipate
  survives it.
- **Validation that can be skipped:** An early return, a cache hit, a
  feature-flag branch, or a test-only path reaches the sink without the check.
- **No negative check:** Nothing confirms the crossing rejects what it should.
  Absence of an error check is a silence claim, never evidence that the input
  was handled.

## Trust assumed downstream

- **Sanitised once, trusted everywhere:** A value is escaped or encoded at the
  boundary and every later use assumes it, so a second sink gets an escaped value
  in a context that needed a different treatment.
- **Provenance lost in transit:** Data crosses a boundary — into a queue, a
  cache, a log, a table, another process — and nothing records whether it had
  been validated, so the receiving side cannot know what it is holding.
- **A boundary assumed from a name:** A field called `internal`, a path under
  `trusted/`, or a header assumed authenticated, treated as proof of origin.
- **Authentication standing in for authorisation:** The caller is known, so the
  action is permitted, with no check of whether *this* caller may do *this* to
  *this* record.