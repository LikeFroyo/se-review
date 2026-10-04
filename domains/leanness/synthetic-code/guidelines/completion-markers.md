# Completion markers — code that reads finished and is not

Audit for the inverse of dead code: work that is present, reachable, and shaped like a feature, but was never finished.

## Unimplemented bodies on reachable paths

- **`NotImplementedError` as an implementation:** A handler, method, or branch that raises because nobody wrote the body, still wired into routing, the schema, or the interface it claims to satisfy.
- **Placeholder bodies:** `pass`, `...`, or an empty function body on a path callers reach, so the contract is satisfied and nothing happens.
- **Placeholder returns:** `return {}`, `return []`, `return None`, or a zero-valued constant where a real value is required, and downstream code reads the empty result as a legitimate "nothing to do".
- **Mock data in a production path:** Hardcoded fixtures, sample rows, or stub records reachable outside tests, which look like real data to everything reading them.

## Guarantees asserted but not implemented

- **Concurrency claims without a mechanism:** A docstring or comment calling a function "thread-safe" or "safe for concurrent use" where the body holds no lock, no atomic operation, and no thread-local state.
- **Idempotency claims without a key:** A docstring calling a mutating function "idempotent" where nothing deduplicates the request — no idempotency key, no natural-key check, no state guard.
- **Atomicity claims without a transaction:** A docstring calling a multi-write function "atomic" where the writes are not inside one transaction or an equivalent compensation.
- **Error-handling claims without a check:** A docstring promising a validated, sanitized, or safe-for-untrusted-input boundary at a function that performs no validation itself and delegates nothing to a caller that does.
