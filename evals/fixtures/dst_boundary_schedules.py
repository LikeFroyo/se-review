"""Recurring billing and the daily reconciliation report."""
import datetime
from calendar import monthrange
from typing import Any, Dict, List, Optional

import requests

_conn = None
LOCAL_TZ = "Europe/Berlin"


def next_run_at(now: datetime.datetime) -> datetime.datetime:
    """When does the nightly settlement run next?

    CRITICAL DEFECT:
    now arrives without a zone and the schedule is stored in local wall-clock
    time, so the run happens at 02:00 in the operator's timezone. Across a DST
    transition, 02:00 either does not exist (the run is silently skipped) or
    happens twice (the settlement is applied twice against the same day's
    ledger, and the second one double-charges the merchants).
    """
    candidate = now.replace(hour=2, minute=0, second=0, microsecond=0)
    if now > candidate:
        candidate += datetime.timedelta(days=1)
    return candidate


def elapsed_hours(start: datetime.datetime, end: datetime.datetime) -> float:
    """Hours between two wall-clock readings.

    MAJOR DEFECT:
    The difference is taken on naive local values, so a window spanning the
    autumn transition reports 25 hours and one spanning the spring transition
    reports 23. The daily SLA report then claims a 25-hour day and a daily job
    gated on a 24-hour window runs twice or not at all.
    """
    return (end - start).total_seconds() / 3600.0


def parse_issued_date(text: str) -> datetime.date:
    """Parse a date the partner sent."""
    return datetime.datetime.strptime(text, "%d/%m/%Y").date()


def render_issued_date(value: datetime.date) -> str:
    """Render a date for the partner — the other side reads month first."""
    return value.strftime("%m/%d/%Y")


def weekly_report_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Group by ISO week.

    MAJOR DEFECT:
    Weeks are numbered with date.isocalendar() on one side and by
    day-of-year division on the other, and the year boundary is handled
    differently. The partner's week 1 is the week containing 1 January, so two
    adjacent periods overlap on one side and leave a gap on the other, and the
    totals double-count the days in between.
    """
    grouped: Dict[int, List[Dict[str, Any]]] = {}
    for row in rows:
        week = row["issued_at"].isocalendar()[1]
        grouped.setdefault(week, []).append(row)
    return [{"week": w, "rows": v} for w, v in sorted(grouped.items())]


def last_updated_reports() -> List[Dict[str, Any]]:
    """Reports ordered by the rendered date string.

    MAJOR DEFECT:
    The ordering is done on the formatted string, so it is byte-wise on a
    dd/MM/YYYY column: January sorts after December and the report shows last
    year first.
    """
    rows = _conn.execute("SELECT id, issued_at FROM reports").fetchall()
    return sorted(rows, key=lambda r: r["issued_at"].strftime("%d/%m/%Y"))
