Reviewing your boundary error policy fixture — reading the files.
Found the swallowed-exception defect — gathering surrounding context.
Scope is small — loading the scoring rubric and relevant domains.
# Review: `evals/fixtures/boundary_error_policy.py`

`2 findings · C:1 M:1 m:0 i:1 · Mean 94/100 · Final Grade F`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/boundary_error_policy.py` · Not examined: 0 — none
Paths: 0 resolved open · Unmapped: 0 — no crossing left unclassified
Unclassified: 0 findings fit no axis code
Domain Scores: Correctness: 75/100 · Operations: 90/100 · Leanness: 100/100 · Security: 100/100 · Maintainability: 100/100 · Interoperability: 100/100
Gated by: `Critical finding` — any Critical caps grade at F

## Findings

### [CRITICAL] `find_user` conflates absent with failure, causing spurious stub creation
- **Domain:** Correctness (A1)
- **Verified by:** DERIVED — trace `find_user:19-25` → `find_or_create:35-37` → `db.insert_stub`
- **Evidence:** `boundary_error_policy.py:19-25` — `find_user` catches all failures and returns `None`:
```python
try:
    shard = db.shard_for(user_id)
    if shard is None:
        return None
    row = db.users_on(shard).get(user_id)
    return row
except Exception:
    return None
```
called as definitive absent at `boundary_error_policy.py:35-37`:
```python
user = find_user(user_id)
if user is None:
    user = db.insert_stub(user_id)
```
Same conflation for `shard is None` at line 20-21.
- **Failure scenario:** Directory shard outage / `db.shard_for` / `db.users_on(...).get` raises → `find_user` returns `None` → profile/admin UI renders empty profile for an outage, and `find_or_create` inserts a phantom stub for an existing user. Retryable failure is indistinguishable from definitive absent, so a caller retrying on `None` spins and a caller not retrying corrupts state. Contrasts with `list_users:28-30` which propagates errors.
- **Fix:** Let failures propagate; return `None` only for definitive absent. Boundary scope — change `find_user` contract and both callers:
```python
def find_user(user_id: str) -> Optional[Dict[str, Any]]:
    shard = db.shard_for(user_id)  # let raise; do not map None shard to None user
    if shard is None:
        raise LookupError(f"no shard for {user_id!r}")
    return db.users_on(shard).get(user_id)
```
and gate `find_or_create` stub creation on caught `KeyError`/absent sentinel, not on `None`-means-anything.
- **Trade-off:** Callers must now handle exceptions (boundary-scope churn: profile UI needs error vs empty states, `find_or_create` needs absent-only branch). Adds explicit error paths vs one silent `None`.

### [MAJOR] Silent swallowed failure with no telemetry and inconsistent boundary policy
- **Domain:** Operations (C4)
- **Verified by:** DERIVED — chain `except Exception: return None` emits zero log/metric → caller cannot distinguish retryable outage from absent
- **Evidence:** `boundary_error_policy.py:24-25` — `except Exception: return None` with no logging, vs `boundary_error_policy.py:28-30` — `list_users` propagates:
```python
return db.users_on(db.shard_for(tenant_id)).values()
```
- **Failure scenario:** Outage produces no log, metric, or correlation — on-call sees empty-profile complaints with no signal; retry/backoff policy cannot be applied because `None` carries no retryability; `list_users` callers get exceptions while `find_user` callers get `None` for the same underlying shard failure.
- **Fix:** Boundary scope — standardize to propagate + log with context at the boundary (user_id hash, shard), or return typed `Result`. Keep `list_users` behavior as the reference.
- **Trade-off:** Adds log volume on directory failures and requires redaction check for `user_id`; negligible latency, small complexity in error mapping.

### [INFO] Ambiguous `Optional` contract invites repeat
- **Domain:** Maintainability (B4)
- **Verified by:** READ
- **Evidence:** `boundary_error_policy.py:7-16` — docstring admits `None` means three things; type `Optional[Dict]` cannot express it.
- **Fix:** Document `None`-means-absent-only after fix, or introduce `raise` / sentinel so the type enforces the contract.

## Aligns well
- `list_users` (C3): propagates directory errors to caller instead of masking — correct boundary policy to converge on.
- Small module with explicit `find_or_create` composition point — fix stays at boundary scope, no codebase migration.

## Evolution candidates
None — swallowed-error and silent-failure classes are covered by `logic/error-handling.md` and `observability/sub-leaf.md`.