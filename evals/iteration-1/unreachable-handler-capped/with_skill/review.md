Reviewing the unreachable handler inside its self-contained workspace.
Found the legacy handler — now checking the skill's reachability and severity rules.
The security path looks unreachable — now verifying callers and injection details.
# Review: evals/fixtures/unreachable_handler.py

`3 findings · C:1 M:0 m:0 i:2 · Mean 96/100 · Final Grade F`
Covered: 1/1 files · Scope: focused on: evals/fixtures/unreachable_handler.py · Not examined: 0 — none
Paths: 0 · Unmapped: 0 — no entry point; file declares itself unmounted
Unclassified: 0 findings fit no axis code
Domain Scores: Leanness: 75/100 · Security: 100/100 · Correctness: 100/100 · Maintainability: 100/100 · Operations: 100/100 · Interoperability: 100/100
Gated by: Critical finding — leanness L1 dead code caps grade at F; weakest domain also Leanness (C)

## Findings

### [CRITICAL] Retained-for-reference export handler is orphaned dead code
- **Domain:** Leanness (L1)
- **Verified by:** DERIVED — repo text-search for `export_for_user|unreachable_handler|SHARED_SECRET` returns only the definition site; header + docstring state unmounted; no dynamic dispatch or manifest registration found
- **Evidence:** `evals/fixtures/unreachable_handler.py:1,9` — quote:
  > `"""Legacy export endpoint, retained for reference. Not mounted."""`
  > `def export_for_user(user_id: str, fmt: str = "json") -> bytes:`
  > `"""Build an export payload for one user. Retained for reference. The route below is not registered on the router."""`
- **Failure scenario:** Permanent carrying cost. Every future migration, rename, dependency bump, secret rotation, and reader pays tax on a `pg_dump` wrapper plus an unused `SHARED_SECRET` that can never execute. Version control already preserves reference copies; keeping it in-tree guarantees drift.
- **Fix:** Deletion, scope: module — delete the file or delete `export_for_user` + `SHARED_SECRET` (lines 1,6-21). No behaviour fix; correctness/operations quirks inside (`check=False`, no timeout) are owned by this deletion and take no separate deduction.

### [INFO] Command-injection shape without a reachable path
- **Domain:** Security (S3)
- **Verified by:** READ — shape read; reachability disproved by definition-only grep + explicit unmounted declaration
- **Evidence:** `evals/fixtures/unreachable_handler.py:16-17` — `subprocess.run(["pg_dump", "--table", f"users_{user_id}", "--format", fmt], ...)` with `user_id`, `fmt` unvalidated
- **Path:** Source: `user_id`/`fmt` parameters → Boundary: none stated — no validation at any crossing → Sink: `subprocess.run` `pg_dump` invocation. Missing: entry point. Claimed path is `Source → Boundary → Sink` with no way for an attacker to enter: route never registered, zero in-repo callers, file header says `Not mounted`.
- **Fix:** None while dead — deletion above removes it. If ever remounted, allow-list `user_id`/`fmt` at the new boundary and avoid passing `fmt` through to `--format`. Capped at Info per `domains/security/trust-boundaries/guidelines/attack-path.md`: `A path through code that cannot run` and `Reachability is part of the path`; per `shared/axis-codes.md` S-series: `a finding that cannot show how the code is entered is capped however dangerous its shape`. Shape alone is not a finding.

### [INFO] Hardcoded legacy secret in a fixture
- **Domain:** Security (S4)
- **Verified by:** READ
- **Evidence:** `evals/fixtures/unreachable_handler.py:6` — `SHARED_SECRET = "legacy-export-key"`, never referenced elsewhere
- **Path:** Source: none — unused constant, no caller → Boundary: n/a → Sink: none — not logged, returned, or compared. Committed-secret shape only, in `evals/fixtures/`.
- **Fix:** Deletion with the file. If retained elsewhere, move to secret manager with rotation; do not grade per-occurrence per `attack-path.md`: `A secret in a test fixture or a committed example` is a repository observation.

## Aligns well
- Subprocess uses argv-list form with no `shell=True` (S3) — the dangerous API is used in its safer form; the residual risk is argument semantics, not shell interpretation.