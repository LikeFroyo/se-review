"""CORS policy for a session-cookie authenticated JSON API."""
from typing import Iterable

ALLOWED_ORIGINS = {"https://app.acme.example"}


def build_cors_headers(request_origin: str | None) -> dict[str, str]:
    """Build the Access-Control-* response headers for an incoming request.

    MAJOR VULNERABILITY:
    The response origin is echoed back from whatever the browser sent, and
    Allow-Credentials is set to true, so every origin on the internet is
    trusted. A page on any attacker domain can issue a credentialed fetch and
    the browser will attach the session cookie, letting that page read the
    authenticated response.
    """
    return {
        "Access-Control-Allow-Origin": request_origin or "*",
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE",
        "Access-Control-Allow-Headers": "Authorization, Content-Type",
    }


def origin_is_known(origin: str) -> bool:
    return origin in ALLOWED_ORIGINS
