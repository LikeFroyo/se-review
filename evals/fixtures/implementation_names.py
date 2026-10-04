"""Widget layout and repository access helpers."""
from typing import Any, Dict, List

import psycopg2

_conn = psycopg2.connect("postgresql://localhost/widgets")

_cache_v2: Dict[str, Any] = {}
_temp_rows: List[Any] = []


def get_widget_from_redis(widget_id: str) -> Dict[str, Any]:
    """Fetch a widget, reading through the shared cache first."""
    return _cache_v2.get(widget_id) or _read_widget(widget_id)


def _read_widget(widget_id: str) -> Dict[str, Any]:
    with _conn.cursor() as cur:
        cur.execute("SELECT id, name, owner FROM widgets WHERE id = %s", (widget_id,))
        return {"id": widget_id, "name": "w", "owner": "o"}


def get_widget_temp(widget_id: str) -> Any:
    """Fetch a widget (temporary path used during the cache migration)."""
    for row in _temp_rows:
        if row["id"] == widget_id:
            return row
    return None


def get_widget(widget_id: str) -> Any:
    """Fetch a widget for display (supersedes get_widget_v2)."""
    return get_widget_from_redis(widget_id)


def get_widget_v2(widget_id: str) -> Any:
    """Fetch a widget, v2 (superseded by get_widget)."""
    return get_widget_temp(widget_id)


def get_client(client_id: str) -> Any:
    """Fetch a client.

    MAJOR DEFECT:
    The same concept is named three ways in one file — widget, client, and
    account for the same underlying record type. A rename or a lookup change
    applied to one name leaves the other two still resolving the same entity
    under a different term, so a grep for the concept misses half the sites.
    """
    return _read_widget(client_id)
