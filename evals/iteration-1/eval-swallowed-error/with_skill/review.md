# Review: evals/fixtures/swallowed_error.py

`3 findings · C:2 M:1 m:0 i:0 · Mean 85/100 · Final Grade F`
Covered: 1/1 in-scope files · Scope: focused on `evals/fixtures/swallowed_error.py` · Not examined: 0 — none
Domain Scores: Correctness: 75/100 · Operations: 65/100 · Maintainability: 100/100 · Leanness: 100/100 · Interoperability: 100/100
Gated by: **Critical finding** (any Critical caps the grade at F); weakest domain: Operations (65, Grade D)

## Findings

### [CRITICAL] Swallowed exception masks payment-charging failures and orphans partial order state
- **Domain:** Correctness (A1)
- **Verified by:** `RAN` — executed `process_fulfillment` with a stub gateway/account service: DB ran `payment_status = 'PAID'`, `account_service.provision` raised `TimeoutError`, function returned `False`, and **no traceback or log record was emitted**.
- **Evidence:** `evals/fixtures/swallowed_error.py:18` — `except Exception:` followed by `return False` (lines 18–23), discarding the exception type, message, and traceback.
- **Failure scenario:** Customer is charged and row marked `PAID` (line 11–12), then provisioning fails; the handler swallows the error, records no `fulfillment_status`, issues no refund, and emits no log. The order is permanently stuck in a charged-but-not-fulfilled state, and on-call has zero signal — the comment on lines 19–22 admits this but does not resolve it.
- **Fix:** Catch specific exceptions, log with `logger.exception(...)` (the `logger` on line 4 is currently unused), compensate (refund or mark `FULFILLMENT_FAILED` and alert), and/or re-raise. Scope: module (this function and its callers' error contract).
- **Trade-off:** Callers must now handle raised exceptions / richer failure enum; adds a compensation path (refund call) whose own failure needs a retry/DLQ story.

### [CRITICAL] Silent failure path emits zero logs or telemetry
- **Domain:** Operations (C4)
- **Verified by:** `RAN` — same execution above: stderr/stdout carried no log record from the failure.
- **Evidence:** `evals/fixtures/swallowed_error.py:18-23` — `except Exception:` block contains only a comment and `return False`; `logger` (line 4) is never called.
- **Failure scenario:** Every payment, DB, and network failure routes through this handler; none is observable. Monitoring cannot distinguish "no orders" from "100% failure," so an outage persists until customers complain.
- **Fix:** `logger.exception("fulfillment failed for %s", order_id)` in the handler plus a metric/audit event. Scope: local.
- **Trade-off:** Log volume and PII hygiene (don't log full card/payment payloads) — needs redaction discipline, negligible latency.

### [MAJOR] Multi-step charge→provision sequence has no transaction boundary, so partial commits are the norm on failure
- **Domain:** Correctness (A1) / Operations (C7)
- **Verified by:** `DERIVED` — trace chain: line 12 commits `PAID` before line 15's `provision` can fail; each `db_conn.execute` is an independent statement with no surrounding transaction/rollback, and `provision` (line 15) is not atomic with the DB writes.
- **Evidence:** `evals/fixtures/swallowed_error.py:9-17` — Step 1 charge + UPDATE, Step 2 provision + UPDATE, with no `BEGIN`/`COMMIT`/`ROLLBACK` and no saga/outbox compensation.
- **Failure scenario:** Crash or exception between line 12 and line 16 leaves `payment_status='PAID'` with stale `fulfillment_status`; there is no recovery reconciliation path anywhere in the file.
- **Fix:** Wrap DB writes in one transaction and make the payment→provision flow a saga with explicit compensating action, or write an outbox row in the same transaction as the charge record. Scope: module.
- **Trade-off:** Longer DB transaction hold time or an outbox dispatcher's operational burden; compensation logic adds code paths that must themselves be tested.

## Aligns well
- `evals/fixtures/swallowed_error.py:4` — a module-level `logger` is provisioned, ready for the fix above (B4/C4 intent present, unwired).
- Clear docstring on `process_fulfillment` stating the success/failure contract (B4).