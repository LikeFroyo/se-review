Reviewing the file and run directory.
Found the complexity hotspot — now checking the eval context.
This looks like a full review — discovering the relevant domains.
I've got the domain overview — now digging into the specific checklists.
The structure confirms the smells — now verifying the metrics.
# Review: `evals/fixtures/complexity.py` (`process_order_checkout`)

`5 findings · C:0 M:2 m:3 i:0 · Mean 95/100 · Final Grade C`
Covered: 1/1 files · Scope: focused on: evals/fixtures/complexity.py · Not examined: 0 — none
Paths: 0 · Unmapped: 0 — no attacker-reachable sink; inputs are pricing/inventory data, only sinks are arithmetic, dict return, and list append
Unclassified: 0 findings fit no axis code
Domain Scores: Maintainability: 77/100 · Correctness: 97/100 · Leanness: 100/100 · Security: 100/100 · Operations: 97/100 · Interoperability: 100/100
Gated by: weakest domain: Maintainability — **always printed.**

Serial review (1 file, well under 30-file / 5,000-line fan-out ceiling). No `--focus` / `--min` / `--diff-only` filters applied.

## Findings

### [MAJOR] God function: cyclomatic complexity ~20, nesting to 4-5, pricing + inventory + notification in one body
- **Domain:** Maintainability (B1)
- **Verified by:** DERIVED — AST walk of `process_order_checkout`: ~20 `If/For/BoolOp` decision nodes; max block nesting 5; 98-line body. Trace chain: `for item in items` (complexity.py:31) → `if stock < qty` (complexity.py:39) → `else: if audit_log is not None` (complexity.py:42-44); parallel chain `if is_vip` (complexity.py:48) → `if user_tier == "PLATINUM"` (complexity.py:49) → `if line_price > 1000.0` (complexity.py:50); parallel chain `if send_receipt` (complexity.py:83) → `if email` (complexity.py:86) → `if "@" in email` (complexity.py:87) → `if audit_log is not None` (complexity.py:88).
- **Evidence:** `evals/fixtures/complexity.py:9-98` — `def process_order_checkout(...)`, body spans discount math (complexity.py:48-70), inventory gate (complexity.py:39-44), tax dispatch (complexity.py:74-79), receipt side-effect (complexity.py:83-89).
- **Failure scenario:** Any discount-rule, tax-rule, or stock-policy change forces editing the same 90-line body; a tax fix risks breaking VIP discount branches with no seam to test in isolation. Permanent carrying tax, not a one-time read cost.
- **Fix:** Split by responsibility at module scope: `validate_inventory(item, apply_override)`, `price_line(item, user_tier, is_vip)`, `compute_tax(taxable, currency)`, `maybe_queue_receipt(order, send_receipt, audit_log)`; `process_order_checkout` becomes orchestration only.
- **Trade-off:** Adds 3-4 small functions and call overhead (negligible latency); pays back in isolated unit tests per rule. Scope: module.

### [MAJOR] Boolean flag arguments switching execution paths plus 7-parameter arity
- **Domain:** Maintainability (B1)
- **Verified by:** DERIVED — signature at complexity.py:9-17 has `is_vip: bool`, `apply_override: bool`, `send_receipt: bool` (3 flags) plus 7 total params; each flag selects a distinct path: `if not apply_override: return ...` (complexity.py:40), `if is_vip: ... else: ...` (complexity.py:48-70), `if send_receipt: ...` (complexity.py:83).
- **Evidence:** `evals/fixtures/complexity.py:9-17` — `def process_order_checkout(order, user_tier, items, is_vip, apply_override, send_receipt, audit_log=None)`.
- **Failure scenario:** Callers combine flags into 2³ behaviours verified only through the full checkout; adding a fourth tier/flag multiplies untested combinations and transposition risk at call sites.
- **Fix:** Replace flags with explicit seams at boundary scope: a `DiscountPolicy` enum/strategy for `is_vip`+`user_tier`, an `InventoryPolicy` (`strict` vs `backorder`) for `apply_override`, and a separate `queue_receipt()` call instead of `send_receipt`; group params into `OrderContext` object.
- **Trade-off:** More types and one extra call site for receipts; cost is upfront API churn for fewer combinatorial tests later. Scope: boundary.

### [MINOR] Magic discount rates, thresholds, and tax rates with no named constants
- **Domain:** Maintainability (B4)
- **Verified by:** READ
- **Evidence:** `evals/fixtures/complexity.py:50-79` — `0.25, 0.20, 0.15, 0.10, 0.05, 0.08, 0.03, 0.02`, thresholds `1000.0, 500.0, 5000.0`, rates `0.0825, 0.21, 0.10`.
- **Fix:** Hoist to module constants (`PLATINUM_HIGH_VALUE_RATE`, `USD_TAX_RATE`, ...) or a rate table.

### [MINOR] Unenforced input contract: unvalidated `dict.get` defaults silently change behaviour
- **Domain:** Correctness (A8)
- **Verified by:** DERIVED — chain: `order.get("currency", "USD")` (complexity.py:26) → `if currency == "USD" / elif "EUR" / else 0.10` (complexity.py:74-79); `item.get("stock", 0)` (complexity.py:34) → `if stock < qty: return Out of stock` (complexity.py:39); `item.get("price", 0.0)` with no negativity check.
- **Evidence:** `evals/fixtures/complexity.py:26,31-34,74-79`
- **Fix:** Validate at function entry (local scope): reject unknown currency, negative price, and missing stock explicitly instead of defaulting.

### [MINOR] Audit trail via mutated `audit_log` list plus hidden notification side-effect
- **Domain:** Operations (C4)
- **Verified by:** READ
- **Evidence:** `evals/fixtures/complexity.py:43-44,88-89` — `audit_log.append(...)` inside pricing loop and inside `if send_receipt:` calculation function.
- **Fix:** Return audit events as structured data in the result dict (local scope) instead of mutating the caller's list; move receipt queuing out of the totals computation.

## Aligns well
- Early return on empty cart (complexity.py:28-29) fails fast on (A1).
- No dead code, unused surface, or speculative generality found; every parameter is read (L1–L4 clean).
- No attacker-controlled source reaches a harmful sink; no auth, crypto, or deserialization surface in scope (S1 clean).
- Float-money rounding is single-process here so no cross-boundary (D3) finding is raised per the interoperability boundary rule; the residual precision note belongs to Correctness, not the seam.