Reviewing target fixture and run directory.
Found coarse-grained locking defects — now checking eval expectations.
I've mapped the defects to the concurrency and performance guidelines — now verifying the scoring.
# Review: `lock_starvation.py` (focused)

`2 findings · C:0 M:2 m:0 i:0 · Mean 97/100 · Final Grade B`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/lock_starvation.py` · Not examined: 0 — none
Paths: 0 resolved open · Unmapped: 0 — no trust-boundary crossings in 53-line fixture
Unclassified: 0 findings fit no axis code
Domain Scores: Correctness: 80/100 · Operations: 100/100 · Security: 100/100 · Maintainability: 100/100 · Interoperability: 100/100 · Leanness: 100/100
Gated by: `weakest domain: Correctness (B)` — always printed

## Findings

### [MAJOR] Coarse batch lock serialises all workers to one core
- **Domain:** Correctness (A2)
- **Verified by:** RAN — two-thread repro: 50-doc `index_documents` batch + concurrent `append_to_index`; contender blocked 0.068s ≈ full 50×1ms batch
- **Evidence:** `lock_starvation.py:21-27` — `index_documents`, `with _lock:` wraps entire `for document in documents:` loop including `time.sleep(0.001)` per item
```python
with _lock:
    for document in documents:
        _index[document["id"]] = document
        time.sleep(0.001)
```
- **Failure scenario:** 8-worker pool indexing a 10,000-doc batch (~10s of hold time): 1 worker holds `_lock` for the whole batch, 7 block on `with _lock` in `index_documents`/`append_to_index`. Throughput is permanently 1 core regardless of pool size; tail latency = full batch duration. DERIVED chain: `index_documents:22` acquire → `index_documents:25` sleep per item → `append_to_index:32` waiter blocks.
- **Fix:** Narrow the critical section to the dict mutation only (scope: module — `index_documents`). Move `time.sleep` / per-doc work outside the lock, or delegate to existing `append_to_index` per item.
- **Trade-off:** Per-item acquire/release adds ~10s of ns per doc but restores parallel speedup; cost is loss of batch atomicity — a concurrent reader can now observe a partial batch.

### [MAJOR] Drain holds lock across 5s empty-queue sleep, starving all workers
- **Domain:** Correctness (A2)
- **Verified by:** RAN — started daemon `drain_queue` on empty `pending`, then `_lock.acquire(timeout=2.0)` from main thread: returned `False`, waited full 2.002s
- **Evidence:** `lock_starvation.py:45-53` — `drain_queue`, `with _lock:` wraps `while True:` including `time.sleep(5.0)` on the empty path
```python
with _lock:
    while True:
        item = pending.pop(0) if pending else None
        if item is None:
            time.sleep(5.0)
```
- **Failure scenario:** One worker enters `drain_queue` when the queue runs dry and holds `_lock` for the full 5.0s sleep. Every other worker calling `index_documents`/`append_to_index`/`drain_queue` blocks for up to 5s per drain cycle; under intermittent load this repeats indefinitely and the pool stalls with no deadlock and no corruption.
- **Fix:** Pop under lock, process and wait outside it (scope: module — `drain_queue`). Replace `pending: list` + `sleep` with `queue.Queue.get(timeout=5.0)` outside the lock, or `threading.Condition.wait()`.
- **Trade-off:** Requires changing `pending` type / all producers to `put()` + notify (boundary scope if producers live elsewhere); adds wake-up/notify complexity but eliminates the 5s starvation window. No per-item cost.

## Aligns well
- `append_to_index:30-33` holds the lock for one dict insert only — correct minimal critical section (A2).
- Single module-level `_lock` guarding `_index` is the right granularity of shared state; no lock-ordering or nested-lock hazard present (A2).
- Both defects are labelled inline (`MAJOR DEFECT`); per ground rules documented-is-not-resolved, so severity stands, but intent is unambiguous.

*Operations (C1/C2) cross-references both items as throughput collapse but takes no separate deduction — Correctness owns the failure scenario (lock held across loop/drain, per `domains/correctness/concurrency/guidelines/deadlocks-locking.md:14`). No security path (no Source → Boundary → Sink), no leanness/maintainability/interop defects in 53 lines.*