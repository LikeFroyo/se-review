# Race conditions — shared mutable state and atomicity

Audit concurrent operations and synchronization guards.

## What to look for

- **Check-then-act races:** Checking a condition outside a synchronized block (e.g. `if key in cache: cache[key] = ...`) where another thread can alter state between check and action.
- **Non-atomic read-modify-write:** Counter increments (`counter += 1`) or dictionary appends executed across threads without locks or atomic primitives.
- **Unsynchronized collections:** Reading or writing standard non-thread-safe collections (e.g. standard hash maps or lists) from multiple threads or goroutines.
- **Unsafe publication:** Publishing partially initialized objects or returning internal mutable data references from behind a lock without copying.
