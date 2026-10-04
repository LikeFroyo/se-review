# Logging & telemetry — structured diagnostics and distributed tracing

Audit operational instrumentation and metric exposure.

## What to look for

- **Unstructured / Free-text logging:** Emitting plain string messages without structured key-value attributes (e.g. JSON format with timestamp and severity).
- **Dropped correlation IDs:** Losing request IDs, trace IDs (`traceparent`), or span IDs when handing off tasks across threads or async pools.
- **Uninstrumented critical paths:** Critical business transactions (e.g. checkout, payment auth) lacking RED signals (Rate, Errors, Duration).
- **Silent error branches:** Exception catch blocks that fail to emit an error log with operational context.
