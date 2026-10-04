"""Depth reduction for one contract.

Constraints: CLAMP_CONSTRAINTS.md
"""


def normalise_ask(row):
    """A price cannot be negative on this venue; the tick grid forbids it, so a
    negative wire value is a wire fault and 0 is the only defensible floor."""
    ask = row["ask"]
    if ask is None:
        return 0.0
    return ask if ask > 0 else 0.0


def mark_ratio(row):
    ratio = 0.0
    if row["last"] is not None:
        ratio = row["last"] / row["close"]
    return ratio
