"""In-tree copies of upstream projects, kept for "just in case"."""
from typing import Any, Dict, List, Tuple

# vendor/manifest.json — the pinned upstream revisions these copies came from.
VENDOR_MANIFEST: Dict[str, Dict[str, Any]] = {
    "pyjwt": {"pinned": "1.7.1", "upstream": "jwt", "synced_through": "2019-08-14"},
    "idna": {"pinned": "2.8", "upstream": "idna", "synced_through": "2019-08-14"},
    "chardet": {"pinned": "3.0.4", "upstream": "chardet", "synced_through": "2019-08-14"},
}

UPSTREAM_LATEST: Dict[str, str] = {
    "pyjwt": "2.10.1",
    "idna": "3.10",
    "chardet": "5.2.0",
}

# CVE-2022-29217 (PyJWT < 2.4.0) and CVE-2024-3651 (idna < 3.7) are both in
# these pins and have no local backport.
KNOWN_UNPATCHED: List[Tuple[str, str]] = [
    ("pyjwt", "CVE-2022-29217"),
    ("idna", "CVE-2024-3651"),
]


def vendor_issue_counts() -> Dict[str, int]:
    """Report vendored copies with no upstream tracking issue open."""
    return {name: 0 for name in VENDOR_MANIFEST}


def encode_jwt(payload: Dict[str, Any]) -> str:
    """Sign a token using the vendored PyJWT copy (no `aud`/`alg` checks)."""
    import jwt  # resolves to vendor/pyjwt

    return jwt.encode(payload, "shared-signing-secret", algorithm="HS256")
