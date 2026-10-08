Reviewing your impossible-state fixture — inspecting code and eval layout.
Found the core Order model — now gathering eval context to complete the review.
Scope mapped — now loading the review rubric to grade the fixture.
I've mapped the defect pattern — now verifying the failure is actually reachable.
# Review: `evals/fixtures/impossible_state.py`

`2 findings · C:1 M:1 m:0 i:0 · Mean 94/100 · Final Grade F`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/impossible_state.py` · Not examined: 0 — none
Paths: 0 · Unmapped: 0 — no trust-boundary crossing in this in-memory model
Unclassified: 0 findings fit no axis code
Domain Scores: Correctness: 90/100 · Maintainability: 75/100 · Security: 100/100 · Leanness: 100/100 · Operations: 100/100 · Interoperability: 100/100
Gated by: `Critical finding` — any Critical caps the grade at F; weakest domain (Maintainability, C) would otherwise gate at C.

Serial review (1 file, ~50 lines; no fan-out per `shared/domain-fanout.md` ceiling).

## Findings

### [CRITICAL] Independent lifecycle booleans admit impossible states
- **Domain:** Maintainability (B1)
- **Verified by:** RAN — executed `mark_cancelled(); mark_shipped()`, `mark_refunded()` without pay, and all-flags-true repro against the fixture; all stored without error.
- **Evidence:** `evals/fixtures/impossible_state.py:6-12` — `Order.__init__` defines four independent flags:
  `self.is_paid = False`, `self.is_cancelled = False`, `self.is_refunded = False`, `self.is_shipped = False`
  with `mark_paid/mark_cancelled/mark_shipped/mark_refunded` at `:15-29` each flipping one flag with no check of the others, and `to_row() :31-39` persisting any of the 2^4 combinations.
- **Failure scenario:** `o.mark_cancelled(); o.mark_shipped()` yields `{is_cancelled: True, is_shipped: True}` — a shipped-after-cancel record that is storable, returned by `to_row()`, and reads as valid downstream. `o.mark_refunded()` with no prior pay yields `{is_refunded: True, is_paid: False}` — a refund of an unpaid order. `mark_paid(); mark_cancelled(); mark_shipped(); mark_refunded()` yields all-true. No assignment can reject these; terminal states are not absorbing. This is the exact trigger in `domains/maintainability/complexity/guidelines/state-representation.md` (boolean state) and scores Critical per `domains/maintainability/complexity/sub-leaf.md`.
- **Fix:** Shape first, behaviour separately. Replace the four bools with a single closed state (e.g. `Status` enum: `AWAITING_PAYMENT → PAID → SHIPPED → COMPLETE`, plus terminal `CANCELLED`/`REFUNDED`), with transitions that raise on illegal moves and absorbing terminals. Scope: module (`Order` class + `to_row`/`reconcile` readers).
- **Trade-off:** Adds one enum and guard clauses (small complexity increase, localized to `Order`); eliminates the recurring cost of every reader re-interpreting flag combinations.

### [MAJOR] Unguarded non-idempotent transitions and precedence-masking reader
- **Domain:** Correctness (A1)
- **Verified by:** RAN — same repro run: `reconcile()` on the cancelled+shipped row returns `"closed"`; double `mark_paid()` yields `history == ['paid','paid']`.
- **Evidence:** `evals/fixtures/impossible_state.py:15-29` — each `mark_*` unconditionally sets `True` and appends to `history`; `reconcile() :42-50` checks `if order.is_refunded or order.is_cancelled: return "closed"` before `is_shipped`/`is_paid`.
- **Failure scenario:** The invalid combination from Finding 1 is not just storable but reachable on the happy path with no error, and the reader hides it: cancelled+shipped reports `"closed"`, so a caller cannot distinguish "cancelled before fulfilment" from "shipped despite cancellation" and may skip fulfilment-reversal or double-charge. Re-entering `mark_paid()` duplicates the `paid` side effect in `history`, so retries/re-deliveries corrupt the audit trail — the `Transition effects not idempotent` and `Guard bypassed` triggers in `domains/correctness/logic/guidelines/state-machine-completeness.md`.
- **Fix:** Add transition guards (`paid` requires unpaid+uncancelled; `shipped` requires paid+uncancelled; `cancelled`/`refunded` require non-terminal and refuse post-ship/post-close, raising or returning an error), make re-entry idempotent (no second `history` append), and either surface conflicting states as an error in `reconcile()` or remove `reconcile()`'s precedence chain once the enum makes it total. Scope: module (`mark_*` + `reconcile`).
- **Trade-off:** Adds branch checks per transition and a defined duplicate-delivery policy (raise vs. no-op); cost is a few extra unit tests for the transition table. Behaviour fix ships now; the structural enum fix in Finding 1 remains the durable fix.

## Aligns well
- `amount_cents: int` avoids float money (D3); no float conversion or rounding in scope.
- `to_row()` is a pure projection with no I/O or branching — easy to replace when the state becomes an enum.

## Notes on domains with no findings
- Security (100): no untrusted source, boundary, or sink in this file; no open paths.
- Leanness (100): no dead code or speculative surface proved; `history` is written but never read here — noted as a smell, not graded dead without whole-repo proof.
- Operations/Interoperability (100): `history: List[str]` grows unboundedly on repeated `mark_*`, but with no loop, persistence, or wire contract in scope this is not graded as a C1/D4 defect.