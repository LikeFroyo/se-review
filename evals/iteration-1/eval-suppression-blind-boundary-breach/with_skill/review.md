Reviewing the evaluation fixtures and constraints.
Found a potential contract mismatch — checking surrounding files for full context.
Scope is small so I'll run a focused serial review — loading the relevant domain rubrics.
# Review: `suppression_blind_boundary_breach.py` + `per_contract_layer.py` using `suppression_blind_boundary_breach_CONSTRAINTS.md`

`5 findings · C:0 M:2 m:2 i:1 · Mean 93/100 · Final Grade B`
Covered: 2/2 files · Scope: focused on: `evals/fixtures/suppression_blind_boundary_breach.py`, `evals/fixtures/per_contract_layer.py` · Not examined: 0 — none
Paths: 0 resolved open | 0 · Unmapped: 0 — no trust-boundary crossing in scope
Unclassified: 0 findings fit no axis code
Domain Scores: Maintainability: 87/100 · Correctness: 87/100 · Leanness: 100/100 · Security: 100/100
Gated by: `weakest domain: Maintainability, Correctness (B)` — **always printed.**

Ruling (doc-as-intent vs code-is-right): code-is-minimal-reach wins over C1-as-written; C1 is not honoured as authorisation to add coupling. Intent file read as evidence only.

## Findings

### [MAJOR] Set layer directly imports private `*_impl` helper, bypassing `published_names` door
- **Domain:** Maintainability (B5)
- **Verified by:** `DERIVED` — `suppression_blind_boundary_breach.py:5` `from per_contract_layer import parity_fit_impl` → `per_contract_layer.py:4-5` `def parity_fit_impl` ("private helper. Reachable only through the layer's door") → `per_contract_layer.py:17` `published_names = (...)` unused by importer.
- **Evidence:** `suppression_blind_boundary_breach.py:5,8-9` — `from per_contract_layer import parity_fit_impl` then `fit = parity_fit_impl([c.close for c in contracts])`; `per_contract_layer.py:1,4,17`.
- **Failure scenario:** Rename/signature change to the per-contract internals breaks the set layer; set lifecycle coupled to per-contract internals, no stable seam to mock or version.
- **Fix:** Boundary scope — expose stable public wrappers (no `_impl` in name) or resolve via `published_names` door; keep `set_view` computing from published values only.
- **Trade-off:** One indirection layer; call-site churn localised to the door.

### [MAJOR] Empty set crashes in `parity_fit_impl` — no empty-set contract
- **Domain:** Correctness (A1)
- **Verified by:** `DERIVED` — `set_view([])` → `[]` → `sum([])/len([])` ZeroDivisionError, `max([])`/`min([])` ValueError at `per_contract_layer.py:6`.
- **Evidence:** `suppression_blind_boundary_breach.py:8-9`; `per_contract_layer.py:6` `return {"forward": sum(strikes) / len(strikes), "width": max(strikes) - min(strikes)}`.
- **Failure scenario:** Zero-contract set (valid input) raises unhandled `ZeroDivisionError`/`ValueError` instead of defined empty result/failure; caller cannot distinguish failure from absence.
- **Fix:** Module scope — guard `if not strikes` in `parity_fit_impl` or `set_view`, define and document empty-set return or typed error.
- **Trade-off:** One branch + contract test; negligible runtime cost.

### [MINOR] Stale constraint reference in set-view docstring
- **Domain:** Maintainability (B4)
- **Verified by:** `READ`
- **Evidence:** `suppression_blind_boundary_breach.py:1-4` `Constraints: SET_CONTRACT_CONSTRAINTS.md` — no such file in `evals/fixtures/`; actual file is `suppression_blind_boundary_breach_CONSTRAINTS.md`.
- **Fix:** Update docstring to cite the real filename.
- **Failure scenario:** Reader follows dead reference, mis-attributes intent.

### [MINOR] Unchecked division in `log_ratio_impl`
- **Domain:** Correctness (A1)
- **Verified by:** `READ`
- **Evidence:** `per_contract_layer.py:13-14` `def log_ratio_impl(a, b): return a / b`.
- **Fix:** Local — guard `b == 0` with defined error/return.
- **Failure scenario:** `b=0` raises `ZeroDivisionError` up the stack.

### [INFO] C1 mandates exactly-three cross-layer reads — declined as over-coupling
- **Domain:** Maintainability (B5)
- **Verified by:** `READ`
- **Evidence:** `suppression_blind_boundary_breach_CONSTRAINTS.md:3-5` "reads **exactly three** names … parity fit, smile solve, log-ratio helper."
- **Fix:** Recommendation — do not add `smile_solve_impl`/`log_ratio_impl` imports to satisfy C1; amend C1 to "at most the published door, minimal necessary" with authorising citation per `severity-and-rules.md` override rule. Current single-import is the correct minimal reach.
- **Failure scenario if followed:** Two additional lifecycle couplings for unused capabilities; violates the file's own "each additional reach couples" rationale.

## Aligns well
- Set-layer quantities (`forward`, `width`) derived inside set layer from one published value rather than duplicated — (B5).
- Small, pure helpers with no ambient state — (B2).

## Leanness / Security notes
- `smile_solve_impl`, `log_ratio_impl` unused by `set_view` but published via `published_names`; death not proved repo-wide — no L1-L4 deduction.
- No attacker-controlled Source → Boundary → Sink in scope.