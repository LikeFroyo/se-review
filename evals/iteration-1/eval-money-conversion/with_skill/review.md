Reviewing your money conversion fixture — inspecting code and run artifacts.
Found float-based pricing defects; now gathering eval context to complete the review.
Scope confirmed to a single fixture; now loading the review domains and scoring rules.
Core money-handling rules are clear; now checking the remaining guidelines to finalize severity.
Core defects verified by execution; now checking the last scoring details before compiling your report.
# Review: `evals/fixtures/money_conversion.py`

`7 findings · C:4 M:2 m:1 i:0 · Mean 79.5/100 · Final Grade F`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/money_conversion.py` · Not examined: 0 — none
Paths: 0 · Unmapped: 0 — no trust boundary crossing found in single-module fixture
Unclassified: 0 findings fit no axis code
Domain Scores: Correctness: 75/100 · Interoperability: 30/100 · Leanness: 75/100 · Maintainability: 97/100 · Operations: 100/100 · Security: 100/100
Gated by: `Critical finding` — also weakest domain: Interoperability (F); mean band C capped to F

## Findings

### [CRITICAL] Float money in `quote_price` — invoice never reconciles
- **Domain:** Interoperability (D3)
- **Verified by:** RAN — stubbed `requests`, imported fixture, ran `quote_price(0.1,3)` and `sum(quote_price(0.1,1)['total'] for _ in range(10))`
- **Evidence:** `money_conversion.py:11-29` — `subtotal = unit_price * quantity; tax = subtotal * 0.2; return {... "total": subtotal + tax}` with `unit_price: float`, serialised as JSON number
- **Failure scenario:** `quote_price(0.1,3)` returns `total=0.36000000000000004` vs exact `Decimal('0.36')`; 10× `0.1` lines sum to `1.2000000000000002` vs `1.20`. Consumer summing line-item `total`s disagrees with `Decimal` sum of same lines on every invoice; drift grows with line count.
- **Fix:** Boundary scope — change contract to integer minor units (`unit_price_cents: int`), compute `subtotal_cents * 6 // 5` with explicit rounding, return ints. Migrate callers/ledger to cents in one change.
- **Trade-off:** Adds integer-cents convention at the API boundary; callers doing float math must convert once via `Decimal(str(x))`. No runtime cost.

### [CRITICAL] Currency conversion applied twice plus float wire
- **Domain:** Interoperability (D3)
- **Verified by:** DERIVED — chain: producer converts GBP→EUR before serialising (per `convert_gbp_to_eur` docstring `49:58`) → wire carries `float` → this function `return round(amount_gbp * rate, 2)` multiplies by `rate` again
- **Evidence:** `money_conversion.py:49-58` — `def convert_gbp_to_eur(amount_gbp: float, rate: float) -> float: return round(amount_gbp * rate, 2)`
- **Failure scenario:** EUR value already in EUR is scaled by `rate` a second time, off by square of rate (e.g. 10 GBP @1.17 applied twice → ~13.69 instead of 11.70), plus binary-float wire error (`100.10*1.234` → `123.52` vs exact `123.52340` before rounding, Python `round` half-even vs financial half-up on ties).
- **Fix:** Boundary scope — define single conversion owner: accept `Decimal` major units or int minor units with explicit currency code, convert exactly once, round once with `ROUND_HALF_UP` to 2dp. Delete the second multiplication.
- **Trade-off:** Requires auditing producer to confirm it converts; contract change forces all GBP/EUR call sites to pass tagged amounts. Adds `Decimal` quantize cost, negligible.

### [CRITICAL] `rank_customers` sorts numbers as lowercased strings
- **Domain:** Correctness (A1)
- **Verified by:** RAN — `rank_customers({'a':100.0,'b':20.0,'c':9.0})` returns `['a','b','c']`, expected numeric-asc `['c','b','a']`
- **Evidence:** `money_conversion.py:61-63` — `return sorted(scores, key=lambda k: str(scores[k]).lower())`
- **Failure scenario:** Any leaderboard with mixed magnitudes is misordered (`"100.0" < "20.0" < "9.0"` lexicographically), so top-customer selection, payouts, or prioritisation act on the wrong customer deterministically.
- **Fix:** Local scope — `sorted(scores, key=lambda k: scores[k])` (add `reverse=True` if descending intended; intent currently ambiguous so default asc numeric).
- **Trade-off:** None; pure bug fix. Descending vs ascending must be confirmed with owner.

