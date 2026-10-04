# Attack paths — what makes a security finding a finding

Audit every claimed vulnerability for whether a path exists from something an
attacker controls to something that causes harm. This is the domain's proof
obligation and it differs from every other domain: a correctness defect is
established by a wrong output or a failing input, while a security defect is
established only by a **path**. Without one it is a hypothesis, and the grade
reflects that.

## The three parts

A security finding above Info names all three. Two is a lead. One is a note.

| Part | What it is | Missing it means |
|---|---|---|
| **Source** | The specific input an attacker controls, and where it enters | No entry point, no reachability — the code may be dead to an attacker |
| **Boundary** | The crossing where it should have been rejected, and was not | No defect: the value may be handled safely further in |
| **Sink** | The operation that causes harm, reached with the value intact | Harm is theoretical; the operation may already be safe by construction |

- **Source named only by category:** "User input" or "the request body" is not a
  source. Which field, reaching which entry point, under whose control.
- **Boundary asserted rather than shown:** "Not validated" without the crossing
  where validation belongs, and without what would have been checked.
- **Sink named only as a class:** "A query" or "a shell" without the operation
  and the value that reaches it.
- **A path through code that cannot run:** The route is never registered, the
  branch is dead, the caller passes only constants. Reachability is part of the
  path and omitting it inflates the grade.
- **Reachability asserted from a name:** A handler named `admin` or a function
  taking an `internal` argument treated as proof that only trusted callers reach
  it, with nothing establishing who those callers are.

## Asymmetry

Security is not averageable, and a finding must say which of these it is.

- **Gated on reachability from an untrusted source.** Anything below is a lead,
  not a finding, whatever its shape.
- **Gated on privilege.** An issue reachable only by an already-privileged
  actor is a defence-in-depth note, not a vulnerability, and is Info unless it
  crosses a boundary that separates two different privilege levels.
- **Named against the actor who benefits.** "An attacker can" is not a severity
  argument. Who, and what they gain, decides whether harm is plausible.
- **Never netted against a clean review.** A missed authorisation defect is not
  offset by a correct review elsewhere, so security results are reported as a
  set of unresolved paths rather than folded into a domain score that a good
  average can hide.

## What is not a finding

- **A dangerous API used safely.** The sink exists and the value reaching it is
  constrained, parameterised, or bounded. Report the constraint's absence only
  if something can actually remove it.
- **A hardening suggestion.** Better isolation, an extra check, a defence that
  would reduce blast radius. Valid; Info.
- **A version with a known advisory and no reachable path from this code.** An
  inventory item, not a finding, until a path is shown.
- **A secret in a test fixture or a committed example.** Worth saying once, as a
  repository observation, not graded per occurrence.