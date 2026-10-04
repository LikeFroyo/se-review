# Resilience Sub-Domain Evaluator

Evaluates retry policies, exponential backoff, jitter, timeouts, circuit breakers, health signalling, and shutdown.

## Guidelines in this sub-domain

| Area | Focus | File |
|---|---|---|
| **Retries & Backoff** | Immediate retries, missing jitter, retry amplification | `guidelines/retries-backoff.md` |
| **Timeouts & Breakers** | Missing timeouts, deadline propagation, circuit breakers | `guidelines/timeouts-breakers.md` |
| **Process Lifecycle** | Liveness vs readiness, dependency-coupled health, graceful shutdown | `guidelines/process-lifecycle.md` |
| **Work-Unit Retry Safety** | The retried unit that applies its side effect twice | `guidelines/work-unit-retry-safety.md` |

## Sub-domain scoring & deduction rules
- Immediate retry loop hammering failing downstream (thundering herd): **MAJOR** (-10 points).
- Unbounded network call with no timeout on critical path: **MAJOR** (-10 points).
- Retrying non-idempotent operation without key: **CRITICAL** (-25 points).
- Liveness check coupled to a dependency (fleet restart storm): **CRITICAL** (-25 points).
- No graceful shutdown, or a grace period shorter than the longest request: **MAJOR** (-10 points).
