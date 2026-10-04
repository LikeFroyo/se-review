# Error handling — failure propagation and causal chains

Audit error propagation, exception containment, and boundary translation.

## What to look for

- **Swallowed exceptions:** Bare `except Exception: pass` or `catch (Throwable t) {}` discarding errors with no logging.
- **Unchecked return values:** Ignoring error outputs or discarding return values with `_` without written justification.
- **Double-handling / log-and-rethrow:** Logging an exception and immediately re-throwing or returning it, creating duplicate noisy log entries without added context.
- **Broken causal chains:** Stringifying errors (`str(e)` or `%v`) at internal boundaries, destroying the underlying causal stack trace.
- **Missing panic boundaries:** Background goroutines, tasks, or threads spawned without boundary panic/unhandled rejection catches.

## Failure path with less work than the success path

- **Guard clause skips required effects:** A validation that returns early without performing the effects the success path performs — the audit record, the metric increment, the event publish, the state transition to a rejected or failed state — so the record exists for successes and not for failures.
- **Effect emitted before the check:** An audit write, notification, or metric emitted before the validation that decides whether the action is allowed, so a rejected action is still recorded as having happened.
- **Cleanup only on the happy path:** A resource acquired before an operation and released only when the operation succeeds, so a failure leaks it — and the leak is invisible because the failure path returns early.
- **Error path raises a different failure:** A handler whose failure branch raises a new error while the original is discarded, so the caller sees an internal error and the real cause is nowhere in the chain.
