Reviewing your fixtures and run directory.
Found the tautological test pattern — now digging into the surrounding context.
This looks like a tautology check — now verifying against the skill's correctness rules.
I've mapped the defect to the testing guidelines — now gathering the scoring details for the final report.
Execution confirms both issues — now finalizing severity and scope.
# Review: `evals/fixtures/pricing.py` + `evals/fixtures/test_expected_value.py`

`2 findings · C:0 M:1 m:1 i:0 · Mean 98/100 · Final Grade A`
Covered: 2/2 files · Scope: focused on: `evals/fixtures/pricing.py`, `evals/fixtures/test_expected_value.py` · Not examined: 0 — none
Paths: 0 resolved open · Unmapped: 0 — no trust crossings in scope
Unclassified: 0 findings fit no axis code
Domain Scores: Correctness: 90/100 · Security: 100/100 · Maintainability: 100/100 · Operations: 100/100 · Interoperability: 100/100 · Leanness: 97/100
Gated by: neither — highest grade reached

Serial mode: 2 files in scope, below 30-file / 5,000-line fan-out ceiling, stayed serial.

## Findings

### [MAJOR] Self-derived expected value — test recomputes the implementation
- **Domain:** Correctness (A6)
- **Verified by:** RAN — executed `python3 -c` with `sys.path=evals/fixtures`: `price_for(100.0,0.15)==85.0` and inline `expected==85.0` match; `price_for(100.0,0.15,0.08)==price_for(100.0,0.15,0.0)` shows second issue.
- **Evidence:** `test_expected_value.py:10-12` — quote offending lines; `pricing.py:3-5` — quote offending lines:
  ```python
  # test_expected_value.py:10-12
  expected = subtotal - (subtotal * rate)
  assert price_for(subtotal, rate) == expected
  # pricing.py:5
  return subtotal - (subtotal * discount_rate)
  ```
  File header `test_expected_value.py:1` states it: `Pricing — the implementation, and a check that cannot fail.`
- **Failure scenario:** Any shared algorithmic misunderstanding passes both sides. The check confirms the code, whatever it does — per `domains/correctness/testing/guidelines/expected-value-provenance.md`: expected re-derived from the implementation. Suite reports protection it does not provide and would freeze a wrong formula as correct.
- **Fix:** Local scope — assert an independently-sourced literal with provenance, e.g. `assert price_for(100.0, 0.15) == 85.0  # 15% off $100 per <requirement>` plus boundary cases (`0%`, `100%`, fractional cents). Do not compute `expected` from `rate`.
- **Trade-off:** Literals must be revisited on deliberate behaviour change; that update cost is the signal — a co-mutated literal without re-verified provenance is itself a defect.

### [MINOR] Unused `tax_rate` parameter silently ignored
- **Domain:** Leanness (L2)
- **Verified by:** RAN — `price_for(100.0,0.15,0.08)` returns `85.0`, identical to `tax_rate=0.0`; `grep tax_rate` in scope finds only `pricing.py:3` definition site, no use in body, no caller passes it.
- **Evidence:** `pricing.py:3-4`:
  ```python
  def price_for(subtotal: float, discount_rate: float, tax_rate: float = 0.0) -> float:
      """Apply the discount to the subtotal. Tax is applied by the caller."""
  ```
  Ruling between readings: doc-as-intent wins — ignoring tax is not a calc bug, but the accepted-then-dropped parameter is a contract trap.
- **Fix:** Local scope — delete `tax_rate` parameter, or implement and test it. If caller-applies-tax is the contract, the signature must not accept it.
- **Fix scope:** local.

## Aligns well
- Implementation is a pure function with no I/O, branching, or ambient state (A1).
- No trust boundary, auth, injection sink, or secret in scope — nothing to grade above Info (S1–S4).
- No loop, retry, cache, or wire-format surface in scope (C1, D3–D4).

No cut. No `--min` exclusions.