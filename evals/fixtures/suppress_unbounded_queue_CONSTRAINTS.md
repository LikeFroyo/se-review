# Intake constraints

**C1 (binding).** The ingress queue is unbounded. It is never capped, never sheds,
never drops, and no producer is throttled.
**Why:** a frame once accepted is an exchange event and is unrecoverable; a cap
converts consumer latency into silent data loss.
**What depends on this:** every accepted frame is eventually delivered exactly once,
and no re-request path exists to recover a discarded one.

**C2 (binding).** The backlog is *measured*, never policed. `enqueued`, `peak_backlog`
and the live depth are the operator's only liveness signal.
