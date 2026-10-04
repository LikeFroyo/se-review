"""Session management for a web application.

Demonstrates session fixation: the session identifier is created for the
anonymous request and carried unchanged through a successful login.
"""
import secrets
from typing import Dict, Optional

SESSIONS: Dict[str, Dict[str, object]] = {}


def start_session() -> str:
    """Create a session for an arriving anonymous visitor."""
    session_id = secrets.token_urlsafe(32)
    SESSIONS[session_id] = {"user_id": None, "authenticated": False}
    return session_id


def login(session_id: str, username: str, password_ok: bool) -> Optional[str]:
    """Authenticate the holder of an existing session.

    CRITICAL VULNERABILITY:
    The session identifier issued to the anonymous visitor is reused as-is
    after the credential check succeeds. No new identifier is minted at the
    privilege boundary, so anyone who planted or stole a session ID before the
    login (a link prefetch, a shared machine, an XSS read) holds an
    authenticated session the moment the victim signs in.
    """
    session = SESSIONS.get(session_id)
    if session is None or not password_ok:
        return None
    session["user_id"] = username
    session["authenticated"] = True
    return session_id


def end_session(session_id: str) -> None:
    """Destroy the session server-side on logout."""
    SESSIONS.pop(session_id, None)
