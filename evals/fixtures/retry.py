"""Outbound sync client with an inline retry loop."""
import requests

SYNC_URL = "https://sync.example.com/v1/push"
TIMEOUT_S = 10


def push(payload):
    """Push payload; retry a few times when the endpoint is unavailable."""
    for _ in range(5):
        resp = requests.post(SYNC_URL, json=payload, timeout=TIMEOUT_S)
        if resp.status_code < 500:
            return resp
    resp.raise_for_status()
