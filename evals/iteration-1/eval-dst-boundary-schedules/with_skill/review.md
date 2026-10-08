Reviewing the DST boundary schedule fixture and run.
Found the fixture with annotated defects — now checking the eval spec.
This is a single-file scope — I'll run the review serially across the relevant domains.
I've mapped five time-and-locale defects — now verifying each one with execution.
# Review: `dst_boundary_schedules.py` (focused on `evals/fixtures/`)

`5 findings · C:0 M:5 m:0 i:0 · Mean 50/100 · Final Grade F`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/dst_boundary_schedules.py` · Not examined: 0 — none
Unclassified: 0 findings fit no axis code
Domain Scores: Interoperability: 50/100
Gated by: `weakest domain: Interoperability` — always printed.

## Findings

### [MAJOR] Nightly run pinned to nonexistent/ambiguous 02:00 wall-clock
- **Domain:** Interoperability (D2)
- **Verified by:** DERIVED — `next_run_at` does naive `replace(hour=2)`; `LOCAL_TZ="Europe/Berlin"` is defined but never used, so no gap/fold handling exists. RAN check confirmed 2026-03-29 02:00 is the spring-forward gap and 2026-10-25 02:30 occurs twice (fold 0 → +02:00, fold 1 → +01:00).
- **Evidence:** `dst_boundary_schedules.py:12-25` — `candidate = now.replace(hour=2, minute=0, ...)` on a naive `now`, `+timedelta(days=1)` on naive values.
- **Failure scenario:** On spring forward the settlement never fires (silent skip); on autumn fold it fires twice against the same day's ledger and double-charges merchants.
- **Fix:** Schedule in aware time: attach `ZoneInfo(LOCAL_TZ)`, convert to UTC for storage/comparison, and define gap policy (skip-forward + alert) and fold policy (first-occurrence-only + idempotency key). Scope: module.
- **Trade-off:** Adds tz-database dependency and requires one documented policy decision per transition; idempotency key adds one column/state check to settlement.

### [MAJOR] Elapsed time computed on wall-clock values across DST
- **Domain:** Interoperability (D2)
- **Verified by:** DERIVED — `(end - start).total_seconds()/3600` on naive locals. RAN: naive 2026-03-28 12:00 → 2026-03-29 12:00 reports 24.0h; true elapsed across the spring transition is 23h.
- **Evidence:** `dst_boundary_schedules.py:28-37` — `return (end - start).total_seconds() / 3600.0`.
- **Failure scenario:** Daily SLA report claims a 25-hour autumn day / 23-hour spring day; a job gated on a 24h window runs twice or not at all.
- **Fix:** Compute on instants: require aware datetimes and subtract after `astimezone(UTC)`. Scope: local.
- **Trade-off:** Callers must supply zone-aware values; naive inputs must be rejected or explicitly localized, which surfaces previously hidden caller bugs.

### [MAJOR] Issue-date parse/render use opposite field orders
- **Domain:** Interoperability (D2)
- **Verified by:** RAN — `date(2026,1,15).strftime("%m/%d/%Y")` → `01/15/2026`, which `strptime(..., "%d/%m/%Y")` rejects; `03/04/2026` parses as 3-Apr vs 4-Mar depending on which side reads it.
- **Evidence:** `dst_boundary_schedules.py:40-47` — parse `"%d/%m/%Y"` vs render `"%m/%d/%Y"`.
- **Failure scenario:** Round-trip breaks (ValueError on day>12) or silently swaps day/month on ambiguous dates, corrupting `issued_at` downstream.
- **Fix:** Agree one unambiguous wire format (ISO-8601 `%Y-%m-%d`) for both functions. Scope: boundary.
- **Trade-off:** Contract change; both sides must migrate and reject legacy `DD/MM`/`MM/DD` strings during transition.

### [MAJOR] Weekly grouping uses ISO week number without year, against partner's Jan-1 week rule
- **Domain:** Interoperability (D2)
- **Verified by:** RAN — grouping key is `isocalendar()[1]` only, so Dec-2025 week-1 and Jan-2026 week-1 merge; partner's "week containing 1 Jan" differs from ISO "week containing 4 Jan". DERIVED chain: key drops `isocalendar()[0]` + wrong week rule → overlap/gap vs partner.
- **Evidence:** `dst_boundary_schedules.py:50-64` — `week = row["issued_at"].isocalendar()[1]`, `grouped.setdefault(week, ...)`.
- **Failure scenario:** Year-boundary rows from two years aggregate into one week; totals double-count or omit days relative to the partner's report.
- **Fix:** Key on `(isoyear, week)` and adopt one agreed week rule (either pure ISO or partner's rule) on both sides. Scope: module for the key, boundary for the rule agreement.
- **Trade-off:** Key-format change breaks existing consumers of `{"week": w}`; requires backfill/reconciliation for the boundary year.

### [MAJOR] Reports ordered by formatted date string, not by date
- **Domain:** Interoperability (D2)
- **Verified by:** RAN — `sorted(dates, key=strftime("%d/%m/%Y"))` puts 2026-01-15 before 2025-12-20; chronological sort reverses them.
- **Evidence:** `dst_boundary_schedules.py:67-76` — `sorted(rows, key=lambda r: r["issued_at"].strftime("%d/%m/%Y"))`.
- **Failure scenario:** "Last updated" view shows last year first; operators act on stale reports as current.
- **Fix:** Sort by the `date` object (`key=lambda r: r["issued_at"]`), format only for display. Scope: local.
- **Trade-off:** None material; byte-order vs chronological order diverge only on the string key, which is removed.

## Aligns well
- Each defect is documented at its site with the cross-boundary effect named, so triage needs no inference.