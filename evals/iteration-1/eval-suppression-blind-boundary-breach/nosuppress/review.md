Reviewing the blind boundary fixture, contract layer, and constraints.
Found a single-import view against a three-name contract — checking the surrounding layout to confirm scope.
The scope is tiny, so I'll run a focused serial review against your constraints and the core quality gates.
# Review: `suppression_blind_boundary_breach.py` + `per_contract_layer.py` against `suppression_blind_boundary_breach_CONSTRAINTS.md`

`3 findings · C:0 M:1 m:1 i:1 · Mean 98/100 · Final Grade A`
Covered: 2/2 files · Scope: focused on: `evals/fixtures/suppression_blind_boundary_breach.py`, `evals/fixtures/per_contract_layer.py` · Not examined: 0 — none
Paths: 0 resolved open · Unmapped: 0 — no untrusted source, boundary, or sink in scope
Unclassified: 0 findings fit no axis code
Domain Scores: Correctness: 97/100 · Maintainability: 90/100 · Security: 100/100 · Leanness: 100/100 · Operations: 100/100 · Interoperability: 100/100
Gated by: neither — mean A, weakest A — **always printed.**

## Findings

### [MAJOR] Set view violates binding C1: reads 1 of 3 required names via direct impl import, bypassing `published_names` door
- **Domain:** Maintainability (B5)
- **Verified by:** `DERIVED` — AST trace: `suppression_blind_boundary_breach.py:5` imports one name; `per_contract_layer.py:17` declares door `published_names = ("parity_fit_impl", "smile_solve_impl", "log_ratio_impl")`; `CONSTRAINTS.md:3-5` requires exactly three reads.
- **Evidence:** `evals/fixtures/suppression_blind_boundary_breach.py:5,8-10` — `from per_contract_layer import parity_fit_impl` then `fit = parity_fit_impl([c.close for c in contracts])`; `evals/fixtures/per_contract_layer.py:4-5` — `parity_fit_impl` documented as `A private helper. Reachable only through the layer's door, by design.`; `evals/fixtures/per_contract_layer.py:17` — door lists three names, two never imported (`smile_solve_impl`, `log_ratio_impl`).
- **Failure scenario:** Set layer silently under-delivers: `smile`/`log-ratio` quantities required by C1 are never computed. Next per-contract change (rename, signature, semantics of either unused helper) breaks the assumed contract without a compile-time signal, and direct `import *_impl` couples set lifecycle to per-contract internals — exactly what C1 `Why` forbids. Ruling: `exactly three` means must-read-three, not at-most-three; `published_names` is the access path, not documentation.
- **Fix:** Shape first, behaviour second. Route access through the declared door (module/boundary scope, 2 files): import the layer module and resolve via `published_names`, then implement the two missing reads and compute remaining set quantities inside the set layer from published values per C1.
- **Trade-off:** Adds one indirection + two call sites; cost is boundary churn (all set-view callers re-verified), not runtime — negligible latency/memory.

### [MINOR] Unguarded denominators crash on empty/zero input
- **Domain:** Correctness (A1)
- **Verified by:** `RAN` — `parity_fit_impl([100,102,98]) -> {'forward':100.0,'width':4}`; `parity_fit_impl([])` raises `ZeroDivisionError`; `set_view([])` raises `ZeroDivisionError`; `log_ratio_impl(1,0)` raises `ZeroDivisionError`.
- **Evidence:** `evals/fixtures/per_contract_layer.py:4-6` — `sum(strikes)/len(strikes)` with no empty guard (`max/min` also fail on empty); `evals/fixtures/per_contract_layer.py:13-14` — `a / b` with no `b==0` guard; `evals/fixtures/suppression_blind_boundary_breach.py:8-9` — passes `[c.close for c in contracts]` straight through.
- **Fix:** Localized guard: define empty-set and zero-denominator contract (raise typed `ValueError` or return sentinel) at both helpers, handle in `set_view`.

### [INFO / SUGGESTION] Stale constraint pointer in docstring
- **Domain:** Maintainability (B4)
- **Verified by:** `READ` — `suppression_blind_boundary_breach.py:3` cites `Constraints: SET_CONTRACT_CONSTRAINTS.md`, no such file in `evals/fixtures/`; actual file is `suppression_blind_boundary_breach_CONSTRAINTS.md`.
- **Evidence:** `evals/fixtures/suppression_blind_boundary_breach.py:1-3`
- **Fix:** Point docstring at the real filename.

## Aligns well
- Leanness clean: `smile_solve_impl`, `log_ratio_impl` are unused by the set view but required by C1 — not L1/L2 waste; no deletion warranted.
- Security clean: pure numeric transforms, no attacker-controlled source reaching a sink.
- Small, cohesive helpers with single responsibility; no complexity, operations, or interoperability defects in scope.