# Sensitivity constraints

**C1 (binding).** Two vega readings exist and are not duplicates. `vega_from_total` and
`vega_from_legs` are two estimators of the same sensitivity from different inputs, and
they coincide only on the contract class this venue lists.
**Why:** the second estimator is the cross-check on the first; collapsing them deletes
the check.
**What depends on this:** the divergence on non-listed classes is the alarm that the
venue listed something it should not have.
