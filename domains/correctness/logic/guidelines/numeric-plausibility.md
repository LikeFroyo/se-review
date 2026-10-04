# Numeric plausibility — computed values that are finite and wrong

Audit every derived quantity for whether it could be *right*, not merely whether it is a number.
A value that is finite, correctly typed, and off by thirty orders of magnitude passes every
representation check and produces a confidently wrong answer.

## Denominators that decay

- **Ratio over a derived denominator:** A quotient whose denominator is a sum, count, volume, or moving total that approaches zero, with no guard applied to the result before it is used.
- **Guard present but bypassed on one path:** The denominator is checked on the main path and read unchecked from a cache hit, an early return, a fallback branch, or a configuration path.
- **Denominator checked but numerator not:** The result is finite so it passes the guard, while the inputs producing it are individually nonsensical.

## Values that are plausible in form and wrong in fact

- **Statistic trusted because it is finite:** A computed aggregate is accepted with no range check, no comparison against a known bound, and no reference value to compare against.
- **Non-finite or sign-violating values absorbed:** A non-finite result, a negative where only non-negative is meaningful, or a negative elapsed duration flows into an accumulator instead of being rejected at the boundary.
- **Threshold fired on a raw magnitude:** A decision compares a computed value against a constant with no check that the value is on the scale the constant was chosen for.
- **Stale input rewinds a marker:** A zero-stamped, out-of-order, or stale record moves a previous-value marker backwards, so the resulting difference is consumed as a fresh positive increment.

## Reporting

- **No plausibility band at consumption:** A derived value feeds a decision, a limit, or an alert with no sanity band at the point of use, so an impossible value is indistinguishable from a normal one.
- **Divergence between two computations unasserted:** The same quantity is computed in more than one place and nothing asserts the two agree, so a drift is invisible until a human compares them by hand.
