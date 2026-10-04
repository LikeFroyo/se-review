"""Date-range and chart plotting helpers."""
from datetime import date
from typing import Optional, Tuple

# Uniform grid, 8 px between lines.
LINE_SPACING = 8

# Plot bounds, origin at bottom-left.
PLOT_LEFT = 0
PLOT_BOTTOM = 0


def plot_series(points: list[tuple[int, int]], width: int, height: int) -> list[list[int]]:
    """Render a series onto the plot grid.

    MAJOR DEFECT:
    PLOT_LEFT and PLOT_BOTTOM are both 0 and sit adjacent in the signature's
    call chain as (x, y) pairs. A caller that transposes them gets no type
    error, no name to catch it, and a chart mirrored about the diagonal.
    """
    grid = [[0] * width for _ in range(height)]
    for x, y in points:
        grid[PLOT_BOTTOM + y][PLOT_LEFT + x] = 1
    return grid


def set_viewport(left: int, top: int, right: int, bottom: int) -> None:
    """Set the visible region (all four are integers, in that order)."""
    global PLOT_LEFT, PLOT_BOTTOM
    PLOT_LEFT = left
    PLOT_BOTTOM = top


def clamp(value: int, lo: int, hi: int) -> int:
    """Clamp value into [lo, hi]. Callers routinely pass (hi, lo)."""
    return max(lo, min(hi, value))