### [CRITICAL] Dead weight: unused `requests` import and `CENTS_PER_UNIT`
- **Domain:** Leanness (L1)
- **Verified by:** DERIVED — repo text search over `evals/fixtures` for `CENTS_PER_UNIT|requests` returns only definition lines `5` and `7`, zero callers; no `getattr`/`importlib`/DI/manifest indirection in file; fixture module, not versioned public API
- **Evidence:** `money_conversion.py:5` — `import requests`; `money_conversion.py:7` — `CENTS_PER_UNIT = 100` never referenced (`MICRO_PER_CENT` is used at `34`, `CENTS_PER_UNIT` is not)
- **Failure scenario:** Permanent carrying cost: every reader, migration, and vendoring pays for a third-party dependency (`requests`) that is never used; unused scale constant invites unit confusion with `MICRO_PER_CENT`.
- **Fix:** Deletion — remove line 5 and line 7.

### [MAJOR] `ledger_import` truncates micro-units via `int()/10`
- **Domain:** Interoperability (D3)
- **Verified by:** RAN — `ledger_import(999)` → `99` (exact 99.9), `ledger_import(15)` → `1` (exact 1.5, 33% loss on that value)
- **Evidence:** `money_conversion.py:37-41` — `return int(decimal.Decimal(amount) / 10)`
- **Failure scenario:** Every amount with remainder mod 10 is systematically short (up to 9 micro-units per import, always downward); ledger total drifts below invoice total with volume. `int()` truncates toward zero instead of rounding.
- **Fix:** Module scope — define rounding contract (`ROUND_HALF_UP` + `quantize`, or explicit floor with documented remainder handling) and apply at both `ledger_import` and `apply_discount` sites.
- **Trade-off:** Rounding adds one `Decimal` operation per import; must agree rounding mode with ledger side or reconciliation still fails on ties.

### [MAJOR] `apply_discount` truncates cents via float division + `int()`
- **Domain:** Interoperability (D3)
- **Verified by:** RAN — `apply_discount(199,10)` → `179` (exact 179.1, loss 0.1c); `apply_discount(101,33)` → `67` (exact 67.67)
- **Evidence:** `money_conversion.py:44-46` — `return int(total_cents * (100 - percent) / 100)` — float `/` then truncating `int()`
- **Failure scenario:** Every discounted line with fractional cents is short by up to ~1c, always in merchant's favour; summed over many lines the invoice total is systematically low and never matches a correctly-rounded expectation.
- **Fix:** Module scope — stay in integers: `(total_cents * (100-percent) + 50) // 100` for half-up, or `Decimal` quantize; same contract as above.
- **Trade-off:** Integer half-up changes existing (buggy) totals by 1c on affected lines; requires backfill decision for historical invoices.

### [MINOR] Magic scale literals with no named contract
- **Domain:** Maintainability (B4)
- **Verified by:** READ
- **Evidence:** `money_conversion.py:22` — `* 0.2`; `money_conversion.py:41` — `/ 10`; `money_conversion.py:46` — `/ 100`; `money_conversion.py:34` — `* MICRO_PER_CENT` (named) vs the rest unnamed
- **Fix:** Localised cleanup — promote `TAX_RATE`, `DISCOUNT_SCALE`, `LEDGER_DIVISOR` to module constants with units in names (`_CENTS`, `_MICROS`).

## Aligns well
- `to_micros` (D3): declared `int → int` fixed-scale conversion `amount_cents * MICRO_PER_CENT`, no float, no rounding — correct pattern.
- Docstrings on `quote_price` and `convert_gbp_to_eur` honestly flag the defects instead of hiding them.

## Domain score derivation
- Correctness 75 = 100-25 (A1 rank sort)
- Interoperability 30 = 100-25-25-10-10 (D3 ×2 Critical, ×2 Major); float-arithmetic ownership assigned here (crossing to consumer/ledger per docstrings), not double-counted in Correctness
- Leanness 75 = 100-25 (one L1 finding collapsed over 2 orphaned symbols)
- Maintainability 97 = 100-3 (B4 magic literals)
- Operations 100, Security 100 — no hot loop, retry, secret, or attacker-reachable sink in scope