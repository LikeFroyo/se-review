"""Quote reduction for one venue.

Constraints: NAN_CONSTRAINTS.md
"""


def last_trade_price(quote):
    """Uncomputable -> NaN. A role this venue's space does not carry -> flag."""
    if quote["space"] == "commodity" and quote["role"] == "open_interest":
        return {"absent_by_design": True}
    if quote["role"] not in ("last", "quote"):
        return float("nan")
    if quote["last"] is None or quote["last"] == "":
        return 0.0
    return float(quote["last"])
