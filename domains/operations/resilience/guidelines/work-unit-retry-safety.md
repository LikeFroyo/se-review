# Work-unit retry safety — the unit that runs twice

Audit every unit of work that can be retried, whether or not it arrived as a message. Duplicate
delivery and multi-service compensation are covered elsewhere; this covers the single unit that
re-executes after a timeout, a crash, or a scheduler re-run.

- **Accumulating side effect on a retried unit:** The unit adds to a total, appends to a log, or increments a counter rather than setting absolute state, so a second execution applies the effect twice.
- **Partial completion with no record:** The unit fails partway through its own steps, leaving side effects with no durable record of which completed, so a retry cannot tell what is already done.
- **Retry restarts the batch:** A failure re-runs every item in the batch rather than the one that failed, so completed work is repeated.
- **Resume from the beginning:** Recovery begins at the start because no cursor, offset, or position is persisted, so each restart re-does everything before it.
- **Completion indistinguishable from interruption:** Shutdown, timeout, or eviction cannot tell a finished unit from one in flight, so finished work is redelivered and interrupted work is half-written.
- **Reported success before the effect is durable:** The unit acknowledges before its side effect is committed, so a crash in between is invisible to the retry and the work is silently lost.
- **Retry budget with no quarantine destination:** A unit that can never succeed consumes the whole budget with nowhere to go, so the queue stops draining.
