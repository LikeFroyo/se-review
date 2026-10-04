# Type & Contracts Sub-Domain Evaluator

Evaluates assertions the type system should be making: unchecked casts, suppressions, and boundaries where a declared contract is not enforced.

## Guidelines in this sub-domain

| Area | Focus | File |
|---|---|---|
| **Type & Contract Assertions** | Unchecked casts, unjustified suppressions, unvalidated parsed input, contract drift | `guidelines/type-and-contract-assertions.md` |

## Sub-domain scoring & deduction rules
- Blanket cast or trusted-parsed-input used on a security- or money-relevant path with no validation: **CRITICAL** (-25 points).
- Type suppression with no justification, or dynamic lookup used as a typed value: **MAJOR** (-10 points).
- Default masking a contract-required field, or validation applied on only one construction path: **MAJOR** (-10 points).
- Contract drift between a declared schema and the payload actually constructed: **MAJOR** (-10 points).
- A well-justified cast at a genuinely dynamic boundary: **INFO** (0 points).

## Scope boundary

- Missing or wrong *type hints* with no consequence is linter work and is not graded here. A cast is graded only where it suppresses a real check.
- A serializer that correctly narrows or validates is the control, not the defect; report the path that skips it.
- Anything here that is a conventional defect (a security bypass, a data-loss bug) is graded at its normal severity **and** cross-referenced to the owning sub-domain, so it is counted once at the higher grade.
