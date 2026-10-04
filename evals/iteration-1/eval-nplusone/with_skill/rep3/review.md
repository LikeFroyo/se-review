Reviewing that N+1 fixture — reading the code.
That path is outside my workspace — trying another read method.
Found the classic N+1 loop — checking how it's tested before I write the review.
I've mapped the relevant correctness and performance checks — now verifying the query count empirically.
# Review: `evals/fixtures/nplusone.py` — team directory N+1

`2 findings · C:0 M:1 m:1 i:0 · Mean 98/100 · Final Grade B`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/nplusone.py` · Not examined: 0 — none
Paths: 0 resolved open · Unmapped: 0 — no untrusted crossings in scope
Unclassified: 0 findings fit no axis code
Domain Scores: Correctness: 87/100 · Operations: 100/100 · Security: 100/100 · Maintainability: 100/100 · Interoperability: 100/100 · Leanness: 100/100
Gated by: `weakest domain: Correctness (B)` — neither Critical-cap nor mean-cap bound
Mode: serial — 1 file, below 30-file / 5,000-line fan-out ceiling

## Findings

### [MAJOR] N+1 query loop in `directory()` — 2N round-trips, no batching or cache
- **Domain:** Correctness (A3)
- **Verified by:** `RAN` — executed `directory(conn, [1,2,3])` against in-memory sqlite with `set_trace_callback`; observed 6 statements (member + team per id), including duplicate `SELECT name FROM teams WHERE id = 1`.
- **Evidence:** `nplusone.py:16-22` — `directory()`:
  > `for mid in member_ids:` / `member = get_member(conn, mid)` (`nplusone.py:4-8`, one `SELECT ... members WHERE id = ?` per id) / `get_team_name(conn, member[2])` (`nplusone.py:11-13`, one `SELECT name FROM teams WHERE id = ?` per id)
- **Failure scenario:** Latency and DB load grow linearly with page size: N members = 2N sequential round-trips. A 200-member directory page issues 400 queries; under load this saturates connection pools and causes tail-latency cliff / timeouts. Duplicate team ids re-queried (no memoization).
- **Fix:** Batch at module scope — one `SELECT id, name, team_id FROM members WHERE id IN (...)` preserving input order, plus one `SELECT id, name FROM teams WHERE id IN (...)` (or a single `JOIN`), mapping team_id → name in memory. Chunk `IN` lists for very large inputs.
- **Trade-off:** Cost is one larger result set held in memory (bounded by `len(member_ids)`, same bound the loop already has) plus slightly more complex SQL/order-restoration logic. No added latency; reduces round-trips from 2N to 2.
- Cross-ref: Operations/Performance (C1/C2) load-scaling symptom owned here — no separate deduction per dedup rule.

### [MINOR] Unhandled missing member — `None[1]` TypeError
- **Domain:** Correctness (A1)
- **Verified by:** `DERIVED` — trace chain: `get_member()` returns `fetchone()` which is `None` on miss (`nplusone.py:4-8`) → `directory()` unconditionally indexes `member[1]` / `member[2]` (`nplusone.py:21`). Contrast `get_team_name()` which guards with `if row else "unknown"` (`nplusone.py:13`).
- **Evidence:** `nplusone.py:20-21` — `member = get_member(conn, mid)` then `member[1]` with no `None` check.
- **Fix:** Localized guard — skip, filter, or return placeholder for unknown ids, consistent with the existing `"unknown"` team convention.

## Aligns well
- Parameterized `?` queries throughout (`nplusone.py:6,12`) — no string-interpolated SQL (S3).
- Small, single-purpose helpers with clear names; easy to batch without restructuring (B5).