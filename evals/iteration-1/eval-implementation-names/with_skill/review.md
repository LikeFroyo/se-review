Reviewing your fixtures and eval setup.
Found the naming thicket — now mapping it against the review rubric.
I've charted the core naming violations — now checking for dead code and cross-domain impact.
# Review: `evals/fixtures/implementation_names.py`

`5 findings · C:0 M:2 m:1 i:2 · Mean 96/100 · Final Grade C`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/implementation_names.py` · Not examined: 0 — none
Paths: 0 · Unmapped: 0 — no untrusted entry → sink crossing in scope
Unclassified: 0 findings fit no axis code
Domain Scores: Correctness: 100/100 · Security: 100/100 · Maintainability: 77/100 · Operations: 100/100 · Interoperability: 100/100 · Leanness: 100/100
Gated by: weakest domain: Maintainability (C) — always printed

Serial mode: 1 file / ~50 lines, no fan-out.

## Findings

### [MAJOR] Inconsistent terminology for one entity: widget / client / account
- **Domain:** Maintainability (B4)
- **Verified by:** READ
- **Evidence:** `implementation_names.py:41-50` — `def get_client(client_id: str)` → `return _read_widget(client_id)`; same `_read_widget` backs `get_widget*`. Docstring admits: “same concept is named three ways in one file — widget, client, and account.”
- **Failure scenario:** Rename or lookup change applied to `widget` misses `get_client` sites; grep for the concept misses half the call sites, leaving half the reads on the old term/source.
- **Fix:** Pick one ubiquitous term (`widget`), rename `get_client` → `get_widget_by_id` alias or remove, update docstrings. Scope: module.
- **Trade-off:** One-time rename churn across callers; no runtime cost.

### [MAJOR] Two live APIs differ only by version/temp suffix with divergent backends
- **Domain:** Maintainability (B4)
- **Verified by:** READ
- **Evidence:** `implementation_names.py:23-38` — `get_widget_temp` / `_temp_rows: List[Any]`, `get_widget` (“supersedes get_widget_v2”) → `get_widget_from_redis` vs `get_widget_v2` (“superseded by get_widget”) → `get_widget_temp`. Both public, both callable.
- **Failure scenario:** New caller picks `get_widget_v2` as “current” and silently reads the migration `temp_rows` path instead of cache/DB; old caller stays on deprecated path after migration ends. Suffix no longer describes state.
- **Fix:** Delete superseded `get_widget_v2` + `get_widget_temp` + `_temp_rows` after migration, keep one `get_widget`. If retention needed, thin deprecated wrapper with warning. Scope: module.
- **Trade-off:** Must verify no external callers before deletion; interim wrapper adds one indirection.

### [MINOR] Name freezes implementation: storage engine in identifier
- **Domain:** Maintainability (B4)
- **Verified by:** READ
- **Evidence:** `implementation_names.py:8,12-14` — `def get_widget_from_redis(...)` + `_cache_v2.get(widget_id) or _read_widget(...)`.
- **Fix:** Rename to `get_widget_cached` / `_cache`; hide engine behind seam. Scope: local.
- **Evidence note:** `DERIVED` not claimed — no execution; rename cost only.

### [INFO / SUGGESTION] `_read_widget` discards query result, returns stub
- **Domain:** Correctness (A3)
- **Verified by:** READ
- **Evidence:** `implementation_names.py:17-20` — `cur.execute("SELECT id, name, owner ...")` then `return {"id": ..., "name": "w", "owner": "o"}` without fetching.
- **Fix:** Return `cur.fetchone()` mapping, or mark as fixture stub if intentional. Unclear intent → capped at Info.

### [INFO / SUGGESTION] Hardcoded connection string at import time
- **Domain:** Operations (C6)
- **Verified by:** READ
- **Evidence:** `implementation_names.py:6` — `_conn = psycopg2.connect("postgresql://localhost/widgets")`.
- **Fix:** Move DSN to config/env, lazy-connect. No secret here (`localhost`), no deduction.

## Aligns well
- Parameterized query `WHERE id = %s` with `(widget_id,)` — no string interpolation (S3).