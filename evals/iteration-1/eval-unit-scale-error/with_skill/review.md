Reviewing the file and directory — pulling the contents for inspection.
First file shows unit handling issues. I'll survey the surrounding eval structure.
I've confirmed this is a focused scope, so I'll examine the relevant domain checklists.
I've mapped the scale and conversion faults. Now I'll verify them with a quick execution.
# Review: `evals/fixtures/unit_scale_error.py`

`6 findings · C:4 M:1 m:1 i:0 · Mean 81/100 · Final Grade F`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/unit_scale_error.py` · Not examined: 0 — none
Paths: 0 · Unmapped: 0 — no service, network, or auth crossing in this fixture
Unclassified: 0 findings fit no axis code
Domain Scores: Correctness: 65/100 · Interoperability: 25/100 · Maintainability: 97/100 · Security: 100/100 · Operations: 100/100 · Leanness: 100/100
Gated by: `Critical finding` — any Critical caps the grade at F; weakest domain is Interoperability (F)

Ruling: docstrings and `_cents` / `_micros` / `_seconds` names state the contract; the arithmetic is graded against them, not the reverse.

## Findings

### [CRITICAL] Invoice stores dollars in `_cents` fields — 100x understatement plus float money
- **Domain:** Interoperability (D3)
- **Verified by:** RAN — instantiated `Invoice(100.00)`; observed `subtotal_cents=100.0, tax=8.25, total=108.25` and `persisted_totals()` returning the same floats instead of `10000 / 825 / 10825` ints.
- **Evidence:** `evals/fixtures/unit_scale_error.py:11-15` — `Invoice.__init__`, quote `self.subtotal_cents = subtotal` / `self.tax_cents = subtotal * TAX_RATE` with `subtotal: float` (dollars) and no `* 100` or rounding.
- **Failure scenario:** Every invoice persists and forwards 1/100th of the real amount. A $100.00 order ledgers as $1.00 (plus binary-float dust, e.g. `19.99 * 0.0825 = 1.649...`). Downstream `convert_to_micros()` compounds it. Silent revenue loss / ledger mismatch on every row.
- **Fix:** Module scope. Store `int(round(subtotal * 100))` in all three `_cents` fields, or change the type to `Decimal`/int-cents at the boundary and reject float. Fix `persisted_totals()` at the same time so it emits ints.
- **Trade-off:** Adds one rounding decision per constructor (half-up vs banker's must match the ledger contract); negligible latency, one contract to confirm with the ledger owner.

### [CRITICAL] `fee_for_overdue` dereferences `invoice.due_at` that is never assigned
- **Domain:** Correctness (A8)
- **Verified by:** RAN — called `fee_for_overdue(Invoice(100.00))`; observed `AttributeError: 'Invoice' object has no attribute 'due_at'`.
- **Evidence:** `evals/fixtures/unit_scale_error.py:18-21` — `fee_for_overdue`, quote `days_overdue = (datetime.utcnow() - invoice.due_at).days`. No `due_at` parameter or assignment in `Invoice.__init__ (11-15)`.
- **Failure scenario:** Every late-fee path raises instead of charging. Batch billing jobs abort on the first overdue invoice; no fee is ever collected.
- **Fix:** Local scope. Add `due_at: datetime` to `Invoice.__init__` (timezone-aware), store it, and guard the subtraction. Scope stays local; callers passing naive datetimes need one migration pass.
- **Trade-off:** Requires choosing the `due_at` source of truth (contract vs DB column) and backfilling existing rows; small schema/call-site cost.

### [CRITICAL] `settlement_window_seconds` mixes ms/s and multiplies instead of dividing — ~10^6x blowup
- **Domain:** Interoperability (D3)
- **Verified by:** RAN — `settlement_window_seconds(1_700_000_000_000)` returned `1698300000000000`; a 1 s-later input (`...001000`) returned a value `1_000_000` s larger instead of `1` s larger.
- **Evidence:** `evals/fixtures/unit_scale_error.py:24-26`, quote `return (created_ms - 1_700_000_000) * MILLISECONDS_PER_SECOND`. `created_ms` is ~1.7e12 (ms) but the epoch constant is ~1.7e9 (s), and ms→s needs `/ 1000`, not `* 1000`.
- **Failure scenario:** Every settlement window is ~53M years; timeouts/sweeps never fire or fire immediately depending on the consumer's clamp. Funds sit unsettled or the scheduler overflows.
- **Fix:** Local scope. `return created_ms // 1000 - 1_700_000_000` (or `/ 1000` if fractional seconds are contractual), with both operands documented as same-unit before subtraction.
- **Trade-off:** Integer vs float seconds must match the consumer; one-line change plus a contract check on whether sub-second precision is kept.

