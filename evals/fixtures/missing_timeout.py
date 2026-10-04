"""Downstream inventory client missing socket and connect timeouts."""
import requests

class InventoryClient:
    def __init__(self, base_url: str):
        self.base_url = base_url

    def fetch_sku_availability(self, sku: str) -> dict:
        """Query inventory service for SKU availability.
        
        MAJOR OPERATIONAL DEFECT:
        requests.get defaults to timeout=None (infinite wait). If the downstream inventory service
        suffers a connection hang or TCP packet loss, the calling gunicorn/uvicorn worker thread
        blocks indefinitely, cascading into thread exhaustion and gateway 504 across the fleet.
        """
        url = f"{self.base_url}/api/v1/sku/{sku}"
        response = requests.get(url)  # Missing timeout=(connect, read)
        return response.json()
