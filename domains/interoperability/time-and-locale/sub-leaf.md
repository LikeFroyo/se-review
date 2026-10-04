# Time & Locale Sub-Domain Evaluator

Audits timestamps, dates, calendars, and orderings that change meaning between two systems, two regions, or two processes.

## Guidelines in this sub-domain

| Area | Focus | File |
|---|---|---|
| **Timezone & Instant** | Naive vs aware datetimes, DST gaps and folds, local-time persistence, clock skew | `guidelines/timezone-and-instant.md` |
| **Locale & Ordering** | Locale-dependent parsing and formatting, week rules, collation, currency and number formats | `guidelines/locale-and-ordering.md` |

## Sub-domain scoring & deduction rules
- A timestamp persisted without a zone and read as local, shifting a scheduled or dated action by hours: **CRITICAL** (-25 points).
- A DST transition dropping or repeating a scheduled action, or a clock rollback moving an interval backwards: **MAJOR** (-10 points).
- Locale-dependent parsing of a date or number the other side formatted in a fixed format: **MAJOR** (-10 points).
- Ordering by a string form of a date, or a collation that sorts differently from the database: **MAJOR** (-10 points).
- Week-number or day-of-week convention differing between the two sides: **MAJOR** (-10 points).
- Both sides explicitly in UTC with an agreed format: **INFO** (0 points).

## Scope boundary

- A clock read inside a business rule is `maintainability/evolvability` (implicit state). Report here only where the *value* means something different on the other side.
- Arithmetic and comparison errors within one process, with no boundary, are `correctness/logic`.
