# Trust Boundaries Sub-Domain Evaluator

Establishes **where untrusted input enters and what is validated there**. This runs first in the
domain because every other security sub-domain states its rules in terms of a boundary, and a rule
referring to a boundary nobody has located cannot be applied.

Work top-down, not bottom-up: enumerate crossings, then walk inward. Correctness review starts at
the code and asks whether it is right; security review starts at the edge and asks what a hostile
actor does.

## Guidelines in this sub-domain

| Area | Focus | File |
|---|---|---|
| **Boundary Inventory** | Untrusted entry points, trust decided by location, validation at the crossing | `guidelines/boundary-inventory.md` |
| **Attack Paths** | Source → boundary → sink; reachability; what is not a finding | `guidelines/attack-path.md` |

## Sub-domain scoring & deduction rules

- **No boundary inventory, and findings claimed anyway:** **CRITICAL** (-25 points). Every other
  finding in the domain is an assertion about a crossing nobody located.
- **Untrusted input reaches a harmful sink with no validation, path shown:** **CRITICAL** (-25).
- **A path with a source and a boundary but no demonstrated sink:** **MAJOR** (-10). A lead, not a
  finding, but worth the reader's attention.
- **A dangerous sink reached only by a privileged actor:** **MINOR** (-3) — defence in depth.
- **Hardening suggestion, no path claimed:** **INFO** (0). Valid and recorded; never graded as a
  vulnerability.
