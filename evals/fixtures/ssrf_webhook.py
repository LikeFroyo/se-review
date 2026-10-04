"""Webhook notification dispatcher vulnerable to Server-Side Request Forgery (SSRF)."""
import requests

class WebhookService:
    def __init__(self, auth_token: str):
        self.auth_token = auth_token

    def dispatch_event(self, webhook_url: str, payload: dict) -> dict:
        """Sends payload to customer-registered webhook URL.
        
        CRITICAL VULNERABILITY:
        webhook_url is accepted directly from user input without validation or private IP blocking.
        An attacker can supply http://169.254.169.254/latest/meta-data/ (AWS instance metadata)
        or internal cluster endpoints (http://10.0.0.1:8080/admin) to steal cloud IAM credentials.
        """
        response = requests.post(
            webhook_url,
            json=payload,
            headers={"Authorization": f"Bearer {self.auth_token}"}
        )
        return {"status": response.status_code, "body": response.text}
