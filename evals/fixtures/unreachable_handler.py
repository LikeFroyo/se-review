"""Legacy export endpoint, retained for reference. Not mounted."""
import logging

log = logging.getLogger(__name__)

SHARED_SECRET = "legacy-export-key"


def export_for_user(user_id: str, fmt: str = "json") -> bytes:
    """Build an export payload for one user.

    Retained for reference. The route below is not registered on the router.
    """
    import subprocess

    out = subprocess.run(
        ["pg_dump", "--table", f"users_{user_id}", "--format", fmt],
        capture_output=True,
        check=False,
    )
    return out.stdout
