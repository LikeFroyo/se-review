# Coercion & wrong-typed values — truthiness and silent conversion

Audit every boundary where a value arrives as one type and is used as another. Nothing here raises; every item produces a wrong answer that looks correct.

## What to look for

- **String used as a boolean:** A condition testing a configuration or request value for truthiness where the value came from an environment variable, a query string, a JSON field, or a form — so `"false"`, `"0"`, `"no"`, and `"off"` all enable the branch they were meant to disable.
- **Boolean used as a number:** Arithmetic on a flag or a count read as a string, so `"12"` silently becomes `12` while `""` and `"abc"` become `0`.
- **Numeric string compared to a number:** A loose equality between a request parameter and a numeric field, so a non-numeric value compares equal to a numeric zero.
- **Empty string conflated with absent:** A check for presence testing truthiness, so a supplied-but-empty field is treated as not supplied and the default is applied silently.
- **Identifier coerced to number:** An identifier, account number, or zip code passed through an integer conversion, so a leading zero, a letter, or an over-long numeric string is truncated, rejected, or silently mapped to another record.
- **Enum from an unvalidated string:** A state or status taken from input and compared against known values, where an unrecognised value falls through to a default branch rather than being rejected.
- **Unvalidated boundary value used directly:** A header, environment variable, or config value consumed without parsing or range checking, so a typo becomes a wrong default rather than a startup failure.
