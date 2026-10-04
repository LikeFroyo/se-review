# Logic & edge cases — boundary analysis and numeric safety

Audit whether the code executes correctly across boundary inputs, types, and defaults.

## What to look for

- **Boundary off-by-one:** Mistakes on `<` vs `<=`, `0`- vs `1`-indexed slices, and range end bounds.
- **Empty / Null states:** None, null, empty collections, or empty strings causing unhandled exceptions.
- **Wrong default values:** Defaults that silently alter previous behavior for existing callers.
- **Floating-point precision:** Direct equality checks (`==`) on floats or using binary floats for financial transactions instead of fixed-point decimals.
- **Date, time & timezone hazards:** Treating naive timestamps as UTC, ignoring daylight savings shifts, or assuming monotonic system clocks.
