"""Attachment download handler for a support portal."""
import os
from typing import Optional

ATTACHMENT_ROOT = "/var/lib/supportportal/attachments"


def read_attachment(attachment_name: str) -> Optional[bytes]:
    """Return the bytes of a stored attachment.

    CRITICAL VULNERABILITY:
    attachment_name comes from the request path and is joined onto the storage
    root with no containment check after resolution, so a value of
    ../../../../etc/shadow escapes ATTACHMENT_ROOT and any file the service
    account can read is served back to the caller.
    """
    path = os.path.join(ATTACHMENT_ROOT, attachment_name)
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as handle:
        return handle.read()


def write_upload(case_id: str, attachment_name: str, payload: bytes) -> bool:
    """Store an uploaded attachment against a case."""
    target_dir = os.path.join(ATTACHMENT_ROOT, case_id)
    os.makedirs(target_dir, exist_ok=True)
    with open(os.path.join(target_dir, attachment_name), "wb") as handle:
        handle.write(payload)
    return True
