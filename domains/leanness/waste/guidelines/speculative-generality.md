# Speculative generality — L2 unused surface and L3 premature abstraction

Audit code against the YAGNI principle: build only what is required now.

## What to look for

- **Unused exported surface (L2):** Exported functions, endpoints, or CLI flags with no callers or callers only in their own unit test.
- **Single-implementor interfaces (L3):** Interface or abstract base class with only one concrete implementation in production code.
- **Speculative extension points:** Event buses, plugin hooks, or middleware slots with zero external subscribers.
- **Unvarying parameter knobs:** Function parameters or configuration flags that are always invoked with the same default argument.
- **Forward-only layers:** Methods or classes that merely delegate to the next layer without adding transformation, caching, or security filtering.

## YAGNI challenge checklist

1. Active requirement: Name the active user story or bug requiring this capability.
2. Two callers rule: Name two distinct production callers for every new abstraction.
3. Rule of Three: Do not generalize on the first or second occurrence; wait until the third repeat.
4. Reversal cost: If the feature could be retrofitted in under a day when needed, delete or defer now.
