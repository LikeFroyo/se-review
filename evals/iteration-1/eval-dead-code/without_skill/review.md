# Code Review: `dead_code.py`

## Summary

This module defines order pricing logic with two pricing adapters and a convenience function. The main issue is that `LegacyPriceAdapter` is dead code — it's defined but never used anywhere in the module, and the docstring explicitly says it was superseded.

---

## Issues

### 1. Dead Code — `LegacyPriceAdapter` (Lines 7–15)

The class docstring says it was *"Superseded by AuroraPricing in the v2 cutover"*, and nothing in this module (or, presumably, the broader codebase) references it. It should be removed. Keeping dead classes around adds cognitive load for future readers and risks someone accidentally wiring it back in.

The commented-out call on line 14 (`# return self.apply_legacy_discount(order)`) compounds this — it references a method (`apply_legacy_discount`) that doesn't even exist on the class. If this is truly just "kept for reference," version control already serves that purpose.

**Suggestion:** Delete `LegacyPriceAdapter` entirely. If there's a genuine need to keep the old logic discoverable, add a comment pointing to the relevant commit or PR.

### 2. `price_order` Creates a New `RateTable` and `AuroraPricing` on Every Call (Lines 26–28)

Every invocation of `price_order` calls `RateTable.load(datetime.now().date())`, which likely hits disk or a database. If this function is called in a loop (e.g., pricing a batch of orders), that's a lot of redundant work.

**Suggestion:** Accept the `RateTable` (or `AuroraPricing` instance) as a parameter, or cache it per date:

```python
def price_order(order, table=None):
    if table is None:
        table = RateTable.load(datetime.now().date())
    return AuroraPricing(table).price(order)
```

### 3. `datetime.now()` Makes the Function Hard to Test (Line 27)

Calling `datetime.now()` directly couples `price_order` to the system clock. Testing for date-boundary behavior requires mocking.

**Suggestion:** Allow the date to be injected:

```python
def price_order(order, as_of=None):
    as_of = as_of or datetime.now().date()
    table = RateTable.load(as_of)
    return AuroraPricing(table).price(order)
```

### 4. Unused Import — `datetime` Is Only Needed Because of the Inline `now()` Call

Minor, but worth noting: if `price_order` is refactored to accept a date or table, the `datetime` import may become unnecessary.

---

## What's Done Well

- **Clear module docstring** — the intent of the module is obvious at a glance.
- **`AuroraPricing` is clean and focused** — small class, single responsibility, easy to understand.
- **`price_order` provides a simple public API** — good that there's a top-level function so callers don't need to know about `RateTable` or `AuroraPricing` internals.
