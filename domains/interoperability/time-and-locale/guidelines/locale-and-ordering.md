# Locale & ordering — the format that depends on where the server is

Audit anything whose *representation* depends on the environment, and anything whose *order* does.

## What to look for

- **Locale-dependent formatting of a wire value:** A number, date, or currency rendered with the host's locale and sent to a consumer that parses a fixed format, so `1,5` becomes `15` and a price is wrong by a thousandfold.
- **Locale-dependent parsing of a fixed-format value:** A parser that accepts the host's own formats, so a document written as `2026-01-15` is unparseable on a host that expects day-first order, and a US-format string is silently misread as a different date.
- **Ambiguous numeric dates:** A date written `03/04/2026` crossing a boundary, where one side means 3 April and the other 4 March, and no side knows which.
- **Week-number convention mismatch:** ISO weeks starting Monday with the first week containing 4 January, versus a locale's Sunday-start and week-1 rule, so a weekly report covers a different span on each side and two adjacent periods overlap.
- **Collation-dependent ordering:** A `sort`, an index, or a comparison using a locale collation, against a database ordering byte-wise, so the application and the database disagree about which record is first.
- **Case folding on one side only:** A lookup or a deduplication that is case-insensitive in the application and case-sensitive in the index, so the same key matches in one path and misses in the other.
- **Currency or decimal separator assumed:** A value carried without its currency and its precision, so a value written in a two-decimal currency is consumed as a unit price and read as a fraction of it.
- **Non-Gregorian or non-Arabic numerals assumed:** A parser that accepts only ASCII digits on one side while the other emits localised digits, so a valid input is rejected or read as zero.
