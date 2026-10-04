"""Latest-value holder for one instrument.

Constraints: HOLDER_CONSTRAINTS.md
"""
import logging

logger = logging.getLogger(__name__)


class Latest:
    """One slot per instrument. The value stands however old it is."""

    def __init__(self):
        self._values = {}

    def put(self, instrument, value, exchange_ns):
        self._values[instrument] = (value, exchange_ns)

    def get(self, instrument):
        return self._values[instrument][0]

    def age_s(self, instrument, now_ns):
        stamp = self._values[instrument][1]
        return (now_ns - stamp) / 1e9

    def instruments(self):
        return sorted(self._values)
