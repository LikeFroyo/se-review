Reviewing the skipped-tests fixture and run bundle.
Found skips and expected failures — now mapping the full eval layout.
Initial pass flags unowned skips — now checking determinism and coverage rules to complete the review.
Review: `evals/fixtures/skipped_tests.py` + `se-run-eval-skipped-tests-with_skill-r1-440ae7`

Scope: single 40-line pytest fixture. Evaluated against `domains/correctness/testing/sub-leaf.md` + `guidelines/test-adequacy.md`.

## Findings

**1. MAJOR (-10): Disabled test with no owner, assertion-free — `skipped_tests.py:15-17`**
```python
@pytest.mark.skip
def test_price_bulk(self):
    pass
```
Violates two `test-adequacy.md:13` / `sub-leaf.md:19` triggers collapsed per one-finding-per-root-cause:
- `skip` with no reason and no owner/issue — reports green while covering nothing.
- `pass` body — assertion-free, survives all mutants.
Failure scenario: bulk-pricing regression ships with suite green; skipped test still costs collection/runtime and reads as protection.
Fix (Local): delete or re-enable with real assertions + `reason=` + owner link + `strict` enforcement. If bulk case obsolete, delete — do not leave `skip`.

**2. MAJOR (-10): Expected-failure that cannot fail, vague owner — `skipped_tests.py:19-21`**
```python
@pytest.mark.xfail(reason="flaky in CI")
def test_price_with_promotion(self):
    assert calculate_price(10, 0.8) == 800
```
- Has `reason=` but no owner/issue, no `strict=True`. Default `strict=False` → when fix lands, result is `XPASS` (still green), marker silently rots. Per `test-adequacy.md:14`.
- Reason `flaky in CI` is undiagnosed flakiness, not a product expectation. Correct handling is determinism fix/quarantine, not `xfail`.
Failure scenario: promotion logic regresses/fixed, suite stays green either way; real fix goes unnoticed.
Fix (Local): `pytest.mark.xfail(strict=True, reason="<issue-url>: <condition>")`, plus CI `--runxfail` check; investigate flakiness instead of masking.

**3. INFO: Uncounted marker set — systemic, no site**
Nothing asserts size of skip/`xfail` list (`test-adequacy.md:18`). Growth is invisible to reviewers.
Fix (Module): add count assertion / CI check on `SKIP/XFAIL` totals; enforce `xfail_strict=true` in config.

**4. INFO: Duplicated check — `skipped_tests.py:23-24` vs `28-29`**
```python
def test_promotion_disabled(self):
    assert apply_discount(1000, "none") == 1000  # identical in TestPricing + TestDunning
```
Two similar lines encoding same rule, not different rules. Deduplicate or differentiate intent; not graded as defect without evidence of divergent knowledge.

**5. INFO: Unverifiable / out-of-scope**
- Unused imports `skipped_tests.py:3,7-8` (`Any,Dict,List,CENTS_PER_UNIT,REGION_MULTIPLIER`): leanness waste, linter work — not graded here.
- `skipped_tests.py:39-40` `shipping_days("uk",...) == 2` vs `"GB"`: ambiguous whether case-insensitivity is intended contract or fixture unrealism. No production code in `evals/` to verify — capped at Info per verification-limits rule.

## Score (testing sub-domain only)

`100 - 10 - 10 = 80` → Grade B. Sound otherwise: remaining 5 tests have real assertions, fixed dates (`date(2026,1,15)`, no `datetime.now()`/`sleep`), no mock-tautology.