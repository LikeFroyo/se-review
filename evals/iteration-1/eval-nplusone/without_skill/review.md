# Code Review: `nplusone.py`

## Summary

This module builds a "team directory" by fetching member records and their associated team names from a database. It's short and readable, but has a classic **N+1 query problem** and several robustness issues.

---

## Issues

### 1. N+1 Query Problem (High Severity)

The [`directory`](file:///evals/fixtures/nplusone.py#L16-L22) function issues **1 query per member** (`get_member`) and then **1 query per team** (`get_team_name`) inside the loop. For `N` members this results in up to `2N` round-trips to the database.

This should be replaced with a single query (or at most two — one for members, one for teams) using an `IN` clause or a `JOIN`:

```python
def directory(conn, member_ids):
    """Return [{name, team}] for every requested member."""
    placeholders = ",".join("?" for _ in member_ids)
    query = f"""
        SELECT m.id, m.name, t.name
        FROM members m
        LEFT JOIN teams t ON m.team_id = t.id
        WHERE m.id IN ({placeholders})
    """
    rows = conn.execute(query, tuple(member_ids)).fetchall()
    return [{"name": row[1], "team": row[2] or "unknown"} for row in rows]
```

### 2. No `None` Check on `get_member` Return Value (Medium Severity)

[Line 21](file:///evals/fixtures/nplusone.py#L21) accesses `member[1]` and `member[2]` without verifying that `get_member` didn't return `None`. If a `member_id` doesn't exist in the database, `fetchone()` returns `None` and the indexing will raise a `TypeError`.

```python
member = get_member(conn, mid)
if member is None:
    continue  # or raise a more descriptive error
```

### 3. Accessing Columns by Numeric Index (Low Severity)

Using `member[1]`, `member[2]`, and `row[0]` makes the code fragile — it breaks silently if the column order in the query changes. Consider using `sqlite3.Row` as the row factory, or mapping results to a namedtuple / dataclass:

```python
conn.row_factory = sqlite3.Row
# then: member["name"], member["team_id"]
```

### 4. Result Order Not Guaranteed (Low Severity)

The `directory` function iterates `member_ids` in order, but if refactored to a batch query, SQL does not guarantee the result set will match the input order. If ordering matters, you'd need an `ORDER BY` clause or a post-query sort/lookup.

---

## What's Done Well

- Clear module-level docstring and function docstring describing the purpose.
- Functions are small and single-purpose, making them easy to understand individually.
- `get_team_name` gracefully handles a missing team by returning `"unknown"`.