### [CRITICAL] `convert_to_micros` is 10x short and reuses a time constant for money
- **Domain:** Interoperability (D3)
- **Verified by:** RAN — `convert_to_micros(100)` returned `100000`; 100 cents ($1) is `1_000_000` micros of a dollar.
- **Evidence:** `evals/fixtures/unit_scale_error.py:29-31`, quote `return amount_cents * MILLISECONDS_PER_SECOND`. Correct factor is `10_000`; `MILLISECONDS_PER_SECOND (1000)` is a time unit applied to money.
- **Failure scenario:** Ledger receives 1/10th of every amount. Combined with finding 1, a $100.00 invoice settles as $0.10. Silent, systematic short-settlement.
- **Fix:** Local scope. Introduce `MICROS_PER_CENT = 10_000` and `return amount_cents * MICROS_PER_CENT`. Do not reuse the time constant.
- **Trade-off:** Must confirm the ledger's micros definition (dollar-micros vs cent-micros) once; zero runtime cost.

### [MAJOR] Overdue fee can go negative and truncates partial days on a naive clock
- **Domain:** Correctness (A1)
- **Verified by:** DERIVED — chain `datetime.utcnow()` (naive, deprecated) minus `due_at` → `.days` floor → `* 500` with no `max(0, …)` floor. A non-overdue invoice yields negative days × 500 = a credit; a 23-hour overrun yields 0.
- **Evidence:** `evals/fixtures/unit_scale_error.py:18-21`, quote `(datetime.utcnow() - invoice.due_at).days` and `return days_overdue * 500`.
- **Failure scenario:** Pre-due invoices accrue negative fees (money owed to the customer); just-overdue invoices escape fees. Naive `utcnow()` also shifts by hours if `due_at` is ever zone-aware/local.
- **Fix:** Module scope. Clamp with `max(0, …)`, define partial-day policy (ceil vs whole-day), and inject the clock (`now: datetime` parameter) instead of calling `utcnow()` inline.
- **Trade-off:** Injecting the clock adds one parameter and test-seam churn; per-day vs partial-day billing needs a product decision.

### [MINOR] Misleading units, magic fee, and dead constants obscure every scale above
- **Domain:** Maintainability (B4)
- **Verified by:** READ — `_cents` names hold dollar-floats, `500` has no name or currency, `SECONDS_PER_DAY` and `currency` are unused, and one time constant names two money scales.
- **Evidence:** `evals/fixtures/unit_scale_error.py:5-21` — `SECONDS_PER_DAY`, `currency`, bare `500`, `_cents` fields holding floats.
- **Fix:** Rename or retype to match reality (`subtotal_cents: int`), name `LATE_FEE_CENTS_PER_DAY = 500`, delete or use `SECONDS_PER_DAY`/`currency`.

## Aligns well
- Docstrings state the intended units (`cents`, `micro-units`, `seconds`) — the contract that makes each scale defect decidable (D3).
- `persisted_totals()` centralizes the DB write in one function, so the cents fix has a single seam (D4).