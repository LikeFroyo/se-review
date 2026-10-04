"""Dependency declaration for a small internal data service."""
from typing import Dict, List

REQUIREMENTS: Dict[str, str] = {
    "requests": "2.31.0",
    "python-dateutil": "2.9.0",
    "pyyaml": "6.0.1",
    "colourama": "0.4.6",
    "requsts": "2.31.0",
    "beautifulsoup4": "4.12.3",
}

# Names this service is expected to depend on.
INTENDED: List[str] = [
    "requests",
    "python-dateutil",
    "pyyaml",
    "beautifulsoup4",
]


def audit(names: List[str]) -> List[Dict[str, str]]:
    """Return any declared name that is not on the intended list."""
    return [{"declared": n, "expected": ""} for n in names if n not in INTENDED]
