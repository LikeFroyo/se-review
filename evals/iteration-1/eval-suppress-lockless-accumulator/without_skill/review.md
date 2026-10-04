I've read both files. Let me review the Python code against the constraints.

## Review: `suppress_lockless_accumulator.py` vs `suppress_lockless_accumulator_CONSTRAINTS.md`

### Constraint C1: "Exactly one thread ever calls `apply()`. It is the pipeline's single consumer thread, started once by `pump`."

**Code analysis:**

The code fully satisfies this constraint:

1. **`pump(rows, absorber)`** is the sole caller of `absorber.apply()`. It's invoked once during pipeline setup.

2. **Single-threaded design:** The docstring states "The only caller of apply(). Started once, on one thread." The global `PUMPED` counter and the function's design confirm single-consumer semantics.

3. **No locks needed:** As the constraints note, "one writer cannot race itself; a lock would imply writers that do not exist." The `Absorber` class has no locks — `_frozen` and `_pending` are mutated lock-free by the single consumer thread.

4. **Read-after-drain pattern:** `freeze()` returns a snapshot of `_frozen` only after the pipeline drains, which is the pattern the constraints describe ("values are read only after the pipeline drains").

### Code correctness

- `_pending[slot] += contribution` — safe under single-writer access
- `_frozen[slot] = self._frozen.get(slot, 0.0) + contribution` — safe under single-writer access  
- `freeze()` returns a clean dict copy — no race conditions on read
- The lockless design is intentional and correct for the single-consumer pipeline pattern

### Conclusion

The implementation is **consistent** with constraint C1. The `Absorber` class is a properly designed lockless accumulator for a single consumer thread, with `pump` as the exclusive `apply()` caller. No violations or redesigns are needed.

Is there a specific aspect of the code-constraint alignment you'd me to investigate further?