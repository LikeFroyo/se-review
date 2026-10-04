# Accumulator constraints

**C1 (binding).** Exactly one thread ever calls `apply()`. It is the pipeline's single
consumer thread, started once by `pump`.
**Why:** one writer cannot race itself; a lock would imply writers that do not exist.
**What depends on this:** `_frozen` and `_pending` are single-writer accumulators whose
values are read only after the pipeline drains.
