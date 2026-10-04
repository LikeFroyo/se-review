# Layer constraints

**C1 (binding).** The set-level view reads **exactly three** names from the per-contract
layer: the parity fit, the smile solve, and the log-ratio helper. Every other set-level
quantity is computed inside the set layer from published values.
**Why:** each additional reach couples the set's lifecycle to the per-contract layer's
internals.
