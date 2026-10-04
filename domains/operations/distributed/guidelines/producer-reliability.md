# Producer reliability — dual writes and the transactional outbox

Audit the producer side: every business-state write paired with an event publish must be atomic.

## What to look for

- **Dual write without a shared atomic unit:** Committing business state to the database and publishing the event to the broker as two separate steps (publish-after-commit, or publish-before-commit).
- **Publish-after-commit with a crash window:** `db.commit()` followed by `broker.publish()` — a crash between the two silently loses the event.
- **Publish-before-commit with a rollback window:** `broker.publish()` followed by `db.commit()` — a rollback emits a ghost event for state that never existed.
- **Missing outbox/CDC relay:** No outbox table written in the same transaction as the business state, and no change-data-capture relay publishing from it.
- **Unordered publish:** Events for the same aggregate published in an order different from their transactions (missing sequence or timestamp ordering from the relay).

## Verification

- The event row (or CDC-captured change) commits in the same transaction as the business state — one atomic unit, never two steps.
- A separate relay (poller or log tailer) delivers outbox rows to the broker and marks them published; relay retries make delivery at-least-once, so consumers must still deduplicate.
- Events per aggregate carry ordering (sequence number or timestamp) preserved by the relay.
