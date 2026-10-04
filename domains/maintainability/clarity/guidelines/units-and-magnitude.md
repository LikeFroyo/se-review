# Units & magnitude — names that misstate scale

Audit every numeric quantity whose name carries a unit, a scale, or a domain magnitude. A wrong magnitude is a silent numerical error, not a typo.

## What to look for

- **Unit lies in the name:** `amount_cents` holding a whole-unit float, `timeout_ms` passed seconds, `size_kb` holding bytes. The name is the only place the unit is recorded, so a mismatch is invisible to every reader and to the type system.
- **Bare number where the unit is the meaning:** A literal with no unit in the name and no type carrying one — `rate * 0.0825`, `total / 1000` — where the multiplier is only recoverable from surrounding prose.
- **Scale change in a conversion step:** A divide or multiply by 1000, 100, 60, or 1024 with no value type at the boundary, so a rounding or a unit error propagates silently.
- **Rounding at a conversion:** A conversion that rounds without a declared mode, so a value converted repeatedly drifts from its original.
- **Unit-free persistence:** A magnitude written to a column, key, queue message, or file with no unit recorded alongside it, so a future reader cannot tell which scale the stored number is in.
- **Mixed units in one expression:** Two quantities with the same name in different modules measured in different units, combined or compared as though they were the same.
