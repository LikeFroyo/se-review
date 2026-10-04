# Timeouts & circuit breakers — bounding latency and isolating failures

Audit network deadlines, connection pooling, and fault isolation.

## What to look for

- **Missing RPC / HTTP timeouts:** Outgoing network calls without explicit connect and read timeouts (defaulting to system-level TCP hang of minutes).
- **Missing deadline propagation:** Creating fresh full timeout budgets at each downstream hop rather than propagating remaining deadline context.
- **Missing circuit breakers:** Calling a hard downstream dependency repeatedly when it is failing 100% of health probes.
- **Unbounded thread/connection pools:** Creating a new thread or database connection per request without pool limits and queue bounds.
