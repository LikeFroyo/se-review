# Idempotency — safe retries and repeatability keys

Audit state-mutating endpoints and client retry behavior.

## What to look for

- **Missing idempotency keys:** Non-idempotent endpoints (`POST` creates, payment debits) lacking client-supplied idempotency key handling (`Idempotency-Key` header).
- **Mismatched replay execution:** Receiving a repeated idempotency key with conflicting payload parameters and silently executing a second effect instead of returning a conflict error (409/422).
- **Consumed retry streams:** Re-sending a consumed HTTP request stream/reader across retries without rewinding or rebuilding the request payload body.
- **Unbounded key lifetime:** Idempotency key stores lacking an automated TTL expiration window (typically 24–48 hours).
