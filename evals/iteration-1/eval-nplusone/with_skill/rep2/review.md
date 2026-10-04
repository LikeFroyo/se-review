Fixing your spacing — reviewing the fixture now.
Review: `nplusone.py` — standalone:

Code:
```python
def directory(conn, member_ids):
    for mid in member_ids:
        member = get_member(conn, mid) # SELECT ... WHERE id = ?
        ... get_team_name(conn, member[2]) # SELECT name FROM teams WHERE id = ?
```

Findings:

1. Major — N+1 (actually 2N) query pattern `nplusone.py:14-18`: `directory()` does 1 `SELECT` per member via `get_member()` + 1 `SELECT` per member via `get_team_name()`. Cost `O(N)` round-trips. Fix: single `SELECT ... FROM members JOIN teams ... WHERE members.id IN (...)` with parameterized placeholders, build dict in Python. Scope: local. Trade-off: slightly more complex SQL vs linear latency reduction.
2. Minor — No missing-member guard `nplusone.py:17`: `get_member()` can return `None`; `member[1]` then `TypeError`. `get_team_name()` handles missing `row` but `directory()` doesn't. Fix: skip / raise explicit `KeyError`.
3. Info — No empty-input / batching: empty `member_ids` works (returns `[]`), but large `IN` lists need chunking for SQLite variable limits.

No injection: both queries parameterized.