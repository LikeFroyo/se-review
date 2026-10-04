Now I have both files. Let me review the Python code against the constraints.

## Review: `suppress_lockless_accumulator.py` vs `suppress_lockless_accumulator_CONSTRAINTS.md`

### Constraint C1: "Exactly one thread ever calls `apply()`. It is the pipeline's single consumer thread, started once by `pump`."

**Compliance: ✅ The code complies with C1.**

**Evidence:**

| Aspect | Code | Constraint |
|--------|------|------------|
| Single caller of `apply()` | `pump()` is the only caller of `absorber.apply()` | ✅ Exactly one thread |
| Single consumer thread | Docstring: `"Absorber: one writer, the pipeline's single consumer thread."` | ✅ Single writer |
| No locks needed | No `threading.Lock` or `RLock` used | ✅ "a lock would imply writers that do not exist" |
| `pump` started once | `PUMPED` counter and `pump()` called once in pipeline | ✅ "started once by `pump`" |

### Code analysis

The `Absorber` class implements a lockless accumulator with two internal state variables:

- **`_pending`** (`defaultdict(int)`): Accumulates raw contributions per slot as they arrive.
- **`_frozen`** (`dict`): Snapshotted values after the pipeline drains, computed in `freeze()`.

The `apply` method:
```python
def apply(self, slot, contribution):
    self._pending[slot] += contribution
    if contribution == 0:
        return
    self._frozen[slot] = self._frozen.get(slot, 0.0) + contribution
```

Key observations:

1. **Early return for zero contribution** — when `contribution == 0`, `_frozen` is not updated. This is consistent because there's nothing to accumulate/freeze.

2. **No synchronization primitives** — since constraint C1 guarantees single-threaded access, omitting locks is correct and avoids unnecessary overhead.

3. **`freeze()` returns a copy** — `{slot: value for slot, value in self._frozen.items()}` prevents external mutation of internal state.

4. **`_pending` tracks in-progress contributions** — the accumulating sum before drainage/freezing.

### Potential improvements / notes

- **No runtime enforcement of C1**: There's no guard or assertion verifying that `apply` is called from only one thread. This is acceptable if the contract is externally guaranteed (which the constraints specify it is), but an debug-mode assertion could catch accidental multi-threaded usage during development.

- **`contribution == 0` early return**: The `self._pending[slot] += 0` still executes (a no-op for `int`), but the early return skips `_frozen` update. This is intentional and correct — zero contributions don't affect the frozen state.

- **Thread-aware documentation**: The docstring could explicitly state "Must only be called from the single consumer thread" to make the contract explicit for future maintainers.

### Conclusion

The code correctly implements a **lockless accumulator** for a single consumer thread, fully consistent with constraint C1. No locks are used (as justified by the absence of multiple writers), and the design is clean and minimal. The only missing piece is a documentation note making the single-thread contract explicit, but this is a style concern rather than a functional issue.

The code requires no changes to satisfy the stated constraints.