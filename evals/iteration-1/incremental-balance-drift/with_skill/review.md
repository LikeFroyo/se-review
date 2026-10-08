Reviewing your incremental drift fixture — inspecting code and run directory.
Found the balance drift — now mapping the full eval context.
Confirmed the core state-corruption pattern — now checking remaining domains for full coverage.
# Review: `incremental_drift.py` — incremental balance drift

`1 finding · C:1 M:0 m:0 i:1 · Mean 95.8/100 · Final Grade F`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/incremental_drift.py` · Not examined: 0 — none
Paths: 0 · Unmapped: 0 — no trust boundary or crossing located
Unclassified: 0 findings fit no axis code
Domain Scores: Correctness: 75/100 · Leanness: 100/100 · Security: 100/100 · Maintainability: 100/100 · Operations: 100/100 · Interoperability: 100/100
Gated by: `Critical finding` — state corruption in `Ledger.reclassify` caps grade at F despite Mean 95.8 (weakest domain Correctness: C would separately gate at C).

## Findings

### [CRITICAL] `Ledger.reclassify` mutates entry amount without adjusting incremental `balance`, causing permanent drift
- **Domain:** Correctness (A3)
- **Verified by:** RAN — executed `Ledger` with two entries (100 + 50), called `reclassify(e0, 20)`; observed `balance=150` vs `sum(applied)=70`, drift +80.
- **Evidence:** `evals/fixtures/incremental_drift.py:14-17` — `Ledger.reclassify`:
```python
def reclassify(self, entry, new_amount: int) -> None:
    """Move an entry to a different amount without re-deriving the balance."""
    entry.amount = new_amount
    self.applied[entry.index] = entry
```
`apply` at `incremental_drift.py:10-12` maintains `self.balance += entry.amount`, but `reclassify` never applies the delta (`new - old`) nor recomputes. Docstring states the defective behavior as intent.
- **Failure scenario:** Any reclassification silently corrupts state and compounds: ledger reports 150 when true total is 70; every subsequent `apply` builds on the wrong base. In a running-total / financial context this is unrecoverable state corruption with no error — downstream reads, assertions on `balance == sum(applied)`, and audits all fail.
- **Fix:** Apply delta before mutation, scope: local (3 lines in `reclassify`):
```python
def reclassify(self, entry, new_amount: int) -> None:
    self.balance += new_amount - entry.amount
    entry.amount = new_amount
    self.applied[entry.index] = entry
```
Alternative O(n) `self.balance = sum(e.amount for e in self.applied)` restores the invariant but sacrifices the incremental design; prefer delta.
- **Trade-off:** Delta fix is O(1), no added memory or latency; cost is ordering discipline — delta must be read before `entry.amount` is overwritten. No structural change.

### [INFO] `reclassify` relies on implicit `entry.index` / untyped `entry` contract
- **Domain:** Maintainability (B4)
- **Verified by:** READ
- **Evidence:** `evals/fixtures/incremental_drift.py:10-17` — `apply(entry)`, `reclassify(entry, ...)` take untyped `entry`; `entry.index` is dereferenced with no validation against `self.applied`.
- **Fix:** Type `entry` (e.g. `Protocol` with `amount: int; index: int`) and bounds-check `0 <= entry.index < len(self.applied)` or look up by identity.

## Aligns well
- Minimal incremental design is correct in `apply` (A3): single O(1) accumulator update, no recomputation loop.
- No gate defects: no dead code or unused surface (L1–L4 clean); no attacker-controlled source → boundary → sink, so no security path (S1–S4 clean).
- No operations/interop surface: pure in-memory `int` arithmetic, no I/O, retry, encoding, time, or wire crossing — nothing to grade under C1–C8 / D1–D4; `applied` retention is intended ledger history, not unbounded-growth leak.