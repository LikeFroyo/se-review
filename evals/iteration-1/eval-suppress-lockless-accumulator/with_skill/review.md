Reviewing your accumulator probe and constraints.
Found the single-writer claim — now verifying it against the implementation.
I've charted the accumulator's logic quirks — now checking the scoring rubric to finalize the report.
# Review: suppress_lockless_accumulator.py with ACCUMULATOR_CONSTRAINTS.md

`3 findings · C:0 M:0 m:2 i:1 · Mean 98/100 · Final Grade A`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/suppress_lockless_accumulator.py` with `suppress_lockless_accumulator_CONSTRAINTS.md` as binding constraint · Not examined: 0 — none
Paths: 0 · Unmapped: 0 — no untrusted entry points in scope
Unclassified: 0 findings fit no axis code
Domain Scores: Correctness: 97/100 · Leanness: 97/100 · Maintainability: 100/100 · Operations: 100/100
Gated by: neither — highest grade reached

Ruling: `CONSTRAINTS.md` C1 honored as binding intent — code, module docstring, and `pump()` docstring agree on a single writer; code-is-right on this point.

## Findings

### [MINOR] Zero-contribution path diverges `_pending` from `_frozen` and mixes int/float zeros
- **Domain:** Correctness (A1)
- **Verified by:** RAN — imported fixture, called `Absorber().apply('x', 0)`, observed `pending={'x': 0}` vs `freeze()={}`; then `apply('x', 5)` gave `pending int` vs `frozen float`
- **Evidence:** `suppress_lockless_accumulator.py:13-17` — `self._pending[slot] += contribution` runs before `if contribution == 0: return`, while `self._frozen[slot] = self._frozen.get(slot, 0.0) + contribution` runs after
- **Failure scenario:** A consumer that ever reconciles `freeze()` against `_pending` (or iterates `_pending` keys) sees a phantom slot with `0` that `freeze()` omits; `defaultdict(int)` also materializes a key on every zero-contribution row. Type drift: `_pending` seeds `int`, `_frozen` seeds `0.0`.
- **Fix:** Local scope — move the `_pending` update below the zero early-return, or document the split explicitly, and unify the seed (`0.0` in both or `0` in both).

### [MINOR] `_pending` is written but never read in scope
- **Domain:** Leanness (L1)
- **Verified by:** DERIVED — chain `__init__:11` writes `defaultdict(int)` → `apply:14` writes → `freeze:19-20` reads only `_frozen`; no reader of `_pending` in the file
- **Evidence:** `suppress_lockless_accumulator.py:11,14,19-20` — `self._pending = defaultdict(int)`, `self._pending[slot] += contribution`, `freeze()` returns only `{slot: value for slot, value in self._frozen.items()}`
- **Fix:** Local deletion — remove `_pending` if it is vestigial, or expose it via an accessor if an out-of-scope reader exists. Not graded Critical: repo-wide death not proven from this single-file scope.

### [INFO] Module-global `PUMPED` counter is ambient mutable state
- **Domain:** Maintainability (B2)
- **Verified by:** READ
- **Evidence:** `suppress_lockless_accumulator.py:23,26-31` — `PUMPED = 0`, `pump()` does `global PUMPED` + `PUMPED += 1` per row
- **Fix:** Local scope recommendation — make the count an instance field on `Absorber` or a return value from `pump()` so reuse/testing does not share global state. No synchronization is required; see Aligns well.

## Aligns well

- Suppressed concurrency hardening per C1 (A2): `_frozen`, `_pending`, and `PUMPED` are single-writer accumulators owned by the pipeline's single consumer thread started once by `pump()`. One writer cannot race itself; no `Lock`, `RLock`, `synchronized`, or concurrent-dict retrofit is warranted. Adding a lock would imply writers that do not exist, add contention/complexity, and contradict the binding constraint.
- `freeze()` returns a fresh dict comprehension (A2): read-after-drain plus copy avoids caller aliasing of internal `_frozen` without any locking.
- Explicit ownership comments (`slot -> value, owned by the consumer thread`, `The only caller of apply(). Started once, on one thread.`) state the threading contract where it is enforced (B4).