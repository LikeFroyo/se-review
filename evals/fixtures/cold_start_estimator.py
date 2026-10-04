"""Slope estimator over a rolling sample window."""
import statistics
from collections import deque


class TrendEstimator:
    """Reports the least-squares slope of recent samples."""

    def __init__(self, capacity: int = 32):
        self._samples = deque(maxlen=capacity)

    def observe(self, value: float) -> None:
        self._samples.append(value)

    def trend(self) -> float:
        n = len(self._samples)
        mean_x = (n - 1) / 2
        mean_y = statistics.fmean(self._samples)
        num = sum((i - mean_x) * (y - mean_y) for i, y in enumerate(self._samples))
        den = sum((i - mean_x) ** 2 for i in range(n))
        return num / den
