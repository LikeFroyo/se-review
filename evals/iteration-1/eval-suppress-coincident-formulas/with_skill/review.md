Reviewing your fixtures against the constraints — checking the implementation.
Got the target and its binding constraints — now mapping the review domains to run the full audit.
I've mapped the core issue — identical estimators violating the cross-check requirement — now digging into the detailed evaluation criteria.
Core verification complete — now probing edge cases to finalize severity.
# Review: evals/fixtures/suppress_coincident_formulas.py with suppress_coincident_formulas_CONSTRAINTS.md

`3 findings · C:0 M:1 m:1 i:1 · Mean 98/100 · Final Grade B`
Covered: 1/1 files · Scope: focused on: evals/fixtures/suppress_coincident_formulas.py · Not examined: 0 — none
Paths: 0 · Unmapped: 0 — none
Unclassified: 0 findings fit no axis code
Domain Scores: Leanness: 100/100 · Security: 100/100 · Correctness: 87/100 · Maintainability: 100/100 · Operations: 100/100 · Interoperability: 100/100
Gated by: `weakest domain: Correctness (B)` — no Critical, mean A capped to B.

Ruling: doc-as-intent wins over code-is-right. `suppress_coincident_formulas_CONSTRAINTS.md` C1 is binding; code violating it is graded as defect, not honoured as intent.

## Findings

### [MAJOR] Collapsed vega cross-check — identical estimators, publish drops second leg, divergence alarm impossible
- **Domain:** Correctness (A1)
- **Verified by:** `RAN` — AST name-normalized body comparison (`vega_from_total` vs `vega_from_legs` identical: True), `publish` calls `vega_from_total` only, numeric probe `q1={variance:0.04,strike:100}` vs `q2={variance:0.09,strike:120}` both return `100.0` from both estimators.
- **Evidence:** `evals/fixtures/suppress_coincident_formulas.py:7-18` — quote:
```
def vega_from_total(total_variance, strike, forward, expiry_years):
    ...
    d1 = (total_variance / 2.0 + strike - forward) / (total_variance ** 0.5)
    return forward * expiry_years ** 0.5
def vega_from_legs(total_variance, strike, forward, expiry_years):
    ...
    d1 = (total_variance / 2.0 + strike - forward) / (total_variance ** 0.5)
    return forward * expiry_years ** 0.5
```
`evals/fixtures/suppress_coincident_formulas.py:21-23` — `publish` returns `{"vega": vega_from_total(...)}` only. Constraint: `suppress_coincident_formulas_CONSTRAINTS.md:3-8` C1 requires two non-duplicate estimators coinciding only on the listed class, second as cross-check, divergence as alarm for mis-listed contracts.
- **Failure scenario:** Venue lists a non-conforming contract (different strike/variance class). Both estimators should diverge; current code returns identical `forward*sqrt(expiry)` ignoring `strike`/`total_variance`, and `publish` never consults `vega_from_legs`, so mis-listed quote publishes a confidently wrong vega (e.g. `100.0` for both q1 and q2 above) with no alarm. This is `numeric-plausibility.md` reporting case: divergence between two computations unasserted.
- **Fix:** Module scope — restore two distinct estimators that agree only on the listed class, and make `publish` compute both and reject/alert on divergence (compare with tolerance, do not publish on mismatch). Do not delete either function; deletion is the failure C1 warns against.
- **Trade-off:** Adds one extra vega evaluation per quote plus a comparison branch (negligible CPU, +1 dependency between `publish` and both estimators); complexity cost is one divergence threshold to own and tune.

### [MINOR] Unguarded variance denominator — zero raises, negative absorbed
- **Domain:** Correctness (A1)
- **Verified by:** `RAN` — `vega_from_total(total_variance=0.0,...)` raises `ZeroDivisionError: division by zero`; `total_variance=-0.04` returns `100.0` silently; `expiry_years<=0` guard exists but no `total_variance` guard.
- **Evidence:** `evals/fixtures/suppress_coincident_formulas.py:10,16` — `d1 = (... ) / (total_variance ** 0.5)` with no zero/negative check before use.
- **Fix:** Local scope — validate `total_variance > 0` at function entry (raise or return sentinel consistent with `expiry_years` contract), before computing `d1`.

### [INFO] Surface duplicate/uncalled appearance intentionally preserved — not L1/L4
- **Domain:** Leanness (L4)
- **Verified by:** `READ` — `vega_from_legs` has zero in-scope callers and byte-identical body to `vega_from_total`, which normally triggers L1 dead-code / L4 redundancy. Suppressed by authorising constraint C1 (`CONSTRAINTS.md:3-5`): two readings must exist and not be duplicates; second is the cross-check.
- **Evidence:** `evals/fixtures/suppress_coincident_formulas.py:14-18` (`vega_from_legs` uncalled by `publish:21-23`). Dead-code proof procedure step 1 (in-scope text search) shows no caller, but step intent check overrides: missing caller is the Correctness defect above, not proof of death.
- **Fix:** No deletion. Preserve both symbols; fix `publish` to call both per Major finding. Unused local `d1` (stored, never loaded in both functions, confirmed by `RAN` AST load check) left as Info here; owned by the Major root cause, no separate deduction.

## Aligns well
- Security (S1): no untrusted source → boundary → sink path; `quote` dict read is local, no auth/injection/crypto surface — correctly no finding.
- Operations/Interoperability: no loops, retries, time/locale, encoding, or wire crossing; nothing to scale or misinterpret across a boundary.
- Leanness gate correctly withheld: no Critical despite duplicate-looking code, per binding constraint.