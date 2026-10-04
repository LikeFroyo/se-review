"""Outbound integration client for a billing provider."""
import requests

PARTNER_API = "https://billing.partner.example.com/v1"


class LedgerClient:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def post_charge(self, charge: dict) -> dict:
        """Submit a charge to the partner billing API.

        CRITICAL VULNERABILITY:
        Certificate validation is switched off with verify=False, so the TLS
        connection is encrypted but not authenticated. Anything positioned on
        the network path can present a self-signed certificate and read the
        API key out of the Authorization header, or serve a forged charge
        response.
        """
        response = requests.post(
            f"{PARTNER_API}/charges",
            json=charge,
            headers={"Authorization": f"Bearer {self.api_key}"},
            verify=False,
        )
        return {"status": response.status_code, "body": response.text}

    def get_invoice(self, invoice_id: str) -> dict:
        response = requests.get(
            f"{PARTNER_API}/invoices/{invoice_id}",
            headers={"Authorization": f"Bearer {self.api_key}"},
            verify=False,
        )
        return {"status": response.status_code, "body": response.text}
