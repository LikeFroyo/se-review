Reviewing the field-name fixture in its self-contained workspace.
Found the reported defects in the fixture — now checking the bundled skill rules to complete the review.
I've mapped the wire-format faults to the rubric — now verifying them with a quick reproduction.
# Review: evals/fixtures/field_name_mismatch.py

`4 findings · C:1 M:2 m:1 i:0 · Mean 76/100 · Final Grade F`
Covered: 1/1 files · Scope: focused on: evals/fixtures/field_name_mismatch.py · Not examined: 0 — none
Paths: 0 · Unmapped: 0 — no security crossings in scope
Unclassified: 0 findings fit no axis code
Domain Scores: Interoperability: 52/100 · Correctness: 100/100
Gated by: `customer_id vs customerId silent misattribution` — **always printed.**

## Findings

### [CRITICAL] Producer `customer_id` consumed as `customerId`, always absent
- **Domain:** Interoperability (D4)
- **Verified by:** RAN — executed `handle_order_event` replica with producer-shaped payload `{"customer_id":"c42",...}`; observed `{'customer':'unknown',...}`; repeated with `c99` — same `unknown`.
- **Evidence:** `field_name_mismatch.py:39` — `customer = event.get("customerId", "unknown")` vs producer schema `field_name_mismatch.py:9` — `"customer_id": "string"`. No writer ever emits `customerId`; the `.get()` default always fires.
- **Failure scenario:** Every order event is attributed to synthetic customer `unknown`. Per-customer totals, counts, and reporting are wrong for the whole dataset with no error. Silent identity corruption.
- **Fix:** Align at the boundary (scope: boundary) — rename one side and dual-read during migration, e.g. `event.get("customer_id", event.get("customerId", "unknown"))`, then remove the legacy spelling once the queue drains.
- **Trade-off:** Dual-read costs one extra lookup per event and temporary ambiguity; a hard rename without it drops or misroutes in-flight events.

### [MAJOR] Strict consumer rejects producer's additive `status` values, backing up queue
- **Domain:** Interoperability (D4)
- **Verified by:** RAN — `status="refunded"` / `"disputed"` against `strict_handler` logic `field_name_mismatch.py:66-67` raises `ValueError("unknown status")`; same inputs against `handle_order_event` silently coerce (see next finding).
- **Evidence:** `field_name_mismatch.py:7-21` — `PRODUCER_SCHEMA` allows `enum[placed, paid, shipped, cancelled, refunded, disputed]` while `CONSUMER_EXPECTS` allows only `enum[placed, paid, shipped, cancelled]`; `field_name_mismatch.py:64-67` — `if set(event) - set(PRODUCER_SCHEMA): raise ...; if event["status"] not in CONSUMER_EXPECTS["status"]: raise ...`
- **Failure scenario:** The moment the producer emits `refunded` or `disputed`, every such message is unprocessable. Depending on retry/DLQ config this stalls the `orders.v1` consumer or fills the DLQ; no forward progress on the new statuses.
- **Fix:** Tolerant reader at the boundary (scope: boundary) — ignore unknown fields, treat unknown enum as `unknown`/DLQ with metric and alert rather than `raise`, and add a version/compatibility window for enum widening. Cross-references Correctness (A4) enum-widening; no separate Correctness deduction.
- **Trade-off:** Tolerance costs explicit unknown-branch code plus monitoring; it trades fail-fast visibility for availability — genuine corruption is detected later, via the DLQ/metric instead of the exception.

### [MAJOR] Unknown `status` silently coerced to `placed`
- **Domain:** Interoperability (D4)
- **Verified by:** RAN — `status="refunded"` and `"disputed"` both returned `"status":"placed"` from `handle_order_event` replica.
- **Evidence:** `field_name_mismatch.py:43-45` — `status = event.get("status"); if status not in ("placed", "paid", "shipped", "cancelled"): status = "placed"`
- **Failure scenario:** Refunds and disputes are counted as new `placed` orders. Revenue, fulfilment, and dispute metrics are silently corrupted; downstream state machine takes the wrong branch with no signal.
- **Fix:** Fail explicitly at the seam (scope: module) — map unknown to an `unknown` sentinel, route to DLQ, or reject with a logged error instead of defaulting to a valid business state.
- **Trade-off:** Explicit handling adds a branch and an operational queue/metric to own; it costs code and triage against eliminating silent state corruption.

### [MINOR] Absent `totalCents` coerced to `0`, indistinguishable from real zero
- **Domain:** Interoperability (D4)
- **Verified by:** RAN — payload with no `totalCents` returned `"total": 0`, identical to a genuine zero-total order.
- **Evidence:** `field_name_mismatch.py:40-42` — `total = event.get("totalCents"); if not total: total = 0`
- **Fix:** Distinguish absent from zero (scope: local) — `if total is None: ...` with required-field validation instead of falsiness.

## Aligns well
- `negotiate_format` (`field_name_mismatch.py:71-79`) provides a pinned default (`json-v1`) when `Accept` is absent, avoiding the no-default negotiation hazard (D4).
- `shippedAt` nullability agrees on both sides (`nullable timestamp` in both schemas), and both schemas are recorded in code rather than only in prose.