# Magic values & comments — intent capture and documentation honesty

Audit constant declarations, magic values, and comment utility.

## What to look for

- **Magic numbers & strings:** Raw numeric literals (e.g. `0.0825`, `86400`, `1000`) or string codes embedded directly in logic without named constants.
- **Echo comments:** Comments that restate what the line already expresses (`# increment counter` above `counter += 1`).
- **Comments compensating for unclear code:** A multi-line comment explaining complex nested logic instead of refactoring the logic into well-named helper functions.
- **Missing why-comments:** Non-obvious trade-offs, bug workarounds, or regulatory requirements implemented without explaining *why* the non-standard choice was made.
- **Invariant documented but never enforced:** A comment stating a precondition the code depends on ("caller must hold the lock", "must be called inside a transaction", "safe to retry") with no assertion, guard, or type carrying it, so the rule is advisory and the first caller that misses it fails in production rather than at the boundary.
