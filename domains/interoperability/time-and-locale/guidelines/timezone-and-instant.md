# Timezone & instant — when is this, exactly

Audit every timestamp that crosses a boundary, for whether it denotes an instant or a wall-clock reading.

## What to look for

- **Naive timestamp persisted:** A datetime written without a zone and read as local on the other side, so the instant shifts by the reader's offset — a nightly job runs at a different hour per host, and a deadline is met or missed depending on where the reader runs.
- **Local time treated as an instant:** A wall-clock value from a form, a terminal, or an operating-system schedule stored as though it were UTC, so every downstream calculation is offset by the difference.
- **DST gap and fold:** A scheduled or recurring time falling in the spring-forward gap (the local time does not exist) or the autumn fold (the local time occurs twice), so an action is skipped or executed twice.
- **Fixed offset instead of a zone:** A `+01:00` applied permanently where a zone identifier is required, so the offset is wrong for half the year and the code has no way to learn the right one.
- **Clock skew assumed away:** Ordering decided by a timestamp from a machine whose clock is not synchronised, so events commit in an order their producers did not intend and last-writer-wins picks the wrong row.
- **Elapsed time computed across a DST boundary:** A duration derived from two wall-clock values that span a transition, so a 24-hour window is 23 or 25 hours long and a daily job runs twice or not at all.
- **Rounding to the wrong boundary:** A timestamp truncated to the day, the hour, or the minute in one timezone and compared against a value truncated in another, so two events in the same period land in different ones.
