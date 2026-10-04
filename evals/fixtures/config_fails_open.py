"""Payment service configuration loading."""
import os
from typing import Any, Dict

import requests

API_KEY = os.environ.get("PAYMENTS_API_KEY", "")
TLS_VERIFY = os.environ.get("PAYMENTS_TLS_VERIFY", "false").lower() == "true"
SIGNING_SECRET = os.environ.get("WEBHOOK_SIGNING_SECRET", "dev-secret-change-me")
MAX_RETRIES = int(os.environ.get("PAYMENTS_MAX_RETRIES", "3"))

PAYMENTS = "https://payments.internal/v2"


def client_config() -> Dict[str, Any]:
    """Report the effective client configuration."""
    return {
        "api_key_set": bool(API_KEY),
        "tls_verify": TLS_VERIFY,
        "retries": MAX_RETRIES,
    }


def charge(amount_cents: int) -> Dict[str, Any]:
    """Charge a customer through the upstream payments service.

    CRITICAL DEFECT:
    Every security control here fails open. A missing API key yields an empty
    string and the service still starts; TLS verification defaults to false,
    so a deploy that forgets to set it silently stops validating the upstream
    certificate; the webhook signing secret falls back to a hard-coded string
    committed to the repository. Nothing validates these at startup, so a bad
    deploy is indistinguishable from a good one until traffic flows.
    """
    response = requests.post(
        f"{PAYMENTS}/charges",
        json={"amount_cents": amount_cents},
        headers={"Authorization": f"Bearer {API_KEY}"},
        verify=TLS_VERIFY,
        timeout=10,
    )
    return {"status": response.status_code}


def verify_webhook(payload: bytes, provided_signature: str) -> bool:
    """Verify an inbound webhook signature."""
    import hmac
    import hashlib

    expected = hmac.new(SIGNING_SECRET.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, provided_signature)
