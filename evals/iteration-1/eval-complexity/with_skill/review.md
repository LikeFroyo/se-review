I'll read that file.
Let me check how this fixture is used before reviewing.
This is eval #8. Let me check the guideline IDs it maps to and measure the complexity claims rather than trusting the docstring.
My measurement script was wrong (it didn't descend properly). Let me rewrite it correctly.
Still undercounting — my visitor has a bug. Let me verify with a flat, unambiguous count plus `radon` as a cross-check.
Flat count confirms 20 decision points (CC = 20). Now let me find the B1/B5 guideline definitions to grade correctly.
# Complexity Review: `process_order_checkout`

`1 finding · C:0 M:1 m:0 i:0 · Sub-Domain Score: 90/100 (Grade A-)`

## Findings

### [MAJOR] Single 88-line function owns five divergent responsibilities, gated by three boolean flags
- **Domain:** Maintainability (B1 Complexity, B5 Design)
- **Evidence:** `evals/fixtures/complexity.py:9-98` — `process_order_checkout` carries **19 decision points** (cyclomatic complexity **20**, measured via AST: `if` at 28, 36, 39, 40, 43, 48, 49, 50, 55, 62, 63, 68, 74, 86, 87, 88; `elif` at 54, 76; `for` at 31), against a guideline threshold of 10–15 (`complexity/guidelines/cognitive-cyclomatic.md:8`). Body is 88 lines against a 50-line threshold (`:9`).

  **Nesting reaches 4 levels past the guideline's 3-level limit** in three independent places:
  - `complexity.py:39-44` — `for` → `if stock < qty` → `if not apply_override` / `else:` → `if audit_log is not None`
  - `complexity.py:48-60` — `for` → `if is_vip` → `if user_tier == "PLATINUM"` → `if line_price > 1000.0`
  - `complexity.py:83-89` — `if send_receipt` → `if email` → `if "@" in email` → `if audit_log is not None`

  **Divergent duties in one body:** cart validation (`:28-29`), inventory/stock enforcement (`:39-44`), tiered discount policy (`:48-69`), tax-rate selection (`:74-79`), receipt dispatch (`:83-89`), and audit recording (`:44`, `:89`) — six, where the guideline names "validating input + computing pricing + updating database + sending notifications" as the canonical conflation (`:9`).

  **Three boolean flags branch behavior** — `is_vip`, `apply_override`, `send_receipt` (`:13-15`) — plus arity 7 with a defaulted `audit_log: Optional[List[str]] = None` (`:16`). `parameter-lists.md:7-8,10` names both the flag pattern and the arity/`None`-default pattern explicitly. `is_vip` also *partially duplicates* `user_tier`: the `else` branch at `:61-69` re-tests `user_tier == "SILVER"` for non-VIP users, so the two parameters encode overlapping policy state that no single value owns.

- **Failure scenario:** The discount ladder is 8 mutually exclusive terminal paths (`:48-69`) whose coverage cannot be exercised independently — a test of the tax path (`:74-79`) must first construct an `items` list that survives stock validation, VIP branching, and every line-item default. There is no seam: `total`, `discount`, and `tax` are locals discarded at return, so no test can assert a discount rate in isolation. The concrete regression risk is the *silent* kind. At `:59-60`, a VIP with tier `SILVER` or `BRONZE` falls to `discount += line_price * 0.05`; at `:68-69`, a non-VIP `BRONZE` line at or under $5 000 gets **no discount at all**, because `discount` is only incremented inside the `if line_price > 5000.0` guard and there is no `else`. Adding a fourth tier or moving the $5 000 threshold means editing a branch inside a nesting level an author has to re-derive to locate — and the change is invisible in review precisely because 88 lines of nesting suppress the diff's legibility. A maintainer who "just adds an else" to the $5 000 path silently re-prices every bronze cart in production.

- **Fix:** Decompose into four single-responsibility functions, replacing all three booleans (scope: **local** to the module):
  1. `price_cart(items, discount_policy) -> PricingResult` — pure, no flags. Move the `:48-69` ladder into a `TierDiscountPolicy` lookup keyed on `(tier, is_vip)`, so the 8 paths become a data table with one branch. This is where the missing-`else` defect becomes visible as a *missing table row* rather than a missing nested block.
  2. `validate_inventory(items) -> list[StockShortfall]` — pure, returns shortfalls instead of returning early, so `apply_override` (`:40`) becomes a caller's decision rather than an internal branch.
  3. `tax_for(currency, taxable) -> Decimal` — extract `:74-79`; the currency ladder becomes a rate table.
  4. `dispatch_receipt(order) -> None` and audit emission — pull `:83-89` out entirely. This is the highest-value single change: it removes the only side effect from the calculation path and drops nesting from 4 levels to 1.

  Within what remains, flatten `:39-44` by inverting to a guard clause (`if stock < qty and not apply_override: return ...`) and delete the `else:` at `:42`, which is redundant after the `return` at `:41`. Replace `total`/`discount`/`tax` floats with `Decimal` and return a typed `PricingResult` dataclass — this kills the three `round()` calls at `:93-96` and gives tests a seam.

- **Trade-off:** At local scope the cost is one refactor commit touching no call sites in this file, plus a new policy table. The real price is elsewhere: the three flags are almost certainly load-bearing for callers *outside* this file, so splitting them into a policy object is a boundary change that needs caller migration — worth doing, but schedule it separately from the local extraction. The `Decimal` switch will surface any latent float drift in stored totals that the current `round()` is masking; expect that to generate its own follow-up rather than being a free correctness win.

## Aligns well
- Early-exit on empty cart (`complexity.py:28-29`) is the right shape for a guard clause — the function just fails to apply that pattern consistently to the four deeper branches.
- `currency = order.get("currency", "USD")` (`:26`) defaults sensibly and keeps the currency explicit in the returned payload (`:97`), so the caller is not left inferring it.