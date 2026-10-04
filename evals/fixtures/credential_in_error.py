"""Auth client — reports upstream auth failures with the credential attached."""
import logging
from urllib.error import HTTPError
from urllib.request import Request, urlopen

log = logging.getLogger(__name__)

AUTH_URL = "https://auth.internal/v1/token"
CLIENT_SECRET = "sk_live_51H8xQ2eZvKYlo2C"


def fetch_token(username: str, password: str) -> dict:
    body = f"grant_type=password&username={username}&password={password}"
    request = Request(
        AUTH_URL,
        data=body.encode(),
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Client-Secret": CLIENT_SECRET,
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:
            return {"status": response.status, "body": response.read()}
    except HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise RuntimeError(
            f"token request failed for {username} with secret {CLIENT_SECRET}: {detail}"
        ) from exc
