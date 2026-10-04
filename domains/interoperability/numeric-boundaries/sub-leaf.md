# Numeric Boundaries Sub-Domain Evaluator

Audits numbers that change representation between two systems: floats becoming money, integers losing precision, units changing scale.

## Guidelines in this sub-domain

| Area | Focus | File |
|---|---|---|
| **Representation** | Float money, fixed vs decimal, integer width, serialised precision | `guidelines/representation.md` |
| **Conversion** | Unit scale, rounding mode, cumulative rounding, precision loss in transit | `guidelines/conversion.md` |

## Sub-domain scoring & deduction rules
- Money held or transported as a binary float, producing a total that is wrong by cents on every order: **CRITICAL** (-25 points).
- A unit conversion or a scale change with the wrong factor, or applied twice: **CRITICAL** (-25 points).
- Identifier or sequence number exceeding the receiving field's integer width, silently wrapping or truncating: **CRITICAL** (-25 points).
- Serialisation that drops trailing zeros or a stated precision, so a value round-trips to a different number: **MAJOR** (-10 points).
- Cumulative rounding across a conversion chain, drifting from the original: **MAJOR** (-10 points).
- Rounding mode differing from the other side's stated convention: **MAJOR** (-10 points).
- Both sides using a declared fixed-precision decimal type: **INFO** (0 points).

## Scope boundary

- **A name that misstates a local unit is `maintainability/clarity`** (`units-and-magnitude.md`). This sub-domain begins where the value is *converted or transported* and the two sides disagree.
- Float arithmetic inside a single process with no boundary, and no correctness consequence beyond the arithmetic itself, is `correctness/logic`.
- Do not restate the security sub-domain's cryptography rules; a hash or a signature is not a numeric boundary.
