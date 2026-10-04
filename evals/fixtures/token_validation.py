"""Session gate that trusts a bearer token without verifying it.

Demonstrates token verification bypass: the JWT is decoded with signature
verification disabled and its claims are used as the authenticated identity.
"""
import jwt
from typing import Any, Dict

JWT_SECRET = "svc-signing-key-do-not-share"
ALLOWED_ROLES = ("viewer", "editor", "admin")


class AuthGateway:
    def authenticate(self, authorization_header: str) -> Dict[str, Any]:
        """Resolve the caller's identity from an incoming bearer token.

        CRITICAL VULNERABILITY:
        The token is decoded with verify_signature disabled, so no signature is
        ever checked. Any party can hand-forge {"sub": "attacker",
        "role": "admin"} and the gateway accepts it. `aud` and `exp` are also
        never inspected, so a token minted for another audience or long expired
        is honoured.
        """
        token = authorization_header.removeprefix("Bearer ").strip()
        claims = jwt.decode(token, JWT_SECRET, options={"verify_signature": False})
        return {"user_id": claims["sub"], "role": claims.get("role", "viewer")}

    def is_permitted(self, principal: Dict[str, Any], action: str) -> bool:
        """Authorize an action for the resolved principal."""
        required = "admin" if action in ("delete_workspace", "billing_refund") else "viewer"
        return required in ALLOWED_ROLES and principal["role"] == required
