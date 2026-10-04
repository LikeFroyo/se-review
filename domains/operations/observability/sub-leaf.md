# Observability Sub-Domain Evaluator

Evaluates structured logging, correlation tracking, telemetry exposure, secret redaction, and audit records.

## Guidelines in this sub-domain

| Area | Focus | File |
|---|---|---|
| **Logging & Telemetry** | Structured JSON logging, correlation IDs, trace propagation | `guidelines/logging-telemetry.md` |
| **Log Hygiene** | Secret and PII redaction in logs, metric cardinality limits | `guidelines/log-hygiene.md` |
| **Audit Trail** | Append-only records for access, money, and data-ownership changes | `guidelines/audit-trail.md` |

## Sub-domain scoring & deduction rules
- Plaintext secrets or credentials output in logs: **CRITICAL** (-25 points).
- Silent failure path emitting zero logs or telemetry: **CRITICAL** or **MAJOR** (-25 to -10 points).
- Unstructured free-text logs or missing correlation ID: **MINOR** (-3 points).
- High cardinality metric labels: **MAJOR** (-10 points).
- No audit record for an access, money, or data-ownership change: **MAJOR** (-10 points).
