# Representation — the number is not the same number

Audit the *type* a number is carried in, on each side of every boundary.

## What to look for

- **Money as a binary float:** A price, total, tax, or balance held in a single- or double-precision float and written to a wire or a ledger, so 0.1 + 0.2 is not 0.3 and a sum of many rows does not equal the total of the same rows.
- **Decimal string to float and back:** A value serialised from a decimal type, parsed as a float, and re-serialised, so the value differs from the original by a representation error that nobody notices because both print the same.
- **Integer too narrow for the receiving field:** A 64-bit identifier, a nanosecond timestamp, or a sequence number written into a 32-bit column, an unsigned field, or a JavaScript number, so it wraps, goes negative, or loses precision silently.
- **Rounding mode not stated:** A conversion or a reduction that rounds half-up on one side and half-even on the other, so the two disagree by one unit on every tie and the totals never reconcile.
- **Trailing precision dropped in transit:** A value serialised without a scale or a fixed number of decimal places, so a consumer reads 1.5 as 1 and a rate as 0.
- **Truncation where rounding was intended:** A cast or a scale-down that discards the remainder instead of rounding, so a total is always short and the loss is systematic rather than random.
- **Percentage or ratio stored as a rounded integer:** A rate kept in basis points or whole percent with the remainder discarded, so the effective rate differs from the configured one on every calculation.
