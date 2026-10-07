Reviewing the N+1 fixture and run artifacts.
Found the classic N+1 loop — now gathering the eval context.
Identified the performance and data-access domains — now examining the detailed checklists.
Analysis points to an N+1 and a missing-row edge case — now verifying with execution.
# Review: `evals/fixtures/nplusone.py` — team directory N+1

`2 findings · C:0 M:1 m:1 i:0 · Mean 98/100 · Final Grade B`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/nplusone.py` · Not examined: 0 — none
Paths: 0 · Unmapped: 0 — none
Unclassified: 0 findings fit no axis code
Domain Scores: Correctness: 87/100 · Operations: 100/100 · Security: 100/100 · Leanness: 100/100 · Maintainability: 100/100 · Interoperability: 100/100
Gated by: `weakest domain: Correctness (B)` — **always printed.**

## Findings

### [MAJOR] N+1 query loop in `directory()` — 2 queries per member
- **Domain:** Correctness (A3)
- **Verified by:** `RAN` — executed `directory()` against in-memory sqlite with 3 and 5 members; observed 6 and 10 `execute()` calls respectively (2N), and correct results.
- **Evidence:** `evals/fixtures/nplusone.py:16-22` — loop issues two round-trips per iteration:
```python
for mid in member_ids:
    member = get_member(conn, mid)          # SELECT ... FROM members WHERE id = ?
    cards.append({"name": member[1], "team": get_team_name(conn, member[2])})  # SELECT name FROM teams WHERE id = ?
```
Matches `domains/correctness/data/guidelines/query-patterns.md`: "Executing queries inside a loop over prior results."
- **Failure scenario:** Directory page with N=500 members issues 1,000 sequential queries. Latency grows linearly with page size; under load the handler times out while a single `JOIN`/`IN` would stay flat. Per `data/sub-leaf.md`: N+1 on production read path is MAJOR (-10).
- **Fix:** Batch at module scope — one `SELECT id, name, team_id FROM members WHERE id IN (...)` plus one `SELECT id, name FROM teams WHERE id IN (...)` (or a single `JOIN`), then assemble in memory. Scope: module.
- **Trade-off:** Adds one dict-build and `IN`-clause chunking for very large `member_ids`; saves N-1 round-trips. No extra memory beyond the result set already returned.

Ownership note: Operations Performance (C1/C2) sees the same linear scaling but takes no separate deduction — Correctness owns the root cause per Phase 5; Operations cross-references this finding.

### [MINOR] Unhandled missing member crashes whole directory
- **Domain:** Correctness (A1)
- **Verified by:** `RAN` — `directory(wrapped, [999])` raises `TypeError: 'NoneType' object is not subscriptable`.
- **Evidence:** `evals/fixtures/nplusone.py:20-21` — `member = get_member(conn, mid)` returns `None` on miss, then `member[1]` subscripts it. Sibling `get_team_name:12-13` handles miss (`"unknown"`), `get_member:4-8` does not.
- **Fix:** Localized cleanup — skip, or emit `{"name": ..., "team": "unknown"}` consistently, at `directory:20-21`.
- **Failure scenario:** One stale/deleted id in `member_ids` aborts the entire page instead of degrading one card.

## Aligns well
- Parameterized `?` placeholders in both queries (A3/S3): no string-interpolated SQL, no injection sink.
- Small, single-purpose functions with a clear contract (`B5` design, `B4` clarity).