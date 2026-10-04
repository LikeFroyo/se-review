# Chain constraints

**C1 (binding).** `coverage_ratio` is a reported column, not a computed one. The only
chain shape this venue admits quotes every member, so the column reads 1.0 by
construction.
**Why:** the column exists so a chain that *stops* quoting every member becomes visible
as a departure from 1.0 rather than being inferred from an absent field.
**What depends on this:** `surface` publishes it and downstream health compares it
against 1.0.
